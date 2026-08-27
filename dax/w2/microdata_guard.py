#!/usr/bin/env python3
"""Refuse to write licensed microdata where `git add -A` could stage it.

The hazard is real and was found in practice, not imagined. Both IPUMS-CPS
builders default their `--output` to a path inside `dax/data_built/`, which is
inside the repository work tree. What keeps the microdata out of a commit is
two lines of `.gitignore`, added when the first panel was built:

    dax/data_built/cps_preevent_power_panel.parquet
    dax/data_built/cps_extract.parquet

A clone checked out at a commit *older* than those lines has a `.gitignore`
that does not mention the file. Running the builder there writes the parquet
into a work tree that does not ignore it, `git status` shows it as untracked,
and `git add -A` stages 3.85 MB of licensed person-level microdata. Nothing in
the builder, the receipt, or CI catches it, because by the time CI sees the
push the redistribution has already happened.

The guard closes that by asking the work tree that will actually hold the file
whether it would ignore it -- `git check-ignore`, run against the output's own
directory, so a stale `.gitignore` answers for itself rather than the current
checkout answering on its behalf. Three outcomes:

  * path is not inside any git work tree      -> write (nothing can stage it)
  * path is inside one and is ignored there   -> write (that tree is current)
  * path is inside one and is NOT ignored     -> refuse

The third case is exactly the stale clone, and refusing is the whole point:
the builder stops before the file exists, so there is nothing to stage. The
operator's fix is to pull the current `.gitignore` or to pass an `--output`
outside the work tree, and the error says both.

This is a redistribution guard, not a secrecy guard: it protects files whose
licence forbids committing them. Receipts, counts, hashes and code mappings
carry no microdata and are committed as usual.
"""
from __future__ import annotations

import pathlib
import subprocess


class MicrodataPathError(RuntimeError):
    """Raised when a licensed output would land somewhere git could stage it."""


def _git(args, cwd):
    """Run git in `cwd`; return (returncode, stdout). Absent git -> (None, '')."""
    try:
        r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True,
                           text=True, timeout=15)
        return r.returncode, r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None, ""


def work_tree_for(path):
    """The git work tree that would contain `path`, or None if there is none.

    Resolved from the output's *parent directory*, which must already exist --
    callers mkdir before guarding. Asking from the parent rather than from the
    current working directory is what makes a stale clone answer for itself:
    the builder may be launched from anywhere, and it is the tree holding the
    file, not the tree holding the shell, that could stage it.
    """
    parent = pathlib.Path(path).resolve().parent
    if not parent.is_dir():
        return None
    code, out = _git(["rev-parse", "--show-toplevel"], parent)
    if code != 0 or not out:
        return None
    return pathlib.Path(out)


def is_ignored(path, work_tree):
    """True if `work_tree`'s ignore rules cover `path`.

    `git check-ignore -q` exits 0 when the path is ignored, 1 when it is not,
    and >1 on error. An error is not treated as ignored: an unreadable answer
    about a licensing guard has to fail closed.
    """
    p = pathlib.Path(path).resolve()
    code, _ = _git(["check-ignore", "-q", str(p)], work_tree)
    if code is None:
        raise MicrodataPathError(
            f"cannot run git to check whether {p} is ignored by the work tree "
            f"at {work_tree}. Refusing to write licensed microdata into a "
            f"repository whose ignore rules could not be read.")
    if code == 0:
        return True
    if code == 1:
        return False
    raise MicrodataPathError(
        f"`git check-ignore` failed (exit {code}) for {p} in {work_tree}. "
        f"Refusing to write licensed microdata on an unreadable answer.")


def assert_not_committable(path, what="licensed microdata"):
    """Refuse to write `path` into a work tree that would not ignore it.

    Call after creating the parent directory and before writing. Returns a
    dict describing the decision, for the receipt.
    """
    p = pathlib.Path(path).resolve()
    tree = work_tree_for(p)
    if tree is None:
        return {"output_in_git_work_tree": False, "work_tree": None,
                "ignored_by_work_tree": None,
                "guard": "no work tree contains this path; nothing can stage it"}
    if is_ignored(p, tree):
        return {"output_in_git_work_tree": True, "work_tree": str(tree),
                "ignored_by_work_tree": True,
                "guard": "path is inside a work tree and that tree ignores it"}
    raise MicrodataPathError(
        f"REFUSING TO WRITE {what} to {p}.\n"
        f"\n"
        f"That path is inside the git work tree at {tree}, and that tree's "
        f"ignore rules do NOT cover it. Writing here would leave the file "
        f"untracked but stageable: a `git add -A` in this clone would commit "
        f"licensed person-level microdata, which the redistribution terms "
        f"forbid.\n"
        f"\n"
        f"This usually means the clone is checked out at a commit older than "
        f"the .gitignore lines that name this file. Two fixes, either is "
        f"enough:\n"
        f"  1. bring this clone's .gitignore up to date "
        f"(git -C {tree} pull), then re-run; or\n"
        f"  2. re-run with --output pointing outside the work tree, e.g. "
        f"a scratch directory on the compute host.\n"
        f"\n"
        f"The receipt, which carries only counts, hashes and code mappings "
        f"and no microdata, is committed either way.")
