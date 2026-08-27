"""The daily circuit breaker must fire in every hour, not twenty of them.

log() stamps entries in UTC. mtd_spend() and today_spend() used to filter on
the LOCAL date. Wherever the two disagree, today_spend() matched nothing and
returned 0.0, so `today_spend() + est_cost > DAILY_CAP` compared est_cost
against the cap alone and the breaker did not fire -- for four hours a day on
US Eastern, more on other offsets, and cleanly the rest of the time. A guard
that works twenty hours in twenty-four is the worst kind: it reads as flaky
and gets trusted.

Found by an SCC seat at 2026-08-24T20:20:50-0400, with the log already
stamping 2026-08-25.
"""
import datetime
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "budget", ROOT / "ops" / "runner" / "budget.py")
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)


@pytest.fixture
def log(tmp_path, monkeypatch):
    path = tmp_path / "spend_log.jsonl"
    monkeypatch.setattr(B, "LOG", path)
    return path


def write(path, entries):
    path.write_text("".join(json.dumps(e) + "\n" for e in entries))


def test_the_breaker_fires_during_the_utc_local_split(log, monkeypatch):
    """The exact window the seat was standing in.

    Spend is logged under the UTC date. If the filter used the local date it
    would see nothing, today_spend() would be 0.0, and a dispatch that should
    breach the cap would be allowed.
    """
    utc_now = datetime.datetime(2026, 8, 25, 0, 20, 50,
                                tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(B, "_utc_now", lambda: utc_now)
    write(log, [{"ts": "2026-08-25T00:10:00+00:00", "worker": "deepseek",
                 "cost": B.DAILY_CAP}])

    assert B.today_spend() == pytest.approx(B.DAILY_CAP)
    ok, reason = B.can_dispatch("deepseek", 1.0)
    assert ok is False
    assert "daily cap" in reason


def test_naive_utc_stamps_already_in_the_log_still_match(log, monkeypatch):
    """The log is append-only and holds entries written by the old code."""
    utc_now = datetime.datetime(2026, 8, 25, 0, 20, 50,
                                tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(B, "_utc_now", lambda: utc_now)
    write(log, [{"ts": "2026-08-25T00:10:00.123456", "worker": "deepseek",
                 "cost": 5.0}])
    assert B.today_spend() == pytest.approx(5.0)


def test_yesterdays_spend_does_not_count_toward_today(log, monkeypatch):
    """The complement: the fix must not make the breaker fire when it shouldn't."""
    utc_now = datetime.datetime(2026, 8, 25, 0, 20, 50,
                                tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(B, "_utc_now", lambda: utc_now)
    write(log, [{"ts": "2026-08-24T23:50:00+00:00", "worker": "deepseek",
                 "cost": B.DAILY_CAP}])
    assert B.today_spend() == pytest.approx(0.0)
    assert B.can_dispatch("deepseek", 1.0)[0] is True


def test_the_per_vendor_subcap_uses_the_same_clock(log, monkeypatch):
    """It reads today_spend(vendor), so it inherited the same blind window."""
    utc_now = datetime.datetime(2026, 8, 25, 0, 20, 50,
                                tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(B, "_utc_now", lambda: utc_now)
    cap = B.PER_VENDOR_DAILY["deepseek"]
    write(log, [{"ts": "2026-08-25T00:00:00+00:00", "worker": "deepseek_r",
                 "cost": cap}])
    # deepseek_r bills to the same vendor key as deepseek.
    assert B.today_spend("deepseek") == pytest.approx(cap)
    ok, reason = B.can_dispatch("deepseek", 1.0)
    assert ok is False


def test_month_to_date_uses_utc_too(log, monkeypatch):
    """Same split, rarer trigger: it only misfires across a month boundary,
    which is precisely when a monthly cap matters most."""
    utc_now = datetime.datetime(2026, 9, 1, 0, 30, 0,
                                tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(B, "_utc_now", lambda: utc_now)
    write(log, [{"ts": "2026-08-31T23:00:00+00:00", "worker": "kimi", "cost": 400.0},
                {"ts": "2026-09-01T00:10:00+00:00", "worker": "kimi", "cost": 5.0}])
    # August spend must not count against September.
    assert B.mtd_spend() == pytest.approx(5.0)


def test_log_writes_an_offset_aware_utc_stamp(log, monkeypatch):
    utc_now = datetime.datetime(2026, 8, 25, 0, 20, 50,
                                tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(B, "_utc_now", lambda: utc_now)
    B.log("deepseek", 1.5)
    entry = json.loads(log.read_text().splitlines()[0])
    assert entry["ts"].startswith("2026-08-25T")
    assert entry["ts"].endswith("+00:00")


def test_no_local_clock_call_survives_in_the_module():
    """The regression guard. A single date.today() reintroduces the whole bug.

    Parsed rather than grepped: the module's own comment explains why utcnow()
    was removed, and a substring check reads that prose as code.
    """
    import ast

    source = (ROOT / "ops" / "runner" / "budget.py").read_text(encoding="utf-8")
    banned = {"today", "utcnow", "now"}
    offenders = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in banned:
            continue
        if func.attr == "now":
            # datetime.now(timezone.utc) is the correct call; a bare now() is not.
            if node.args or node.keywords:
                continue
        offenders.append(f"{func.attr}() at line {node.lineno}")
    assert not offenders, (
        "budget.py must read one clock, UTC. Local or naive calls found: "
        + ", ".join(offenders))
