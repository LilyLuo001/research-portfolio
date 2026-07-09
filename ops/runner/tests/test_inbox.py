"""run_inbox.sh: executes ops/box/inbox.sh once per content version, appends
output to the tracked inbox_log.md, commits, and never re-runs unchanged
content — the box's git-operated remote-hands channel."""
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]


def _repo(tmp_path):
    (tmp_path / "ops" / "box").mkdir(parents=True)
    shutil.copy(ROOT / "ops" / "box" / "run_inbox.sh",
                tmp_path / "ops" / "box" / "run_inbox.sh")
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "t@t"],
                ["git", "config", "user.name", "t"]):
        subprocess.run(cmd, cwd=tmp_path, check=True)
    return tmp_path


def _run(repo):
    return subprocess.run(["bash", "ops/box/run_inbox.sh"], cwd=repo,
                          capture_output=True, text=True, timeout=60)


def test_inbox_runs_once_and_logs(tmp_path):
    repo = _repo(tmp_path)
    (repo / "ops" / "box" / "inbox.sh").write_text("echo hello-from-inbox\nexit 0\n")

    assert _run(repo).returncode == 0
    log = (repo / "ops" / "box" / "inbox_log.md").read_text()
    assert "hello-from-inbox" in log
    assert "[exit: 0]" in log

    # the run is committed (log + marker-driven state travel by git)
    msg = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=repo,
                         capture_output=True, text=True).stdout
    assert msg.startswith("box: inbox run")

    # same content again -> no-op, log unchanged
    assert _run(repo).returncode == 0
    assert (repo / "ops" / "box" / "inbox_log.md").read_text() == log


def test_changed_inbox_reruns_and_failure_does_not_loop(tmp_path):
    repo = _repo(tmp_path)
    (repo / "ops" / "box" / "inbox.sh").write_text("echo v1\n")
    _run(repo)
    (repo / "ops" / "box" / "inbox.sh").write_text("echo v2\nfalse\n")
    _run(repo)
    log = (repo / "ops" / "box" / "inbox_log.md").read_text()
    assert "v1" in log and "v2" in log
    assert "[exit: 1]" in log          # failure is recorded…
    before = log
    _run(repo)                          # …but does NOT re-run every cycle
    assert (repo / "ops" / "box" / "inbox_log.md").read_text() == before


def test_missing_inbox_is_a_noop(tmp_path):
    repo = _repo(tmp_path)
    assert _run(repo).returncode == 0
    assert not (repo / "ops" / "box" / "inbox_log.md").exists()


def test_apply_decisions_invokes_inbox_hook(tmp_path, monkeypatch):
    """The already-installed 30-min cron calls --apply-decisions; the inbox
    runner must piggyback on it so schedule changes deploy via git alone,
    with no crontab reinstall on the box."""
    import sys
    sys.path.insert(0, str(ROOT / "ops" / "runner"))
    import runner

    (tmp_path / "ops" / "box").mkdir(parents=True)
    (tmp_path / "ops" / "box" / "run_inbox.sh").write_text("#!/bin/bash\n")
    (tmp_path / "ops" / "decisions.md").write_text("# just commentary\n")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "load", lambda p: {"tasks": [], "meta": {}})
    calls = []
    monkeypatch.setattr(runner.subprocess, "run",
                        lambda cmd, **kw: calls.append(cmd))

    runner.cmd_apply_decisions()
    assert calls and "run_inbox.sh" in calls[0][1]
