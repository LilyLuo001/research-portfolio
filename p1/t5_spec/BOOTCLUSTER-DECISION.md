# bootcluster() — deferred, and why the ORDER matters

**Status: DEFERRED. Not a gap — a deliberate hold.**
Owner instruction 2026-08-28. Nothing here is open for redesign; only the one
implementation parameter below is unset, and it is unset on purpose.

---

## What IS frozen

| | frozen |
|---|---|
| economic error-dependence structure | **sponsor × stock** |
| headline procedure | wild cluster bootstrap, **null imposed**, Rademacher, 9,999 reps, seed recorded |
| implementation family | **Stata `boottest`** |
| method references | Roodman, MacKinnon, Nielsen & Webb (2019), "Fast and wild: Bootstrap inference in Stata using boottest", *Stata Journal* 19(1):4–60 · Cameron, Gelbach & Miller (2008), *Review of Economics and Statistics* 90(3):414–427 |

`boottest` is the approved family because it supports **multiway error
clustering and a separately specified bootstrap clustering** — the two are
distinct arguments, which is exactly what this design needs. The current Python
`wildboottest` is **not** the primary implementation: its documentation states
multiway clustering is unsupported (owner, 2026-08-28). It may be used as a
cross-check on a one-way specification, never as the headline engine.

## What is NOT frozen, and must not be

The `bootcluster()` argument — which dimension carries the bootstrap weights.

**Likely candidate**: multiway sponsor × stock **error** clustering with
bootstrap weights along the **small sponsor** dimension.

"Likely" is not "chosen". The choice depends on four facts that do not exist yet,
because they are properties of the final analysis sample:

1. **true economic-sponsor count** — post-crosswalk, not the raw `family` field,
   which splits one JPMorgan into three;
2. **treated-sponsor count** — the dimension the weights would run along;
3. **stock reuse across sponsors**, measured on the sample *including controls*
   (the treated-only 20/389 figure is the one already withdrawn — plan §15.3.0);
4. **cluster imbalance** in both dimensions — a nominal count means little when
   one cluster carries most of the mass.

`p1/t5_spec/measure_dependence.py` emits all four into
`dependence_profile.json` under `bootcluster_inputs` (including an inverse-HHI
effective cluster count, which is the number that actually governs a bootstrap's
behaviour).

## The ordering constraint — this is the part that protects the result

> **The choice must be justified in writing BEFORE any headline treatment
> coefficient is observed.**

Not "before publication", not "before the referee asks". Before β_h is seen.
After that point every cluster choice is a choice about a p-value, and no
justification written then can be distinguished from one reverse-engineered from
the answer. This is the same discipline as the deleted "take the most
conservative" rule and the frozen 0.80 continuity threshold: the protection is
the timestamp, not the reasoning.

Operationally:

1. Build the final analysis sample.
2. Run `measure_dependence.py` → `dependence_profile.json`.
3. **Fill in the record below, commit it, and note the commit hash.** No headline
   estimation before this commit exists.
4. Then estimate.

A `git log` on this file is the audit trail. If the record's commit is later than
the first headline run, the pre-specification claim is false and the paper must
say so rather than quietly assert it.

---

## DECISION RECORD — fill at step 3, leave blank until then

```
date                     :
dependence_profile.json  : <commit hash of the committed profile>
n_economic_sponsors      :
n_treated_sponsors       :
n_stocks_multi_sponsor   :
sponsor effective_n      :   (inverse HHI; compare to the nominal count)
stock   effective_n      :

bootcluster() choice     :
justification            :   why this dimension, from the four facts above —
                             not from any coefficient
alternatives considered  :   and why rejected, on the same evidence
headline run commit      :   MUST be later than this record's commit
```

**Unfilled is the correct state today.** Do not fill it with the likely
candidate to tidy the file — a pre-specification that was written before the
facts existed is not a pre-specification, it is a guess with a date on it.
