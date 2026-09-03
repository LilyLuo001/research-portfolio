# Robustness and common-support audit — before any measure is selected

The separability gate (`ai_telework_overlap_receipt.json`) established that AI
exposure and remote-work feasibility are not inevitably near-collinear. It
established nothing about whether the residual variation is *usable*. This
audit decides that, and it runs **before** any exposure measure is chosen and
before any memo is written.

See `CORRECTION_2026-08-25.md` for what the gate was over-read to mean.

## Ten items

1. **Weighted and unweighted Pearson and Spearman.** Spearman matters because
   AIOE is roughly symmetric around zero while the Eloundou measures are
   bounded and right-skewed; a Pearson comparison across them is not
   scale-free.
2. **Alternative employment-weight years.** The current run uses OEWS 2021.
   Re-run on at least one pre-pandemic and one recent year. If the overlap
   ranking moves with the weight year, it is a composition artifact.
3. **Exact SOC crosswalk coverage and aggregation rules.** Report how many
   O*NET-SOC detail codes collapse into each 6-digit SOC, which occupations
   fail to match across sources, and what employment those failures carry.
4. **Correlations within 2-digit occupational groups.** The pooled correlation
   can be driven entirely by between-group differences. If within-group
   correlation is near zero everywhere, the two measures are separating
   occupation *families*, not tasks.
5. **Leave-one-major-group-out.** Drop each 2-digit group in turn and re-run.
   If separability depends on one group, it is that group's story.
6. **Residualised exposure distributions**, plus **the 25 largest positive and
   negative residuals by name**. This is the decisive item: if α's residual
   variation lives in a handful of peculiar occupations, it is not usable no
   matter what the R² says.
7. **Occupations with positive Dingel–Neiman only.** 62.7% of SOC codes are at
   exactly zero, so the full-sample split is `>0` versus `=0`. Re-run the
   comparison using quartiles among the positive-telework occupations, which
   is a genuine high-versus-low contrast.
8. **Power calculation on the real CPS structure** — actual occupation
   clusters, actual age cells, the interaction the design would estimate. Not
   a generic MDE.
9. **All four approved measures**, not the convenient subset. Webb (2020) and
   Frey–Osborne (2017) are in the approved robustness set and are absent from
   the current run.
10. **No novelty claim** until a targeted literature search confirms nobody has
    published this overlap. The commit message for the gate already asserted
    novelty; that assertion is unverified and should be treated as open.

## Status — 2026-08-25

Items 1, 3, 4, 5, 6 and 7 are implemented in `audit_common_support.py`; results
in `AUDIT_RESULTS.md`, receipt in `audit_common_support_receipt.json`, figures
in `figures/`. Two additions requested after this spec was written are folded
in: SOC-vintage sensitivity (every measure re-run on the common sample of all
four sources) and Kish effective sample size with within-group residual
variance under item 4.

| item | status |
|---|---|
| 1 Pearson + Spearman, weighted + unweighted | done |
| 2 alternative OEWS weight years | **BLOCKED** — only OEWS 2021 is in the repo and bls.gov is unreachable from the session (proxy `CONNECT` 403) |
| 3 crosswalk coverage and aggregation rules | done; the SOC 2010→2018 **repair** is BLOCKED for the same reason |
| 4 within 2-digit groups | done |
| 5 leave-one-major-group-out | done |
| 6 residual distributions + named occupations | done |
| 7 quartiles among positive-telework occupations | done, and the quartiles **do not exist** — the collapsed teleworkable share is 1.0 for 89.4% of positive occupations, so the audit reports a fully-vs-partially contrast and flags the degeneracy instead |
| 8 CPS power on the real structure | open |
| 9 Webb (2020) and Frey–Osborne (2017) | open — not obtained, needs network |
| 10 novelty verification | open |

Item 7's outcome revises this spec rather than satisfying it: the spec assumed
a `>0` subsample with interior variation. It does not have one.

## Decision rule, fixed now

The audit does **not** select a measure. It reports whether each measure's
residual variation is (a) large enough, (b) spread across ordinary occupations
rather than concentrated in outliers, and (c) powered in the CPS structure.

Measure choice is justified economically and prospectively — see
`CORRECTION_2026-08-25.md` §2 — and **every** measure is reported in the paper
regardless of which produces a result.
