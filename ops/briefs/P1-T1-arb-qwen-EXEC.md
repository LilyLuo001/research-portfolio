# EXEC BRIEF — P1-T1 third-model arbitration (qwen, 140 items)

_Paste below the line into the box execution agent (the session that drives the
L1 runner on DashScope-provisioned qwen). This is a bounded, out-of-queue run:
a third independent model re-scores 140 contested deepseek v2-A verdicts so
seat C can adjudicate. It does NOT touch the deepseek output, does NOT fill a
full channel B, and does NOT `--complete` any queue task._

---

You are the L1 execution agent on the box. Task: run the **qwen** arbitration
batch `P1-T1-events-arb-qwen` and land its output. Read `CLAUDE.md` and
`ops/decisions.md` (2026-07-18 routing note) for context. The 140 items are the
contested/self-risky subset of the accepted deepseek v2-A T1 channel; rationale
is in `p1/t1_flagged_for_arb.md`.

## Hard constraints
- **Vendor = qwen only (alibaba family).** This is a cross-vendor tiebreaker
  against deepseek (channel A). It MUST NOT run on deepseek, kimi, or any
  Anthropic lane — running it on the same family as channel A collapses the
  independence the arbitration exists to provide. The spec already pins
  `worker: qwen`; do not change it.
- Do not edit `ops/l1/out/P1-T1-events.json` (deepseek v2-A, the primary) or any
  `.v1.json` / `.v2` archive. This run writes a NEW standalone file only.
- Do not run `runner.py --complete` on anything. Arbitration is outside the
  queue's two-strike bookkeeping.

## Pre-flight
1. `export QWEN_API_KEY=<key>` (DashScope).
2. Pin the model in `ops/box/.env`: `QWEN_MODEL=<the qwen3.x-plus / Qwen-Max id
   your key can call>`. Verify it resolves — a wrong id 404s and voids the run
   with an uninformative body. `models.py` reads `QWEN_MODEL` (default
   `qwen-max`).
3. Confirm outbound network to `dashscope.aliyuncs.com`.

## Run
```
python ops/l1/run_mopup.py P1-T1-events-arb-qwen --live
```
The batch is sentinel-fenced (S1=`RMCGX`, S2=`2022-04-22`, S3=`Ridgeline Funds
Trust`; synthetic excerpt, document-grounded). Chunks of 6 ride the full
sentinel set each; **any chunk that misses a sentinel voids the whole run** and
writes `ops/l1/out/P1-T1-events-arb-qwen.void.json` (inspect it, fix, re-run).
On success the answers land at `ops/l1/out/P1-T1-events-arb-qwen.json`.

## Coverage check (qwen, like gemini, can silently drop ids inside a passing
## chunk — so verify, don't assume)
```
python - <<'PY'
import json, re
spec = open('ops/l1/P1-T1-events-arb-qwen.yaml').read()
ids = re.findall(r'^- id:\s*["\']?([0-9-]{15,})', spec, re.M)
out = json.load(open('ops/l1/out/P1-T1-events-arb-qwen.json'))
ans = {k for k in out if k not in ('S1','S2','S3')}
missing = [i for i in ids if i not in ans]
def unparsed(v):
    if not isinstance(v, str): return False
    try: json.loads(v); return False
    except ValueError: return True
bad = [k for k in ans if unparsed(out[k])]
print(f'spec {len(ids)} | answered {len(ans)} | missing {len(missing)} | unparseable {len(bad)}')
print('missing:', missing)
print('unparseable:', bad)
PY
```
If `missing` is non-empty: copy `ops/l1/P1-T1-events-arb-qwen.yaml` to
`...-arb-qwen-r2.yaml`, keep only the missing items in `items:` (leave
`sentinels:` and header intact), run `run_mopup.py P1-T1-events-arb-qwen-r2
--live`, then merge the r2 answers into the main output. Repeat until
`missing == []`. (Same restart pattern used for the gemini resume.)

## Done
```
git add -f ops/l1/out/P1-T1-events-arb-qwen.json
git commit -m "P1-T1 qwen arbitration output (140 flagged items)"
git push
```
Report: how many of the 140 came back event vs no_event, whether the fence held
on the first try, the final `QWEN_MODEL` id used, and total ¥ spent (from
`_last_night.json` / budget log). Then stop — seat C runs the three-way diff
(deepseek v2-A vs qwen vs reference channel) and drives the flips/human-gate
calls. Do not act on the verdicts yourself.
