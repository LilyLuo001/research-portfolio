# PROMPT — finish P1-T1-events channel A (batches 36–90 + assembly)
_Paste everything below the line into a fresh Opus 4.8 Claude Code session in a
clone of this repo on the SCC._

---

You are seat C (P1-prime) finishing **P1-T1-events channel A** — EDGAR
mutual-fund→ETF conversion-event extraction. A previous Anthropic-lane session
completed 35 of 90 batches; you complete 36–90 and assemble the final output.
Read `CLAUDE.md` first; the five meta-rules bind you, especially: **no field
value that is not locatable in the excerpt in front of you** — anything from
memory is a hallucination and must be NA.

## Protocol
1. `python ops/runner/lease.py claim P1-T1-events --account C` (if the lease
   file shows seat C already holds it and TTL expired, re-claim; a live lease
   from another session → stop, report).
2. Branch `task/P1-T1-events`. Touch only `p1/` and `ops/l1/out/`.
3. Commit after every ~5 batches.

## The frozen extraction policy — read these files before ANY verdict
- `p1/t1_channelA_wip/POLICY.md` — the session policy (date fallbacks,
  asset_class rules, scope boundaries, flag conventions, _meta template).
  It is FROZEN: do not reinterpret it, apply it.
- 2–3 of `p1/t1_channelA_wip/rb_0{28,29,34}.jsonl` — match their format and
  judgment style exactly.
- The task rules are embedded verbatim in every spec item (fields: fund_name,
  family, mutual_fund_ticker, etf_ticker, announce_date, effective_date,
  asset_class ∈ {equity_US, equity_intl, fixed_income, other}, 
  AUM_at_conversion_USD, source_accession, source_url, confidence H/M/L;
  non-events → `{"no_event": true}`; contradictory dates for one fund →
  NEED_HUMAN, never average).

## Scope boundaries already adjudicated (do not re-litigate)
- Open-end mutual fund → ETF = EVENT (including completed/retrospective ones).
- MF→MF merger, ETF→ETF trust move, closed-end-fund→ETF, CEF share actions,
  Class C→A aging, plain XBRL prospectuses = no_event (CEF→ETF gets
  "FLAG for arb" in _evidence).
- Excerpts showing only financial highlights of an N-14 = no_event +
  "FLAG for B-channel/arb: transaction language not captured by excerpt windows".

## Workflow (deterministic, already built — do not rebuild)
- `p1/t1_channelA_wip/handoff/worklist.jsonl`: 1357 unique excerpt groups
  (hash → member filing ids with accession/url).
- `p1/t1_channelA_wip/handoff/cb_036.txt … cb_090.txt`: the condensed batches
  you still owe. For each: Read the file, write
  `p1/t1_channelA_wip/rb_NNN.jsonl` with one line per hash:
  `{"h": "<hash>", "v": {<event>|{"no_event": true}|{"events":[...]}}}` — every
  verdict carries `_evidence` quoting/paraphrasing the locator language.
- Do NOT skim: every hash in the batch file gets a line. After each batch,
  `python - <<'EOF'` check that rb line count == number of `=== <hash>`
  headers in the cb file.

## Assembly (after rb_090)
1. Write `p1/t1_channelA_wip/assemble.py`: for each of the 1418 spec item ids
   (parse `ops/l1/P1-T1-events.yaml` items), look up its excerpt hash via
   worklist membership, emit the per-hash verdict with `source_accession` and
   `source_url` filled from that member's own metadata. Output
   `ops/l1/out/P1-T1-events.json` as `{id: verdict, ..., "_meta": {...}}`.
2. `_meta` must contain: `channel: "A — re-routed deepseek→Anthropic L2/SCC
   Opus session (box L1 lane down since 2026-07-10, no ETA; precedent
   E2-T1-facts, E2-T9b)"`, 检索日期, `cross_vendor: "channel B = gemini_free
   (google) — independence preserved"`, and the three sentinel answers
   (answer S1/S2/S3 at the bottom of the spec YOURSELF, from the repo's
   house-verified facts, and record them; if any answer of yours disagrees
   with the spec's `expect`, VOID the run and emit NEED_HUMAN instead).
3. Verify: all 1418 ids present, JSON parses, no verdict lost
   (`len(set(ids))==1418`). `git add -f ops/l1/out/P1-T1-events.json`
   (out/ is gitignored; final channel outputs are force-added — see
   `ops/l1/README.md`).
4. `python ops/runner/lineage.py ops/l1/out/P1-T1-events.json
   ops/l1/P1-T1-events.yaml p1/t1_channelA_wip/handoff/worklist.jsonl`
5. Append one ROUTED note to `ops/decisions.md` (2 lines max, flag for owner
   review). Merge `task/P1-T1-events` → main.
6. **Do NOT run `runner.py --complete P1-T1-events`** — the task completes
   only after channel B lands and P1-T1-arb reconciles. Say so in your
   final report, run `make plan`, list what became READY, stop.
