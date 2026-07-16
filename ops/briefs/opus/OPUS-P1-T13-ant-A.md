# PROMPT — P1-T13-ant channel A (ANT / semi-transparent control event set)
_Paste below the line into a fresh Opus 4.8 Claude Code session in a repo
clone on the SCC. Run AFTER (or parallel to, in a separate session from)
OPUS-P1-T1-events-A-finish.md._

---

You are seat C (P1-prime) executing **P1-T13-ant channel A**: extraction of
the semi-transparent/ANT active-ETF control event set from 414 EDGAR filings
(amendment 修订4). The spec is `ops/l1/P1-T13-ant.yaml` (417 items incl. some
multi-member; worker was deepseek, re-routed to this Anthropic/SCC lane —
box L1 lane down since 2026-07-10; precedent E2-T1-facts). Channel B
(`P1-T13-ant-B.yaml`, gemini_free/google) stays on its own lane, so
cross-vendor independence holds. Read `CLAUDE.md` first; meta-rule 1 binds
every field: locatable in the excerpt or NA.

## Protocol
`python ops/runner/lease.py claim P1-T13-ant --account C` → branch
`task/P1-T13-ant` → touch only `p1/` and `ops/l1/out/` → commit every ~5
batches.

## Schema (per the rules block embedded in every item — 修订4 T13)
Same fields as T1 **plus two columns**:
`disclosure_regime` ∈ {daily_full, semi_transparent} and
`proxy_basket_type` (e.g. ActiveShares/blind trust, Fidelity/NYSE proxy
basket "Portfolio Reference Basket", Blue Tractor Shielded Alpha, Natixis/
NYSE AMS — use the filing's own term, verbatim-derived, never inferred).
Scope: active ETFs **launched or converted since 2019-11** under
semi-transparent exemptive relief, AND regime-switch events
(semi_transparent → daily_full conversions, e.g. the 2025 Putnam
transparency conversions — those ARE events for this set). Non-relevant
filings → `{"no_event": true}`. Every verdict carries `_evidence`.

## Method (reuse P1's deterministic tooling — do not invent a new one)
1. Adapt `p1/t1_channelA_wip/handoff/build_worklist.py` and `condense.py` to
   this spec (change input path to `ops/l1/P1-T13-ant.yaml`, output prefix
   `p1/t13_channelA_wip/`). For condense keywords ADD the T13 phrases:
   `semi-transparent`, `proxy portfolio|Portfolio Reference Basket|Tracking
   Basket|Guardrail`, `ActiveShares`, `Shielded Alpha`, `transparency
   conversion|convert.{0,40}(daily|full) (portfolio )?(holdings|
   transparency)`, `Rule 6c-11`, `exemptive order`.
2. Dedupe → condensed batches → read each batch → per-hash verdict JSONL,
   exactly the T1 workflow (`p1/t1_channelA_wip/POLICY.md` conventions apply;
   its date-fallback ladder — board date, else document date, else filed
   date — carries over).
3. Note: many T13 excerpts are SAI boilerplate (e.g. Neuberger Berman SAIs)
   with no event language — those are `no_event`. The signal items are 497/
   497K supplements and N-1A filings that state the semi-transparent
   structure at launch or announce a transparency conversion.
4. Assemble `ops/l1/out/P1-T13-ant.json` (id → verdict for ALL spec ids +
   `_meta` with the re-route note, 检索日期, cross-vendor line, and your own
   answers to sentinels S1/S2/S3 at the bottom of the spec; any sentinel
   mismatch with `expect` → VOID + NEED_HUMAN). `git add -f` the output,
   emit lineage (`python ops/runner/lineage.py ...` with the spec as input),
   2-line ROUTED note in ops/decisions.md, merge to main.
5. **Do NOT `--complete`** — completion waits on channel B + arb. Report,
   `make plan`, stop.
