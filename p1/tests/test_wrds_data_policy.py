"""Guard: no licensed WRDS/CRSP data reaches this repository.

The free EDGAR path could commit its outputs freely — public locators, no paid
source. The WRDS path cannot: CRSP is subscription data under an agreement that
does not permit redistribution, and a push is irreversible in a way a bad number
is not. Policy is p1/t2_wrds/README.md; these tests are its enforcement, and they
run in CI because CI runs the whole suite.

Deliberately strict: adding a file to p1/t2_wrds/ requires adding it here, which
is the moment to ask "is this licensed data?".
"""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Everything git is allowed to track under p1/t2_wrds/. Code, docs, and artifacts
# derived from PUBLIC T1 output only.
ALLOWED = {
    "p1/t2_wrds/README.md",
    "p1/t2_wrds/build_waves.py",
    "p1/t2_wrds/build_waves.log",
    "p1/t2_wrds/holdings_pipeline.py",
    "p1/t2_wrds/coverage_census.py",
    "p1/t2_wrds/waves.csv",
    "p1/t2_wrds/waves_members.csv",
}
ALLOWED_SUFFIXES = (".lineage.json",)      # provenance sidecars carry no rows

RESTRICTED_MARKER = "WRDS" "-RESTRICTED"   # split so this file is not itself a hit


def tracked(prefix):
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", prefix],
                         capture_output=True, text=True, check=True).stdout
    return [l for l in out.splitlines() if l.strip()]


def test_only_allowlisted_files_are_tracked_under_the_wrds_path():
    unexpected = [f for f in tracked("p1/t2_wrds/")
                  if f not in ALLOWED and not f.endswith(ALLOWED_SUFFIXES)]
    assert not unexpected, (
        "untracked-by-policy file(s) under p1/t2_wrds/: %s\n"
        "If this is derived aggregate output or code, add it to ALLOWED. "
        "If it is a row-level extract of a licensed table, it must NOT be "
        "committed — see p1/t2_wrds/README.md." % unexpected)


def test_no_restricted_marker_in_tracked_files():
    """A raw pull that escapes .gitignore still fails here, on its own marker."""
    r = subprocess.run(["git", "-C", str(ROOT), "grep", "-lI", RESTRICTED_MARKER],
                       capture_output=True, text=True)
    hits = [l for l in r.stdout.splitlines()
            if l.strip() and not l.endswith(("README.md", "test_wrds_data_policy.py",
                                             "WRDS-independent-workplan.md"))]
    assert not hits, "licensed-data marker found in tracked file(s): %s" % hits


def test_raw_and_cache_paths_are_gitignored():
    gi = (ROOT / ".gitignore").read_text()
    for pat in ("p1/t2_wrds/raw/", "p1/t2_wrds/cache/",
                "p1/t2_wrds/*.raw.csv", "p1/t2_wrds/*.raw.parquet"):
        assert pat in gi, "missing .gitignore rule for %s" % pat


def test_a_raw_pull_would_actually_be_ignored(tmp_path):
    """check-ignore, not just a string match — the rule has to bite."""
    for candidate in ("p1/t2_wrds/raw/crsp_holdings.parquet",
                      "p1/t2_wrds/cache/msf.pkl",
                      "p1/t2_wrds/stocknames.raw.csv"):
        r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", candidate])
        assert r.returncode == 0, "%s would NOT be ignored" % candidate


def test_wrds_raw_pulls_are_ignored_but_their_provenance_is_not():
    """Licensed rows stay box-local; the locator that proves them must not.

    Each landed parquet gets a `.lineage.json` carrying the exact SQL, the row
    count and the code version. That sidecar is provenance, not data, and
    meta-rule 1 requires it to exist somewhere durable. The gitignore parent has
    to be `p1/wrds/raw/*`, not `p1/wrds/raw/` — git does not reconsider files
    inside an excluded DIRECTORY, so a negation under the latter never fires and
    the sidecars would vanish silently.
    """
    ignored = "p1/wrds/raw/dsf__dsf.parquet"
    kept = ["p1/wrds/raw/dsf__dsf.parquet.lineage.json",
            "p1/wrds/raw/mf_holdings__matched_fundnos.json"]
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", ignored])
    assert r.returncode == 0, "%s must be ignored — it is licensed CRSP data" % ignored
    for path in kept:
        r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", path])
        assert r.returncode != 0, (
            "%s is ignored, so the pull would land with no committed locator. "
            "Check that .gitignore excludes `p1/wrds/raw/*` (with the star) so "
            "the negations below it can fire." % path)


def test_readme_states_the_policy():
    txt = (ROOT / "p1" / "t2_wrds" / "README.md").read_text()
    for phrase in ("May NOT be committed", "manifest of query locators",
                   RESTRICTED_MARKER):
        assert phrase in txt
