"""The guard that refuses to write licensed microdata where git could stage it.

These tests build real git repositories in tmp_path rather than mocking
subprocess, because the property under test is what `git check-ignore` says in
a work tree whose `.gitignore` is stale -- which is precisely what a mock would
assume away. The hazard was found in practice: a compute-host clone checked out
at a commit older than the `.gitignore` lines naming the panels, where the
builder's default `--output` wrote 3.85 MB of licensed IPUMS-CPS microdata into
a tree that showed it as untracked-and-stageable.
"""
import importlib.util
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "microdata_guard", ROOT / "w2" / "microdata_guard.py")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)
# Register under the name the builders import, so a builder loaded below gets
# THIS module object rather than a second copy. Without this the exception
# classes differ and an end-to-end test cannot tell a refusal from a bug.
sys.modules.setdefault("microdata_guard", GUARD)


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=str(repo), check=True,
                   capture_output=True, text=True)


def _repo(tmp_path, name, gitignore=None):
    repo = tmp_path / name
    (repo / "dax" / "data_built").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    if gitignore is not None:
        (repo / ".gitignore").write_text(gitignore)
    (repo / "README").write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    return repo


CURRENT = "dax/data_built/cps_extract.parquet\n"
STALE = "*.pyc\n"


def test_refuses_when_the_work_tree_does_not_ignore_the_output(tmp_path):
    """The stale clone. This is the case that leaked microdata."""
    repo = _repo(tmp_path, "stale", gitignore=STALE)
    out = repo / "dax" / "data_built" / "cps_extract.parquet"
    with pytest.raises(GUARD.MicrodataPathError) as e:
        GUARD.assert_not_committable(out)
    msg = str(e.value)
    assert "REFUSING TO WRITE" in msg
    # The error has to be actionable at 2am on a compute host: it must name
    # the tree, say why, and give both fixes.
    assert str(repo.resolve()) in msg
    assert "git add -A" in msg
    assert "--output" in msg


def test_allows_when_the_work_tree_ignores_the_output(tmp_path):
    repo = _repo(tmp_path, "current", gitignore=CURRENT)
    out = repo / "dax" / "data_built" / "cps_extract.parquet"
    rec = GUARD.assert_not_committable(out)
    assert rec["output_in_git_work_tree"] is True
    assert rec["ignored_by_work_tree"] is True
    assert rec["work_tree"] == str(repo.resolve())


def test_allows_outside_any_work_tree(tmp_path):
    """A scratch directory on the compute host: nothing can stage it."""
    out = tmp_path / "scratch" / "cps_extract.parquet"
    out.parent.mkdir(parents=True)
    rec = GUARD.assert_not_committable(out)
    assert rec["output_in_git_work_tree"] is False
    assert rec["work_tree"] is None


def test_the_answer_comes_from_the_tree_holding_the_file(tmp_path):
    """Not from the process's cwd.

    A seat can launch the builder from anywhere -- from a current checkout
    while writing into a stale one. If the guard asked git from the cwd it
    would get the *current* tree's ignore rules and wave the write through.
    It must ask the tree that will hold the file.
    """
    stale = _repo(tmp_path, "stale", gitignore=STALE)
    current = _repo(tmp_path, "current", gitignore=CURRENT)
    out = stale / "dax" / "data_built" / "cps_extract.parquet"
    cwd = pathlib.Path.cwd()
    try:
        import os
        os.chdir(current)
        with pytest.raises(GUARD.MicrodataPathError):
            GUARD.assert_not_committable(out)
    finally:
        import os
        os.chdir(cwd)


def test_a_gitignored_parent_directory_counts(tmp_path):
    """Ignoring the directory is as good as naming the file."""
    repo = _repo(tmp_path, "dirignore", gitignore="dax/data_built/\n")
    out = repo / "dax" / "data_built" / "cps_extract.parquet"
    assert GUARD.assert_not_committable(out)["ignored_by_work_tree"] is True


def test_this_repo_ignores_both_panel_defaults():
    """The live check: the two builder defaults are ignored in THIS tree.

    If someone deletes those .gitignore lines, this fails here rather than on
    a compute host after the microdata has already been written.
    """
    for name in ("cps_extract.parquet", "cps_preevent_power_panel.parquet"):
        p = ROOT / "data_built" / name
        tree = GUARD.work_tree_for(p)
        assert tree is not None, "the test suite runs inside the repo"
        assert GUARD.is_ignored(p, tree), f"{name} is no longer gitignored"


# --- end to end, through the real builders -------------------------------
# The unit tests above prove the guard's logic. These prove it is actually
# wired in front of the write, which is the part a refactor could silently
# undo: an unwired guard passes every test above and still leaks.

HEAD = "YEAR,MONTH,AGE,WTFINL,EMPSTAT,UHRSWORKT,CPSIDP,OCC2010\n"
ROWS = ("2025,9,22,1000,10,40,1,1010\n"
        "2025,9,24,1000,21,999,3,1010\n")


def _extract(tmp_path):
    p = tmp_path / "cps.csv"
    p.write_text(HEAD + ROWS, encoding="utf-8")
    return p


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "w2" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_analysis_builder_refuses_to_write_into_a_stale_clone(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    repo = _repo(tmp_path, "stale", gitignore=STALE)
    out = repo / "dax" / "data_built" / "cps_extract.parquet"
    B = _load("build_cps_analysis_panel")
    code = B.main(["--extract", str(_extract(tmp_path)), "--output", str(out),
                   "--receipt", str(tmp_path / "r.json"),
                   "--employed-codes", "10,12"])
    # Refused the way every other guard in the builder refuses: exit 2, not a
    # traceback -- and, the whole point, refused BEFORE the write.
    assert code == 2
    assert not out.exists()


def test_analysis_builder_writes_normally_outside_a_work_tree(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    out = tmp_path / "scratch" / "cps_extract.parquet"
    out.parent.mkdir()
    receipt = tmp_path / "r.json"
    B = _load("build_cps_analysis_panel")
    assert B.main(["--extract", str(_extract(tmp_path)), "--output", str(out),
                   "--receipt", str(receipt), "--employed-codes", "10,12"]) == 0
    assert out.exists()
    import json as _json
    rec = _json.loads(out.with_suffix(".receipt.json").read_text())
    assert rec["output_path_guard"]["output_in_git_work_tree"] is False
