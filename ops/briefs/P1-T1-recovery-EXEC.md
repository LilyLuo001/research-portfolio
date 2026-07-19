# EXEC BRIEF — P1-T1 recovery sweep (DeepSeek v4-pro, box)

_Paste everything below the line into the box execution agent. Three full-text
passes redeploy DeepSeek v4-pro over the raw filings to recover held / quarantined
/ mis-dropped conversions. All builders + mergers are already in the repo._

---

You are the DeepSeek execution agent on the box (BU SCC). Run the three-pass
P1-T1 recovery sweep. Read `CLAUDE.md`. Raw filings are local at
`p1/edgar_filings/{cik}_{accession}.htm` via `p1/edgar_filings/manifest.csv`.

## Hard constraints
- Worker = **deepseek** (channel-A family, model `deepseek-v4-pro`). Do NOT run
  these on qwen/gemini/Anthropic — this is channel-A recovery, not a new channel.
- Do NOT hand-edit `p1/t1_events_final.json` or `p1/events_merged.csv`. Only the
  merge scripts write them. Every recovered row must carry model evidence.
- Each pass is sentinel-fenced (Ridgeline S1/S2/S3). A tripped fence writes
  `<task>.void.json` and voids that run — inspect, fix, re-run. Passes are
  independent; if one fails the others still stand.
- After each merge, `events_merged.csv` re-assembles and `t1_full_audit.csv`
  refreshes automatically.

## Pre-flight
```
git pull
export DEEPSEEK_API_KEY=<key>           # confirm QWEN/GEMINI keys not needed here
python - <<'PY'
import pathlib; assert pathlib.Path("p1/edgar_filings/manifest.csv").exists(), "raw harvest missing"
print("raw harvest present")
PY
```
If any raw `.htm` are missing, run `python p1/fetch_heldback.py` (or the harvester)
first — the builders skip filings whose raw file is absent and report them.

## Pass 1 — effective dates for HELD events (surest win, ~100 conversions)
Events already confirmed; only the closing date is missing.
```
python p1/t1_arb/build_daterecover_spec.py
python ops/l1/run_mopup.py P1-T1-daterecover --live
python p1/t1_arb/merge_daterecover.py
```
If run_mopup reports fewer answers than spec items, re-run it once (chunk drops
are common); merge tolerates partials.

## Pass 2 — target-type confirmation for RECHECK rows (~63 conversions)
Proves the TARGET was an open-end/mutual fund (+ pulls its ticker as evidence).
```
python p1/t1_arb/build_recheck_spec.py
python ops/l1/run_mopup.py P1-T1-recheck --live
python p1/t1_arb/merge_recheck.py
```

## Pass 3 — full-text RE-CATEGORIZATION of the dropped no_event pool
Re-reads whole filings (root-cause fix for the narrow-window false negatives).
Default = MENTION + recheck_noevent. For the wider (bigger, lower-yield) sweep
that also re-reads MF_TO_MF, use the `--reasons` line shown second.
```
python p1/t1_arb/build_recat_spec.py
# wider:  python p1/t1_arb/build_recat_spec.py --reasons MENTION,MF_TO_MF,recheck_noevent
python ops/l1/run_mopup.py P1-T1-recat --live
python p1/t1_arb/merge_recat.py
```

## Validate + land
```
python ops/runner/contracts.py events_merged p1/events_merged.csv     # must print PASS
git add -f ops/l1/out/P1-T1-daterecover.json ops/l1/out/P1-T1-recheck.json ops/l1/out/P1-T1-recat.json
git add p1/t1_events_final.json p1/events_merged.csv p1/events_merged.csv.lineage.json \
        p1/t1_full_audit.csv p1/t1_full_audit.json p1/t1_arb/recovered_dates.json p1/t1_arb/arb_report.md
git commit -m "P1-T1 recovery sweep: dates + target-type + re-categorization (deepseek v4-pro)"
git push
```

## Report back
For each pass: how many items, fence held (Y/N) on first try, and the counts each
merge printed (dates recovered; recheck yes/no/unclear; recat flipped/confirmed).
Then the final `events_merged.csv` conversion count and total ¥ spent (from
`ops/l1/out/_last_night.json` / the budget log). Stop after pushing — seat C
re-audits what moved and refreshes the spotcheck sample for any newly-added rows.
Do not act on verdicts beyond what the merge scripts apply.
