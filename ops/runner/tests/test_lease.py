import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("lease", ROOT / "ops" / "runner" / "lease.py")
assert SPEC and SPEC.loader
LEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEASE)


def _result(code=0, output=""):
    return SimpleNamespace(returncode=code, stdout=output)


def test_failed_push_restores_exact_preclaim_head_without_hard_reset(monkeypatch, tmp_path):
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args == ("status", "--porcelain"):
            return _result(0, "")
        if args == ("rev-parse", "HEAD"):
            return _result(0, "abc123\n")
        if args == ("push",):
            return _result(1, "rejected")
        return _result(0, "")

    monkeypatch.setattr(LEASE, "LEASES", tmp_path / "leases")
    monkeypatch.setattr(LEASE, "_git", fake_git)

    assert LEASE.claim("DAX-test", "A", 1) == 1
    assert ("reset", "--mixed", "abc123") in calls
    assert not any(call[:2] == ("reset", "--hard") for call in calls)
    assert not (tmp_path / "leases" / "DAX-test.lease").exists()


def test_dirty_worktree_refuses_before_writing_or_committing(monkeypatch, tmp_path):
    calls = []

    def fake_git(*args):
        calls.append(args)
        return _result(0, " M user-work.txt\n")

    monkeypatch.setattr(LEASE, "LEASES", tmp_path / "leases")
    monkeypatch.setattr(LEASE, "_git", fake_git)

    assert LEASE.claim("DAX-test", "A", 1) == 1
    assert calls == [("status", "--porcelain")]
    assert not (tmp_path / "leases").exists()
