# Y4 — Estimation: run the frozen tables once

*Prepend `Y0_CONTEXT_PACK.md`. Requires all seven gates PASS.*

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

## Preconditions — all five, verified, before opening any post-period file

1. `COVERAGE_RULE_PRESPEC_v1.md` committed.
2. Fine power grid run and **showing a gradient** — power falling through 80%
   in the 1–3% range. If it is flat near 100% across the grid, stop: the
   simulation engine is understating variance and must be diagnosed first.
3. MDE recomputed under a wild-cluster bootstrap.
4. Novelty gate (`RESEARCH_PLAN_v1.md` §2.4) answered.
5. `DESIGN_FREEZE_v1.md` committed and `v1.0-preregistered` tagged.

Opening a post-period outcome before all five is the one irreversible mistake
available in this project. The pre-registration is the chapter's contribution;
it cannot be reconstructed after the fact.

## Run, in this order

Write outputs to `dax/analysis/outcomes/`. **That directory is sealed: do not
commit anything in it until the owner creates the `v1.0-preregistered` tag.**
Commit the code and the receipts; the tables stay local until the tag.

**Every table below carries three coverage-rule columns** (A strict,
B sibling-imputed primary, C renormalized) and reports **wild-cluster bootstrap
p-values as primary inference**. Normal critical values are known to be
oversized in this design — 6.6% rejection at a nominal 5%.

**Table 1 — summary statistics.** Person-months, weighted, by age band and
exposure quartile. Include the unmatched share.

**Table 2 — primary TWFE.** `RESEARCH_PLAN_v1.md` §6, primary measure,
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

**Figures 1–4** per `RESEARCH_PLAN_v1.md` §7.

## Reporting standard

For every table, record: N person-months, N occupation clusters, weighted N,
and the bootstrap MDE alongside the point estimate. A coefficient without its
MDE is not interpretable in this chapter — the whole question is what the data
can support.

Where an estimate is indistinguishable from zero, write that — and write it as
an **informative** null, stating the MDE, so the reader can see the effect is
smaller than the published estimates rather than invisible to the data. That
distinction is the chapter's contribution and it must be explicit in the text,
not left to the reader.

Do not write "suggestive", "trending toward", or "marginally significant".
Report the interval. Never write "100% power" — write the MDE with its
bootstrap interval and the DGP's assumptions.

## Definition of done

- Six tables, four figures, in `dax/analysis/outcomes/` — uncommitted.
- One receipt per table with N, clusters, weighted N, MDE, and the panel sha256.
- A one-page `RESULTS_NOTE.md`, committed, stating which branch of the
  `RESEARCH_PLAN_v1.md` §3 pre-commitment the estimates fall into — informative
  or imprecise — and nothing more. No interpretation yet.
- `pytest -q` green.
