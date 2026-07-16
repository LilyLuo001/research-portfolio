# PROMPT — DAX-W2-data (frozen public data backbone)
_Paste below the line into a fresh Opus 4.8 Claude Code session on the SCC —
this is the right venue: bulk downloads, storage, long-running builds.
Pre-flight owner items: IPUMS-CPS API key exported as `IPUMS_API_KEY` (owner
registers at ipums.org); confirm outbound network from the node you run on.
Runs in parallel with DAX-W1-memo (different files, same seat A — use one
session at a time per lease, or lease W2 while W1 awaits PI feedback)._

---

You are the Data Engineering Agent for the DAX project (seat A). Read
`CLAUDE.md`, `dax/CLAUDE.md`, `docs/DAX_Execution_Plan_with_AI_Agents.md`
§W2, `docs/DAX_Amendment_v1_1.md`, `ops/contracts/dax_built_backbone.yaml`
(your output contract), and `ops/briefs/DAX-W5-index.md` (downstream
consumer). **Hard rule from the queue: pre-period construction only until
GATE1 — build NO post-event outcome aggregates by dose. Never open
`dax/analysis/outcomes/`.**

## Protocol
`python ops/runner/lease.py claim DAX-W2-data --account A` → branch
`task/DAX-W2-data` → touch only `dax/`. Raw pulls land immutable in
`dax/data_raw/` with checksums; every built file in `dax/data_built/` has a
lineage JSON (`python ops/runner/lineage.py <built> <raw inputs...>`).
Commit per component; PR-sized commits with unit tests (row counts, join
coverage, weight sums) + a short data note each.

## Components (execution plan §W2 verbatim)
1. **O*NET** (2021 vintage frozen primary; retain annual vintages for the
   live variant): task statements, importance/frequency ratings,
   consequence-of-error descriptors. Task-level time shares =
   importance×frequency normalized within occupation; document the proration
   formula. Map consequence-of-error into low/medium/high tiers.
2. **OEWS** mean wages by SOC, 2021 primary + 2019 alternative; prorate to
   tasks via time shares → w (wage cost per completed task); flag
   occupations where 2019 vs 2021 bases diverge > [X]% ([PI-DECISION] the
   threshold; hospitality/health care expected).
3. **IPUMS-CPS** via API: monthly microdata Nov 2021→latest (employment,
   hours, wages, occupation, industry, age, education, unemployment-reason,
   search-duration) + March ASEC with firm size. Build the ages-22–25
   extract with person weights. **Pre-period only for anything dose-indexed.**
4. **Crosswalks**: CPS occ ↔ O*NET-SOC, many-to-many with employment
   weights; within-CPS-code dose-dispersion diagnostics as a
   measurement-quality table.
5. **Static scores**: Felten-Raj-Seamans, Eloundou et al., Webb on the
   frozen SOC vintage; ensemble deciles; non-AI characteristics file (wage,
   education shares, routine-task intensity, import penetration).
6. **Interest-rate sensitivity**: two candidate occupation-level measures
   (e.g. industry duration/leverage exposure weighted to occupations),
   documented — [PI-DECISION] which one is primary.
7. **API price histories**: dated per-token price panel per model from
   published sources; every price change = a dated row + source URL,
   verified against two sources. Seed from the verified rows in
   `dax/memo/w05_legwork_2026-07-10.md` (cite, don't retype); UNKNOWN cells
   stay UNKNOWN. Meta-rule 1 applies to every number in this panel.

## Done
`python ops/runner/contracts.py dax_built_backbone dax/data_built/` PASS +
codebook + all lineage present → merge to main →
`python ops/runner/runner.py --complete DAX-W2-data` → report which tasks
flipped READY (expect DAX-W3-mapA) → `make plan`, stop. If a source is
paywalled/blocked from SCC, emit `NEED_HUMAN: <source, exact URL, what to
download>` and continue with the other components — never substitute a
remembered table.
