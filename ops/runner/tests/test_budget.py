"""budget.py caps: monthly ceiling, daily circuit-breaker, and per-vendor
sub-caps that are shared across worker tiers on the same billing key."""
import budget


def _reset(tmp_path):
    budget.LOG = tmp_path / "spend.jsonl"
    budget.MONTHLY_CAP = 100000.0      # generous, so the daily/vendor caps are what bite
    budget.DISPATCH_CEIL = 1.0
    budget.DAILY_CAP = 10.0
    budget.PER_VENDOR_DAILY = {"deepseek": 6.0}


def test_daily_circuit_breaker(tmp_path):
    _reset(tmp_path)
    ok, _ = budget.can_dispatch("kimi", 5)
    assert ok
    budget.log("kimi", 8)
    ok, why = budget.can_dispatch("kimi", 5)     # 8 + 5 = 13 > 10
    assert not ok and "daily cap" in why


def test_per_vendor_cap_shared_across_tiers(tmp_path):
    _reset(tmp_path)
    budget.log("deepseek", 5)                     # deepseek-chat
    ok, why = budget.can_dispatch("deepseek_r", 2)   # reasoner shares the DeepSeek key
    assert not ok and "deepseek" in why           # 5 + 2 = 7 > 6
    ok, _ = budget.can_dispatch("kimi", 2)        # different vendor -> only the daily cap
    assert ok


def test_monthly_ceiling(tmp_path):
    _reset(tmp_path)
    budget.MONTHLY_CAP = 10.0
    budget.DISPATCH_CEIL = 0.8
    budget.DAILY_CAP = 1e9                         # take the daily cap out of the way
    budget.log("kimi", 7)
    ok, why = budget.can_dispatch("kimi", 2)      # 7 + 2 = 9 > 0.8 * 10 = 8
    assert not ok and "monthly" in why


def test_report_has_today_and_vendor_lines(tmp_path):
    _reset(tmp_path)
    budget.log("qwen", 3)
    lines = budget.report()
    assert any("today" in ln for ln in lines)
    assert any("deepseek" in ln for ln in lines)   # per-vendor sub-cap surfaced
