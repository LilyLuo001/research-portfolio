#!/usr/bin/env python3
"""
budget.py — hard-stops L1 dispatch at 80% of the monthly ¥ envelope; keeps 20%
as escalation reserve. Logs each call's cost estimate; daily line goes in the
digest. Cost overruns are a breakdown mode too (arch §3 rule 7).

Envelope (arch §4): DeepSeek 120–220, Kimi 80–150, GLM/Qwen 40–80,
reserve 50–100, Gemini 0. Total inside ¥300–500.
NOTE: DAX-W4 capability-panel API spend is NOT in this envelope — it's project
DATA cost, own budget line, gated by W0.5 feasibility ceiling.
"""
import json, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
LOG = ROOT / "ops" / "runner" / "spend_log.jsonl"
MONTHLY_CAP = 500       # ¥, upper bound of the envelope
DISPATCH_CEIL = 0.80    # stop new L1 dispatch above this fraction

def mtd_spend():
    if not LOG.exists(): return 0.0
    m = datetime.date.today().strftime("%Y-%m")
    return sum(json.loads(l)["cost"] for l in LOG.read_text().splitlines()
               if l and json.loads(l)["ts"].startswith(m))

def can_dispatch(est_cost):
    return (mtd_spend() + est_cost) <= MONTHLY_CAP * DISPATCH_CEIL

def log(worker, est_cost):
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": datetime.datetime.utcnow().isoformat(),
                            "worker": worker, "cost": est_cost}) + "\n")
