# W2 decision — the O*NET task weight, and what it must not be called

**Date:** 2026-08-24. **Status:** decision taken on delegated authority,
recorded for owner counter-signature. Resolves the four questions in
`W2_TIMESHARE_BLOCKER_2026-08-24.md`.

## The decision in one line

**Adopt the weight definition already in the repository, rename it so it stops
claiming to be a time share, and carry two robustness variants.** Do not invent
a new definition.

## Why "invent a definition" was the wrong question

The blocker memo asked which of FT, IM or RT should define the weight, as
though the choice were open. It is not. `dax/w2/crosswalk/build_legacy_onet_fallback.py`
already computes one, and it is already embedded in results:

```python
frequency_score = sum(k * v for k, v in frequency.items()) / frequency_sum
weight          = importance * frequency_score
share           = weight / sum(weights within the occupation)
```

That is **normalised (Importance x frequency-band-weighted-mean)**, per
occupation. A second definition written now would silently diverge from
Mapping A's wage-bill coverage of `0.0022461` and from the DWA-transport bound
of `0.4169526`, both of which were computed through the existing weights. Two
coexisting "task shares" differing by construction is exactly the class of
fault this project keeps catching one step before it becomes permanent.

**[W2-D1] The existing definition is the primary weight.** It is not
re-derived, and any file claiming to supersede it must reconcile against
`mapA_run_receipt.json`'s pinned mass of `56074210.00000092` over 15,274 usable
tasks.

## What the literature says, and it is not reassuring about the name

Importance-weighted aggregation is the field standard: the weight for task *i*
in occupation *j* is its importance rating over the sum of importance ratings
in that occupation. Multi-factor variants using relevance, importance and
frequency exist, as does an exponential `2^importance x relevance` form.
There is no consensus aggregation function.

Two findings matter more than the menu:

1. **O*NET is not designed for this.** Hatgis-Kessell, Aguirre, Wan and
   Bommasani (2026), *Estimating time spent on work tasks*, motivate their
   method by noting existing time shares are "based on coarse O*NET data **not
   intended for this purpose** and/or estimated via black-box language models."
   That is an independent statement of exactly what the inventory found.
2. **The choice probably does not matter much.** Recent work reports
   importance-weighted and unweighted occupation means correlating at 0.999.
   *Recorded as reported, not verified* — arxiv.org is unreachable from this
   session, so this is a citation to check before it enters the paper.

## [W2-D2] The artifact is renamed. It is not a time share.

`onet_timeshares.parquet` becomes **`onet_task_weights.parquet`**, and its
share column becomes `task_weight_share`.

The quantity is a share of **importance-times-frequency mass**. No O*NET column
carries hours or minutes; the one "% Time" scale occurs in zero data tables and
its nine items measure body position. Calling this a time share would misname
the single artifact the entire wage-bill weighting rests on, in a paper whose
contribution is measurement honesty.

The existing private column `task_time_share` in
`w2_build_outputs/task_wage_allocations.csv` **is not renamed** — that file is
pinned by SHA in `mapA_run_receipt.json` and editing it would break the
reconciliation in W2-D1. Instead the new artifact carries the corrected name,
and a note records that the upstream private column is misnamed. **No prose,
table, or column in any release path may describe this as time.**

## [W2-D3] The known defect, recorded rather than fixed

`frequency_score` collapses FT's seven bands with
`sum(category_index * percent) / sum(percent)` — it treats the band **index**
as a cardinal value. FT categories are ordinal frequency bands, and such bands
are typically spaced closer to logarithmically than linearly, so equal spacing
is an assumption and probably a wrong one.

It is not corrected here, for two reasons. Correcting it would change the
existing weights and break W2-D1's reconciliation, and the correct spacing
requires the published band definitions, which need a source this session
cannot reach. It is recorded as a known limitation with a named fix path:
obtain the FT band definitions, and if they are not near-linear, re-derive the
weight and re-run Mapping A's coverage and the DWA bound together so all three
move at once.

## [W2-D4] Two robustness variants, frozen now

Built alongside the primary, never as replacements:

- **importance-only** — `IM / sum(IM)` within occupation, the field standard;
- **equal weight** — `1 / n_tasks` within occupation.

If the headline moves materially across these three, the aggregation function
is doing work the data cannot support and that is a finding to report, not a
number to select from. The 0.999 correlation above predicts it will not move —
which is precisely why the variants are frozen *before* anyone looks.

## [W2-D5] The vintage caveat travels

O*NET 26.1 is cumulative; Task Ratings rows carry dates spanning 2004-2021.
"2021 vintage" names the release, not each row's survey year. Any statement
that the index rests on 2021 task structure must say this.

## What this unblocks

`onet_task_weights.parquet` is now buildable: the definition is fixed, the
name is honest, the defect is recorded, and the variants are frozen. It needs
one SCC run against the pinned O*NET zip.

## Signature

    Owner counter-signature: ______________________  Date: ____________

    [ ] agreed — adopt, rename, record the defect, freeze the variants
    [ ] adopt but keep the name `onet_timeshares` (NOT recommended: the
        quantity is not time, and the contract's column names freeze on write)
    [ ] re-derive the weight now, accepting that Mapping A coverage and the
        DWA bound must be recomputed in the same change
