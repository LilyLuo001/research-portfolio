#!/usr/bin/env python3
"""Fail-closed, fresh-leaf publication helpers for the numerical audit."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import uuid


class OutputSafetyError(RuntimeError):
    """A requested artifact destination is unsafe or already reserved."""


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
        # The same-name exclusive lock serializes cooperating YAX publishers.
        # rename is atomic on the required same-parent filesystem.
        self.staging.rename(self.target)
        self.published = True
        self.release_lock()

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
