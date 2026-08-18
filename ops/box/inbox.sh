#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-08-14-a
#
# Payload a — W2 price panel, Channel A (archived official pricing pages).
#
# Why this runs here and not in a seat session: web.archive.org is blocked by
# the Claude Code web sandbox's egress policy, so the corroboration channel
# cannot run from a seat. Channel B (git history of a third-party price table)
# already ran there and produced 71 interval rows, all `single_channel`. One
# channel can never certify a price, so every row stays unusable for the
# primary analysis until this payload confirms or contradicts it.
#
# Cost control: snapshots are cached on disk (dax/data_raw/_wayback_cache/,
# git-ignored) because many rows resolve against the same captures — without it
# the sweep is ~850 fetches and blows the 25-minute inbox timeout. The run is
# also resumable: rows already carrying a Channel-A verdict are carried over,
# so if the time budget stops the sweep early, RE-ARM THIS PAYLOAD (change the
# version marker above) and the next cycle continues where it left off.
#
# Idempotent. Safe to re-run. Touches no outcome data; the pre-registration
# seal is not involved.

echo "== host identity =="
echo "$(hostname) : $(pwd) : $(git rev-parse --short HEAD)"

echo "== preflight: can this host reach the archive? =="
if curl -sS -o /dev/null -w "cdx http=%{http_code}\n" --max-time 30 \
     "http://web.archive.org/cdx/search/cdx?url=openai.com/pricing&output=json&limit=1"; then
  echo "archive reachable"
else
  echo "ARCHIVE UNREACHABLE FROM THE BOX — stopping."
  echo "Channel A cannot run anywhere we currently control. Report this in the"
  echo "digest; do NOT mark any price row verified on Channel B alone."
  exit 0
fi

echo "== channel B mirror (blobless clone on first run; ~83MB, then incremental) =="
.venv/bin/python - <<'PYEOF'
import pathlib, sys
sys.path.insert(0, "dax/w2/prices")
import channel_git
mirror = channel_git.ensure_mirror(pathlib.Path("dax/data_raw/_litellm_mirror"))
print("mirror ready:", mirror)
PYEOF

echo "== build price panel, both channels (Channel A capped at 600s) =="
.venv/bin/python dax/w2/prices/build_price_panel.py \
    --time-budget 600 --verbose 2>&1 | tail -30

echo "== contract =="
.venv/bin/python ops/runner/contracts.py price_histories dax/data_built/price_histories.csv

echo "== two-channel status counts =="
.venv/bin/python - <<'PYEOF'
import collections, csv
rows = list(csv.DictReader(open("dax/data_built/price_histories.csv")))
print("panel rows:", len(rows))
for status, n in sorted(collections.Counter(r["price_status"] for r in rows).items()):
    print(f"  price_status={status:16} {n}")
for status, n in sorted(collections.Counter(r["channel_web_status"] for r in rows).items()):
    print(f"  channel_web={status:17} {n}")
conflicts = [r for r in rows if r["price_status"] == "conflict"]
if conflicts:
    print("\nCONFLICTS — archived official page disagrees with the git table.")
    print("These are human-gate items. Do not resolve them by picking a side.")
    for r in conflicts[:20]:
        print(f"  {r['model_id']} {r['price_kind']} ${r['usd_per_1m']} "
              f"<= {r['effective_date_latest']} :: {r['notes'][:110]}")
PYEOF

echo "== next action =="
echo "If 'time budget reached' appeared above, re-arm: bump inbox-version and"
echo "merge to main; the next cycle resumes from the cached verdicts."
echo "When every row is verified/conflict, W2's price half is done and the"
echo "registry's pending_second_date_locator rows can be re-adjudicated."
