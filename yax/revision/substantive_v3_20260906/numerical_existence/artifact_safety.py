#!/usr/bin/env python3
"""Fail-closed, fresh-leaf publication helpers for the numerical audit."""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
import errno
import os
from pathlib import Path
import shutil
import stat
import sys
import uuid
from typing import Any, Callable


class OutputSafetyError(RuntimeError):
    """A requested artifact destination is unsafe or already reserved."""


def _try_kernel_atomic_rename_noreplace(
    source: Path,
    target: Path,
) -> tuple[bool, str, int | None]:
    """Try a kernel-enforced no-replace rename and report unsupported cases."""
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
        backend = "linux_renameat2_RENAME_NOREPLACE"
    elif sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        function = libc.renameatx_np
        function.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(-2, source_bytes, -2, target_bytes, 0x00000004)
        backend = "darwin_renameatx_np_RENAME_EXCL"
    else:
        return False, "kernel_no_replace_unavailable", None
    if result == 0:
        return True, backend, None
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise OutputSafetyError("output target appeared; refusing overwrite")
    unsupported = {
        errno.EINVAL,
        errno.ENOSYS,
        getattr(errno, "EOPNOTSUPP", errno.EINVAL),
        getattr(errno, "ENOTSUP", errno.EINVAL),
    }
    if error in unsupported:
        return False, backend, error
    raise OutputSafetyError(
        f"atomic no-replace publication failed with errno {error}"
    )


def atomic_publish_same_parent(
    source: Path,
    target: Path,
    publication_guard: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Publish by same-parent rename, preferring kernel no-replace semantics.

    Some GPFS deployments return ``EINVAL`` for
    ``renameat2(RENAME_NOREPLACE)``.  On an unsupported result, the portable
    path revalidates the exclusive sibling lock, immediately rechecks target
    absence, and then uses the atomic POSIX same-parent directory rename.
    Unlike the kernel path, that fallback cannot prevent a noncooperating
    same-user process from creating an empty target in the bounded interval
    between the absence check and ``os.rename``.  The returned semantics state
    that limitation explicitly.
    """
    source_parent = source.parent.resolve(strict=True)
    target_parent = target.parent.resolve(strict=True)
    if source_parent != target_parent:
        raise OutputSafetyError("publication rename must remain within one parent")
    initial_guard = publication_guard()
    if not str(initial_guard.get("status", "")).startswith("PASS_"):
        raise OutputSafetyError("publication guard did not return a passing state")
    committed, backend, unsupported_errno = _try_kernel_atomic_rename_noreplace(
        source, target,
    )
    if committed:
        return {
            "status": "PASS_KERNEL_ATOMIC_NOREPLACE_PUBLICATION",
            "publication_backend": backend,
            "same_parent_directory_rename_atomic": True,
            "kernel_no_replace_guarantee": True,
            "portable_gpfs_fallback_used": False,
            "exclusive_sibling_lock_verified": True,
            "publication_guard_status": initial_guard["status"],
            "target_absence_rechecked_immediately_before_portable_rename": False,
            "bounded_noncooperating_same_user_toctou": None,
        }

    # Keep this sequence tight: guard -> lstat absence check -> os.rename.
    # The final operation is atomic, but target nonexistence is cooperative on
    # this path and is not represented as a kernel no-replace guarantee.
    fallback_guard = publication_guard()
    if not str(fallback_guard.get("status", "")).startswith("PASS_"):
        raise OutputSafetyError("portable publication guard did not pass")
    try:
        os.lstat(target)
    except FileNotFoundError:
        pass
    else:
        raise OutputSafetyError(
            "output target appeared during portable publication recheck; "
            "refusing overwrite"
        )
    try:
        os.rename(source, target)
    except OSError as error:
        if error.errno in {errno.EEXIST, errno.ENOTEMPTY}:
            raise OutputSafetyError(
                "output target appeared during portable rename; refusing overwrite"
            ) from error
        raise OutputSafetyError(
            f"portable same-parent publication failed with errno {error.errno}"
        ) from error
    return {
        "status": "PASS_PORTABLE_GPFS_SAME_PARENT_PUBLICATION",
        "publication_backend": "posix_os_rename_under_exclusive_sibling_lock",
        "kernel_no_replace_attempt_backend": backend,
        "kernel_no_replace_unsupported_errno": unsupported_errno,
        "same_parent_directory_rename_atomic": True,
        "kernel_no_replace_guarantee": False,
        "portable_gpfs_fallback_used": True,
        "exclusive_sibling_lock_verified": True,
        "publication_guard_status": fallback_guard["status"],
        "target_absence_rechecked_immediately_before_portable_rename": True,
        "target_replacement_prevention": (
            "exclusive cooperative sibling lock plus immediate lstat absence "
            "recheck; not kernel-enforced"
        ),
        "bounded_noncooperating_same_user_toctou": (
            "not eliminated: a noncooperating same-user writer could create an "
            "empty target between the final lstat and os.rename"
        ),
    }


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
    lock_device: int
    lock_inode: int
    lock_token: bytes
    staging_device: int
    staging_inode: int
    published: bool = False
    post_commit_cleanup_warnings: tuple[str, ...] = ()
    publication_semantics: dict[str, Any] | None = None

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
        lock_token = uuid.uuid4().hex.encode("ascii")
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        try:
            lock_fd = os.open(str(lock), flags, 0o600)
        except FileExistsError as error:
            raise OutputSafetyError("output leaf is already reserved by another run") from error
        try:
            os.write(lock_fd, lock_token)
            os.fsync(lock_fd)
            lock_stat = os.fstat(lock_fd)
            staging = parent / f".{resolved_target.name}.staging-{uuid.uuid4().hex}"
            staging.mkdir(mode=0o700, exist_ok=False)
        except Exception:
            os.close(lock_fd)
            lock.unlink(missing_ok=True)
            raise
        staging_stat = os.lstat(staging)
        return cls(
            resolved_target, staging, lock, lock_fd,
            int(lock_stat.st_dev), int(lock_stat.st_ino), lock_token,
            int(staging_stat.st_dev), int(staging_stat.st_ino),
        )

    def verify_publication_state(self) -> dict[str, Any]:
        """Revalidate the private staging inode and exclusive lock identity."""
        if self.lock_fd is None:
            raise OutputSafetyError("publication lock descriptor is not open")
        try:
            descriptor_stat = os.fstat(self.lock_fd)
            path_stat = os.lstat(self.lock)
            staging_stat = os.lstat(self.staging)
        except OSError as error:
            raise OutputSafetyError(
                "publication lock or staging state cannot be revalidated"
            ) from error
        if not stat.S_ISREG(path_stat.st_mode) or stat.S_ISLNK(path_stat.st_mode):
            raise OutputSafetyError("publication lock path is not a regular file")
        expected_lock = (self.lock_device, self.lock_inode)
        if (
            (descriptor_stat.st_dev, descriptor_stat.st_ino) != expected_lock
            or (path_stat.st_dev, path_stat.st_ino) != expected_lock
        ):
            raise OutputSafetyError("publication lock inode identity changed")
        if descriptor_stat.st_nlink != 1 or path_stat.st_nlink != 1:
            raise OutputSafetyError("publication lock link count changed")
        if descriptor_stat.st_uid != os.geteuid() or path_stat.st_uid != os.geteuid():
            raise OutputSafetyError("publication lock owner changed")
        if os.pread(self.lock_fd, len(self.lock_token), 0) != self.lock_token:
            raise OutputSafetyError("publication lock token changed")
        expected_staging = (self.staging_device, self.staging_inode)
        if (
            not stat.S_ISDIR(staging_stat.st_mode)
            or stat.S_ISLNK(staging_stat.st_mode)
            or (staging_stat.st_dev, staging_stat.st_ino) != expected_staging
        ):
            raise OutputSafetyError("publication staging inode identity changed")
        if staging_stat.st_nlink < 2:
            raise OutputSafetyError("publication staging directory state changed")
        parent_stat = os.stat(self.target.parent)
        if staging_stat.st_dev != parent_stat.st_dev:
            raise OutputSafetyError("publication staging and target span filesystems")
        return {
            "status": "PASS_EXCLUSIVE_SIBLING_LOCK_AND_STAGING_INODE",
            "lock_descriptor_and_path_inode_match": True,
            "lock_owner_is_effective_user": True,
            "lock_token_matches": True,
            "staging_inode_matches_reservation": True,
            "same_parent_filesystem": True,
        }

    def publish(self) -> dict[str, Any]:
        if self.published:
            raise OutputSafetyError("output leaf was already published")
        if self.target.exists() or self.target.is_symlink():
            raise OutputSafetyError("output target appeared after reservation; refusing overwrite")
        self.verify_publication_state()
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
        # The rename is the publication commit point.  Kernel-enforced
        # no-replace is preferred; unsupported GPFS mounts use the explicitly
        # qualified cooperative fallback returned in publication_semantics.
        self.verify_publication_state()
        self.publication_semantics = atomic_publish_same_parent(
            self.staging, self.target, self.verify_publication_state,
        )
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
        except OutputSafetyError:
            warnings.append("lock_cleanup_safety_state_changed")
            self.lock_fd = None
        self.post_commit_cleanup_warnings = tuple(warnings)
        self.publication_semantics["post_commit_cleanup_warnings"] = list(
            self.post_commit_cleanup_warnings
        )
        self.publication_semantics["receipt_ready_semantics_retained"] = True
        return dict(self.publication_semantics)

    def release_lock(self) -> None:
        expected_lock = (self.lock_device, self.lock_inode)
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None
        try:
            path_stat = os.lstat(self.lock)
        except FileNotFoundError:
            return
        if (path_stat.st_dev, path_stat.st_ino) != expected_lock:
            raise OutputSafetyError(
                "refusing to unlink a replaced publication lock inode"
            )
        self.lock.unlink()

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
