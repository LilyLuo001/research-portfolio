
## 2026-07-09T09:30:01Z — inbox edf5f8fc093a @ git ff99b11
```
== where am I ==
ff99b11 Merge branch 'main' of https://github.com/LilyLuo001/research-portfolio
aaec175 Add bu-scc MCP server: local Claude Code hands on the SCC (ControlMaster, no passwords)
Python 3.6.8
== which kimi model ids can this key use ==
moonshot-v1-128k-vision-preview
moonshot-v1-auto
moonshot-v1-32k
moonshot-v1-32k-vision-preview
kimi-k2.7-code-highspeed
moonshot-v1-128k
moonshot-v1-8k-vision-preview
moonshot-v1-8k
kimi-k2.6
kimi-k2.5
kimi-k2.7-code
== clear stale strikes (billing-era + contested-sentinel voids) ==
cleared 0 recorded attempt(s) for E2-T1-facts-B
cleared 0 recorded attempt(s) for E2-T6b-nav
== live L1 pass (gemini is free + fence-fixed; kimi will ERROR until KIMI_MODEL is pinned — no strikes) ==
L1 driver — 6 ready L1 task(s), mode=LIVE
  ✖ P1-T0-crash-B        [ERROR] kimi: HTTPError: 404 Client Error: Not Found for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"Not found the model kimi-latest or Permission denied","type":"resource_not_found_error"}}
  ✓ DAX-W0.5-legwork     output already at DAX-W0.5-legwork.json — not re-sending (validate + --complete it, or delete the file / --force to re-run)
  ✖ E2-T1-facts          [ERROR] kimi: HTTPError: 404 Client Error: Not Found for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"Not found the model kimi-latest or Permission denied","type":"resource_not_found_error"}}
  ✓ E2-T1-facts-B        [DONE] gemini_free: 4 items + 2 sentinels OK (LIVE ¥0.000)
  · E2-T6b-nav           manual channel — run: python ops/l1/gemini_helper.py E2-T6b-nav
  ✖ E2-T9b-scenarios     [ERROR] kimi: HTTPError: 404 Client Error: Not Found for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"Not found the model kimi-latest or Permission denied","type":"resource_not_found_error"}}
  spent today: 0.501 / 70 daily cap (MTD 1.4 / 500)
  1 batch(es) written to ops/l1/out/ — validate + gate downstream before --complete.
[exit: 0]
```

## 2026-07-09T10:10:49Z — inbox f392df27ddbe @ git 25d22d4
```
== crontab BEFORE ==
# Portfolio always-on box schedule. Install with:  crontab ops/box/crontab
# Edit REPO below to your clone path. Times are the box's local time.
# The box holds NO Claude credential; it only runs L0 scripts + L1 cheap APIs.

# --- shared prologue: cd into the repo, load L1 keys, use the venv python ---
# (cron has a minimal env, so we set PATH and source the box .env explicitly)

# every 30 min: pull the latest code, then expire stale leases so abandoned
# tasks re-queue. The pull keeps the box current after merges (ff-only so it
# never conflicts with the box's own digest pushes; failures are logged, not fatal).
*/30 * * * *  cd $HOME/portfolio && git pull --ff-only -q origin main >> ops/box/cron.log 2>&1; cd $HOME/portfolio && .venv/bin/python ops/runner/runner.py --reap >> ops/box/cron.log 2>&1

# 02:00 nightly: run the overnight L1 batch layer (sentinel-fenced, budget-capped)
0 2 * * *  cd $HOME/portfolio && set -a && . ops/box/.env && set +a && .venv/bin/python ops/runner/dispatch.py --smoke >> ops/box/cron.log 2>&1

# 21:00 nightly: write the evening digest, then push briefs + digest to GitHub
0 21 * * *  cd $HOME/portfolio && .venv/bin/python ops/runner/runner.py --digest >> ops/box/cron.log 2>&1 && git add ops/briefs ops/digest && git commit -q -m "box: nightly digest $(date +\%F)" && git push -q origin HEAD:main >> ops/box/cron.log 2>&1

# NOTE: models.py is wired for live dispatch. The 02:00 line runs --smoke as a
# nightly health check; run real batches with:
#   dispatch.py --worker <w> --items <batch.jsonl> --live --cost <N> --out <answers.json>
# Once a per-task L1 driver exists (iterate the plan's ready L1 set -> build items
# -> dispatch -> --complete on sentinel pass), swap the 02:00 line for it.
# portfolio-box (managed by bootstrap.sh)
*/30 * * * *  cd /usr3/graduate/qluo/portfolio && /usr3/graduate/qluo/portfolio/.venv/bin/python ops/runner/runner.py --apply-decisions >> ops/box/cron.log 2>&1; cd /usr3/graduate/qluo/portfolio && /usr3/graduate/qluo/portfolio/.venv/bin/python ops/runner/runner.py --reap >> ops/box/cron.log 2>&1
0 2 * * *     cd /usr3/graduate/qluo/portfolio && set -a && . ops/box/.env && set +a && /usr3/graduate/qluo/portfolio/.venv/bin/python ops/runner/l1_driver.py --live >> ops/box/cron.log 2>&1
0 21 * * *    cd /usr3/graduate/qluo/portfolio && /usr3/graduate/qluo/portfolio/.venv/bin/python ops/runner/runner.py --digest >> ops/box/cron.log 2>&1 && git add ops/briefs ops/digest ops/runner/state.json ops/decisions.md && git commit -q -m "box: nightly digest $(date +\%F)" && git push -q origin HEAD:main >> ops/box/cron.log 2>&1
# portfolio-box (managed by bootstrap.sh)-end
== strip all portfolio cron lines (both duplicate sets) ==
== reinstall the single managed block (new flock'd cron_*.sh) ==

[1m==> box bootstrap complete.[0m
Next:
  1. Fill L1 keys:   $EDITOR /usr3/graduate/qluo/portfolio/ops/box/.env    (then re-run --smoke)
  2. Go live:        wire the real POST in ops/runner/models.py, run one live batch
  3. Schedule it:    INSTALL_CRON=1 ops/box/bootstrap.sh        (if you skipped cron above)
  4. Daily:          make plan   (morning)  /   make digest  (evening)
The box holds no Claude credential; L2 work happens in the official apps on your seats.
== crontab AFTER ==
# Portfolio always-on box schedule. Install with:  crontab ops/box/crontab
# Edit REPO below to your clone path. Times are the box's local time.
# The box holds NO Claude credential; it only runs L0 scripts + L1 cheap APIs.

# --- shared prologue: cd into the repo, load L1 keys, use the venv python ---
# (cron has a minimal env, so we set PATH and source the box .env explicitly)

# every 30 min: pull the latest code, then expire stale leases so abandoned
# tasks re-queue. The pull keeps the box current after merges (ff-only so it
# never conflicts with the box's own digest pushes; failures are logged, not fatal).

# 02:00 nightly: run the overnight L1 batch layer (sentinel-fenced, budget-capped)

# 21:00 nightly: write the evening digest, then push briefs + digest to GitHub

# NOTE: models.py is wired for live dispatch. The 02:00 line runs --smoke as a
# nightly health check; run real batches with:
#   dispatch.py --worker <w> --items <batch.jsonl> --live --cost <N> --out <answers.json>
# Once a per-task L1 driver exists (iterate the plan's ready L1 set -> build items
# -> dispatch -> --complete on sentinel pass), swap the 02:00 line for it.
# portfolio-box (managed by bootstrap.sh)
*/30 * * * *  cd /usr3/graduate/qluo/portfolio && bash ops/box/cron_halfhour.sh >> ops/box/cron.log 2>&1
0 2 * * *     cd /usr3/graduate/qluo/portfolio && bash ops/box/cron_night.sh >> ops/box/cron.log 2>&1
0 21 * * *    cd /usr3/graduate/qluo/portfolio && bash ops/box/cron_evening.sh >> ops/box/cron.log 2>&1
# portfolio-box (managed by bootstrap.sh)-end
== pin KIMI_MODEL=kimi-k2.6 (from /models discovery; manual specs K2.6) ==
KIMI_MODEL=kimi-k2.6
== clear stale strikes ==
cleared 2 recorded attempt(s) for E2-T6b-nav
cleared 1 recorded attempt(s) for E2-T1-facts-B
== live L1 pass on the pinned model ==
L1 driver — 6 ready L1 task(s), mode=LIVE
  ✖ P1-T0-crash-B        [ERROR] kimi: HTTPError: 400 Client Error: Bad Request for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"invalid temperature: only 1 is allowed for this model","type":"invalid_request_error"}}
  ✓ DAX-W0.5-legwork     output already at DAX-W0.5-legwork.json — not re-sending (validate + --complete it, or delete the file / --force to re-run)
  ✖ E2-T1-facts          [ERROR] kimi: HTTPError: 400 Client Error: Bad Request for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"invalid temperature: only 1 is allowed for this model","type":"invalid_request_error"}}
  ✓ E2-T1-facts-B        output already at E2-T1-facts-B.json — not re-sending (validate + --complete it, or delete the file / --force to re-run)
  · E2-T6b-nav           manual channel — run: python ops/l1/gemini_helper.py E2-T6b-nav
  ✖ E2-T9b-scenarios     [ERROR] kimi: HTTPError: 400 Client Error: Bad Request for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"invalid temperature: only 1 is allowed for this model","type":"invalid_request_error"}}
  spent today: 0.501 / 70 daily cap (MTD 1.4 / 500)
  0 batch(es) written to ops/l1/out/ — validate + gate downstream before --complete.
== capture DONE outputs for off-box review ==
== state after ==
{
  "completed": [
    "SH-runner",
    "SH-econlib"
  ],
  "gates_cleared": [],
  "gates_failed": [],
  "attempts": {},
  "_note": "SH-runner and SH-econlib are merged to main and their gates pass (selfcheck + econlib_smoke contract). E2-T6a is NOT marked complete: build_panel.py is synthetic-input scaffolding and its real upstream producers (E2-T2/T3/T5) are still open."
}[exit: 0]
```

## 2026-07-09T10:55:18Z — inbox c9659bf9a3ff @ git aaafa28
```
== python venv upgrade (3.6.8 -> newest module python3) ==
newest python3 module: none found
== live L1 pass (kimi-k2.6, temperature fix from this same pull) ==
L1 driver — 6 ready L1 task(s), mode=LIVE
  ✓ P1-T0-crash-B        output already at P1-T0-crash-B.json — not re-sending (validate + --complete it, or delete the file / --force to re-run)
  ✓ DAX-W0.5-legwork     output already at DAX-W0.5-legwork.json — not re-sending (validate + --complete it, or delete the file / --force to re-run)
  ✖ E2-T1-facts          [VOID-SENTINEL] kimi: reply had no parseable JSON answer-map (all sentinels void) — raw reply kept at E2-T1-facts.void.json — batch discarded
recorded attempt 3 for E2-T1-facts — ESCALATE (shows in plan/digest)
  ✓ E2-T1-facts-B        output already at E2-T1-facts-B.json — not re-sending (validate + --complete it, or delete the file / --force to re-run)
  · E2-T6b-nav           manual channel — run: python ops/l1/gemini_helper.py E2-T6b-nav
  ✖ E2-T9b-scenarios     [VOID-SENTINEL] kimi: sentinels failed ['S1', 'S2'] — raw reply kept at E2-T9b-scenarios.void.json — batch discarded
recorded attempt 4 for E2-T9b-scenarios — ESCALATE (shows in plan/digest)
  spent today: 2.279 / 70 daily cap (MTD 3.2 / 500)
  0 batch(es) written to ops/l1/out/ — validate + gate downstream before --complete.
== capture any new DONE outputs ==
== night report ==
{
  "date": "2026-07-09",
  "live": true,
  "results": {
    "P1-T0-crash-B": "HAS-OUTPUT",
    "DAX-W0.5-legwork": "HAS-OUTPUT",
    "E2-T1-facts": "VOID-SENTINEL",
    "E2-T1-facts-B": "HAS-OUTPUT",
    "E2-T6b-nav": "MANUAL",
    "E2-T9b-scenarios": "VOID-SENTINEL"
  }
}[exit: 0]
```

## 2026-07-09T14:00:02Z — inbox 7b34518c7358 @ git eb3ca77
```
== python module diagnostics (payload d found none) ==
no module command in this shell
/share/pkg
/share/pkg.7
/share/pkg.8
== complete P1-T0-crash-B (reviewed — see payload header) ==
marked complete: P1-T0-crash-B  (state.json is git-tracked — commit it with your merge)
== quarantine weak-model DAX output ==
== clear parked strikes (infra artifacts + stall failures now split-retried) ==
cleared 1 recorded attempt(s) for E2-T1-facts
cleared 4 recorded attempt(s) for E2-T9b-scenarios
== live pass: split per-item retries on kimi-k2.6 ==
L1 driver — 5 ready L1 task(s), mode=LIVE
  ✖ DAX-W0.5-legwork     [VOID-SENTINEL] kimi: chunk 1/3: reply had no parseable JSON answer-map (all sentinels void) — raw reply kept at DAX-W0.5-legwork.void.json — batch discarded
recorded attempt 1 for DAX-W0.5-legwork
  · E2-T1-facts          manual channel — run: python ops/l1/gemini_helper.py E2-T1-facts
  ✓ E2-T1-facts-B        output already at E2-T1-facts-B.json — not re-sending (validate + --complete it, or delete the file / --force to re-run)
  · E2-T6b-nav           manual channel — run: python ops/l1/gemini_helper.py E2-T6b-nav
  · E2-T9b-scenarios     manual channel — run: python ops/l1/gemini_helper.py E2-T9b-scenarios
  spent today: 3.068 / 70 daily cap (MTD 4.0 / 500)
  0 batch(es) written to ops/l1/out/ — validate + gate downstream before --complete.
== capture outputs (incl. per-item partials for provenance) ==
{
  "date": "2026-07-09",
  "live": true,
  "results": {
    "DAX-W0.5-legwork": "VOID-SENTINEL",
    "E2-T1-facts": "MANUAL",
    "E2-T1-facts-B": "HAS-OUTPUT",
    "E2-T6b-nav": "MANUAL",
    "E2-T9b-scenarios": "MANUAL"
  }
}[exit: 0]
```

## 2026-07-10T02:00:03Z — inbox e38a846d2b71 @ git 8ad1868
```
== python3 modules visible from a login shell ==
python3/3.9.9
python3/3.10.5
python3/3.10.12
python3/3.12.4
python3/3.13.8
picked: python3/3.13.8
Python 3.13.8
deps OK
selfcheck PASSED — 59 tasks, 11 contracts, DAG + vendor independence clean.
VENV SWAPPED to Python 3.13.8 (old kept at .venv-old)
== sanity: the cron's python still works ==
cron python OK: 3.13.8
== P1 EDGAR harvester ==
NEED_HUMAN: EDGAR_CONTACT is not set — add 'EDGAR_CONTACT=<your email>'
to ops/box/.env (box-local, gitignored; SEC fair-use requires it).
Harvester NOT started; this payload re-checks on nothing — bump the
inbox-version after adding the var, or start by hand:
  setsid nohup .venv/bin/python p1/fetch_edgar_filings.py >> p1/edgar_filings/harvest.log 2>&1 &
[exit: 0]
```

## 2026-07-10T02:03:25Z — inbox e38a846d2b71 @ git aef5d3f
```
ops/box/inbox.sh: line 16: .venv/bin/python: No such file or directory
== python3 modules visible from a login shell ==
picked: none
SKIP: no python3 module found; needs an interactive look at 'module avail' on the SCC
== sanity: the cron's python still works ==
ops/box/inbox.sh: line 42: .venv/bin/python: No such file or directory
== P1 EDGAR harvester ==
NEED_HUMAN: EDGAR_CONTACT is not set — add 'EDGAR_CONTACT=<your email>'
to ops/box/.env (box-local, gitignored; SEC fair-use requires it).
Harvester NOT started; this payload re-checks on nothing — bump the
inbox-version after adding the var, or start by hand:
  setsid nohup .venv/bin/python p1/fetch_edgar_filings.py >> p1/edgar_filings/harvest.log 2>&1 &
[exit: 0]
```
