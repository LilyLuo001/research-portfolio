#!/usr/bin/env python3
"""Fail-closed, fresh-leaf publication helpers for the numerical audit."""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
import errno
import os
from pathlib import Path
import shutil
import sys
import uuid


class OutputSafetyError(RuntimeError):
    """A requested artifact destination is unsafe or already reserved."""


def atomic_rename_noreplace(source: Path, target: Path) -> None:
    """Atomically rename a same-parent directory without replacing a target."""
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    target_bytes = os.fsencode(target)
    if os.name == "posix" and hasattr(libc, "renameat2"):
        function = libc.renameat2
        function.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(-100, source_bytes, -100, target_bytes, 1)
    elif sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        function = libc.renameatx_np
        function.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(-2, source_bytes, -2, target_bytes, 0x00000004)
    else:
        raise OutputSafetyError("platform lacks atomic no-replace directory rename")
    if result != 0:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise OutputSafetyError("output target appeared; refusing overwrite")
        raise OutputSafetyError(f"atomic no-replace publication failed with errno {error}")


def is_within(path: Path, parent: Path) -> bool:
    path = path.resolve(strict=False)
    parent = parent.resolve(strict=False)
    return path == parent or parent in path.parents


def paths_overlap(left: Path, right: Path) -> bool:
    left = left.resolve(strict=False)
    right = right.resolve(strict=False)
    return left == right or left in right.parents or right in left.parents


@dataclass
class AtomicOutputLeaf:
    """A private staging directory published only after a complete run."""

    target: Path
    staging: Path
    lock: Path
    lock_fd: int | None
    published: bool = False
    post_commit_cleanup_warnings: tuple[str, ...] = ()

    @classmethod
    def reserve(
        cls,
        target: Path,
        repo_root: Path,
        input_paths: list[Path],
    ) -> "AtomicOutputLeaf":
        repo = repo_root.resolve(strict=True)
        raw_target = target.expanduser()
        if raw_target.name in {"", ".", ".."}:
            raise OutputSafetyError("output must be a named leaf")
        parent = raw_target.parent.resolve(strict=True)
        resolved_target = parent / raw_target.name
        if is_within(resolved_target, repo):
            raise OutputSafetyError("output leaf must be outside the Git repository")
        for path in input_paths:
            resolved_input = path.expanduser().resolve(strict=True)
            if paths_overlap(resolved_target, resolved_input):
                raise OutputSafetyError("output leaf must be disjoint from every input path")
        if resolved_target.exists() or resolved_target.is_symlink():
            raise OutputSafetyError("refusing a pre-existing output leaf")

        lock = parent / f".{resolved_target.name}.publish.lock"
        try:
            lock_fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise OutputSafetyError("output leaf is already reserved by another run") from error
        staging = parent / f".{resolved_target.name}.staging-{uuid.uuid4().hex}"
        try:
            staging.mkdir(mode=0o700, exist_ok=False)
        except Exception:
            os.close(lock_fd)
            lock.unlink(missing_ok=True)
            raise
        return cls(resolved_target, staging, lock, lock_fd)

    def publish(self) -> None:
        if self.published:
            raise OutputSafetyError("output leaf was already published")
        if self.target.exists() or self.target.is_symlink():
            raise OutputSafetyError("output target appeared after reservation; refusing overwrite")
        for directory, dirnames, filenames in os.walk(
            self.staging, topdown=False, followlinks=False
        ):
            base = Path(directory)
            for name in filenames:
                path = base / name
                if path.is_symlink() or not path.is_file():
                    raise OutputSafetyError("staging contains a non-regular output")
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
            for name in dirnames:
                if (base / name).is_symlink():
                    raise OutputSafetyError("staging contains a symlink directory")
            directory_fd = os.open(base, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        # Atomic no-replace rename is the publication commit point.
        atomic_rename_noreplace(self.staging, self.target)
        self.published = True
        warnings: list[str] = []
        try:
            parent_fd = os.open(self.target.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except OSError as error:
            warnings.append(f"parent_fsync_errno_{error.errno}")
        # Once rename commits, cleanup failure must not turn success into an
        # ambiguous exception whose caller might misclassify the published leaf.
        try:
            self.release_lock()
        except OSError as error:
            warnings.append(f"lock_cleanup_errno_{error.errno}")
            self.lock_fd = None
        self.post_commit_cleanup_warnings = tuple(warnings)

    def release_lock(self) -> None:
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None
        self.lock.unlink(missing_ok=True)

    def abandon(self) -> None:
        """Release the lock but preserve the private staging leaf for diagnosis."""
        self.release_lock()

    def discard(self) -> None:
        """Remove this audit-created staging leaf after a sanitation failure."""
        if self.published:
            raise OutputSafetyError("cannot discard an already published output leaf")
        if self.staging.exists():
            shutil.rmtree(self.staging)
        self.release_lock()
