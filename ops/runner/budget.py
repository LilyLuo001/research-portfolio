#!/usr/bin/env python3
"""
budget.py — spend guardrails for the L1 cheap-model layer.

Three limits, checked before every live dispatch (dispatch.py calls can_dispatch):
  1. MONTHLY hard cap  — stop new dispatch above DISPATCH_CEIL of the month's ¥
     envelope (keeps 20% escalation reserve). The steady-state throttle.
  2. DAILY cap         — a circuit-breaker, NOT a throttle. Set generously (~3–5×
     the ~¥15/day steady spend) so normal bursty nights pass but a runaway loop
     (retry storm / batch re-fire) trips instead of burning the month overnight.
  3. PER-VENDOR daily  — sub-caps on the two vendors with real volume risk:
     DeepSeek (robustness-grid explosions) and Alibaba/Qwen (bulk annotation).

Currency: the repo's envelope is in ¥ (CNY); every value here is ¥ and every
`cost` you log must be ¥ too. To run the whole thing in USD instead, override the
caps via env (below) with USD numbers and log USD costs — budget.py just sums
whatever unit you feed it. USD annotations use ~7.15 CNY/USD.

NOTE: DAX-W4 capability-panel API spend is NOT governed here — it is project DATA
cost on its own budget line (arch §4), gated by the W0.5 feasibility ceiling.
"""
import json, os, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOG = ROOT / "ops" / "runner" / "spend_log.jsonl"

# --- caps (¥; override with env for a different currency/ceiling) -----------
MONTHLY_CAP = float(os.getenv("PORTFOLIO_MONTHLY_CAP", "500"))    # ~$70/mo
DISPATCH_CEIL = float(os.getenv("PORTFOLIO_DISPATCH_CEIL", "0.80"))
DAILY_CAP = float(os.getenv("PORTFOLIO_DAILY_CAP", "70"))         # ~$10/day circuit-breaker

# map each worker tier to its BILLING vendor (shared API key = shared sub-cap)
VENDOR_OF = {
    "deepseek": "deepseek", "deepseek_r": "deepseek",   # both on DEEPSEEK_API_KEY
    "kimi": "moonshot", "glm": "zhipu",
    "qwen": "alibaba", "gemini_free": "google",
}
# per-vendor DAILY sub-caps (¥). Vendors not listed are bounded only by DAILY_CAP.
PER_VENDOR_DAILY = {
    "deepseek": float(os.getenv("PORTFOLIO_DAILY_DEEPSEEK", "40")),   # ~$5.6
    "alibaba":  float(os.getenv("PORTFOLIO_DAILY_QWEN", "30")),       # ~$4.2 (Qwen bulk)
}


def _entries():
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]


def mtd_spend():
    m = datetime.date.today().strftime("%Y-%m")
    return sum(e["cost"] for e in _entries() if e["ts"].startswith(m))


def today_spend(vendor=None):
    """Total ¥ logged today, optionally filtered to one billing vendor."""
    d = datetime.date.today().isoformat()
    total = 0.0
    for e in _entries():
        if not e["ts"].startswith(d):
            continue
        if vendor and VENDOR_OF.get(e["worker"], e["worker"]) != vendor:
            continue
        total += e["cost"]
    return total


def can_dispatch(worker, est_cost):
    """Return (ok, reason). ok=False means this batch would breach a cap."""
    if mtd_spend() + est_cost > MONTHLY_CAP * DISPATCH_CEIL:
        return False, (f"monthly cap: MTD {mtd_spend():.1f} + {est_cost:.1f} "
                       f"> {DISPATCH_CEIL:.0%} of {MONTHLY_CAP:.0f}")
    if today_spend() + est_cost > DAILY_CAP:
        return False, (f"daily cap: today {today_spend():.1f} + {est_cost:.1f} "
                       f"> {DAILY_CAP:.0f}")
    vendor = VENDOR_OF.get(worker, worker)
    vcap = PER_VENDOR_DAILY.get(vendor)
    if vcap is not None and today_spend(vendor) + est_cost > vcap:
        return False, (f"daily {vendor} cap: {today_spend(vendor):.1f} + "
                       f"{est_cost:.1f} > {vcap:.0f}")
    return True, "ok"


def log(worker, est_cost):
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": datetime.datetime.utcnow().isoformat(),
                            "worker": worker, "cost": est_cost}) + "\n")


def report():
    """Lines for the evening digest's budget section."""
    lines = [
        f"- MTD: {mtd_spend():.1f} / {MONTHLY_CAP:.0f} "
        f"(new dispatch stops at {DISPATCH_CEIL:.0%} = {MONTHLY_CAP * DISPATCH_CEIL:.0f})",
        f"- today: {today_spend():.1f} / {DAILY_CAP:.0f} daily circuit-breaker",
    ]
    for vendor, cap in sorted(PER_VENDOR_DAILY.items()):
        lines.append(f"    - {vendor}: {today_spend(vendor):.1f} / {cap:.0f}")
    return lines


if __name__ == "__main__":
    print("\n".join(report()))
