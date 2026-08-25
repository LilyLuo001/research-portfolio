# C3 — Estimation: run the frozen tables once

*Prepend `C0_CONTEXT_PACK.md`. Requires `DESIGN_FREEZE_v1.md` committed.*

## The rule that governs this task

**The first run of each pre-specified table is the reported run.**

You will produce estimates that may be small, imprecise, or inconsistent across
measures. That is a result. It is written up as a result. You may not:

- try an alternative specification because the first was unfavourable
- change the `Post` date, the age bands, the clustering, or the controls
- drop a measure because it disagrees with the others
- select a window using the pre-trends you are testing

If you believe a frozen specification is genuinely wrong — not merely
unfavourable — stop, emit `NEED_HUMAN` with the argument, and do not run the
alternative yourself.

## Run, in this order

Write outputs to `dax/analysis/outcomes/`. **That directory is sealed: do not
commit anything in it until the owner creates the `v1.0-preregistered` tag.**
Commit the code and the receipts; the tables stay local until the tag.

**Table 1 — summary statistics.** Person-months, weighted, by age band and
exposure quartile. Include the unmatched share.

**Table 2 — primary TWFE.** `CHAPTER_SCOPE_v1.md` §6, primary measure,
clustered on occupation. Rows: baseline, + controls, + state × month, two-way
occupation × month clustering.

**Table 3 — all seven measures.** Identical specification, seven columns. No
measure is preferred. Where they disagree, the disagreement is the finding;
explain it from the measurement audit rather than resolving it by choice.

**Table 4 — vintage repair contrast.** Every measure unrepaired and repaired,
side by side. Report the change in the coefficient and in the estimation
sample. This is the table the chapter is built on.

**Table 5 — telework horse-race.** Exposure alone; telework alone; both. Report
the VIF for each pair, and the change in the exposure coefficient and its
standard error when telework enters.

**Table 6 — pre-trends and placebo.** Event-time coefficients relative to
2022-10. Plus a placebo `Post` at 2018-11 on the 2017-2019 window, which must
be null if the design is sound. **Report it whatever it shows.**

**Figures 1–4** per `CHAPTER_SCOPE_v1.md` §7.

## Reporting standard

For every table, record: N person-months, N occupation clusters, weighted N,
and the MDE from C2 alongside the point estimate. A coefficient without its
MDE is not interpretable in this chapter — the whole question is what the data
can support.

Where an estimate is indistinguishable from zero, write that. Do not write
"suggestive", "trending toward", or "marginally significant". Report the
interval.

## Definition of done

- Six tables, four figures, in `dax/analysis/outcomes/` — uncommitted.
- One receipt per table with N, clusters, weighted N, MDE, and the panel sha256.
- A one-page `RESULTS_NOTE.md`, committed, stating which branch of the
  `CHAPTER_SCOPE_v1.md` §3 pre-commitment the estimates fall into — informative
  or imprecise — and nothing more. No interpretation yet.
- `pytest -q` green.
