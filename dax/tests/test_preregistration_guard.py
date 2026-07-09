"""The guard must trip pre-tag and pass post-tag (DAX W0 req 2)."""
import pathlib
import subprocess
import sys

import pytest

GUARD = pathlib.Path(__file__).resolve().parents[1] / "analysis" / "preregistration_guard.py"
ROOT = pathlib.Path(__file__).resolve().parents[2]


def _tag_exists():
    r = subprocess.run(["git", "-C", str(ROOT), "tag", "-l", "v1.0-preregistered"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return "v1.0-preregistered" in r.stdout.decode().split()


def test_guard_state_matches_tag():
    """Importing the guard in a fresh interpreter exits iff the tag is absent."""
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, {0!r}); "
         "import preregistration_guard; print('UNLOCKED')".format(str(GUARD.parent))],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(ROOT))
    if _tag_exists():
        assert r.returncode == 0 and b"UNLOCKED" in r.stdout
    else:
        assert r.returncode != 0, "guard FAILED to seal outcomes pre-tag"
        assert b"REFUSED" in r.stderr + r.stdout


def test_no_outcomes_files_committed_pre_tag():
    """Mirror of the CI rule, runnable locally."""
    if _tag_exists():
        pytest.skip("tag present — outcomes dir is legitimately unlocked")
    r = subprocess.run(["git", "-C", str(ROOT), "ls-files", "dax/analysis/outcomes/"],
                       stdout=subprocess.PIPE)
    assert r.stdout.decode().strip() == "", \
        "files committed under dax/analysis/outcomes/ before the prereg tag"
