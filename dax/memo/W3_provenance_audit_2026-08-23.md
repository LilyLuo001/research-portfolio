# W3 provenance audit — Mapping A v2 diagnostic and S1 construct pilot

**Audited:** 2026-08-24. **Trigger:** `W3_DECISION_dwa_transport_2026-08-23.md`
section 8, which records these figures as having "no artifacts in this
repository". **Disposition: every figure is FOUND.** Section 8's premise was
wrong, and the correction is the main result of this audit.

## 1. Why section 8 was wrong

The artifacts were never lost. They were committed to `main` — and to
`task/DAX-upstream-gates-20260821` — but not to
`claude/dax-research-direction-1ohi97`, the branch the decision memo was
drafted on. Forty-six files under `dax/mapping/` existed on `main` and not on
this branch. A figure invisible from the branch you are standing on reads
exactly like a figure with no artifact.

The row-level labels behind all three figures are intact on the SCC under
`/usr3/graduate/qluo/dax-private/`, and every SHA-256 pinned in the committed
receipts still matches the file on disk.

The write-up block section 8 imposes is therefore lifted, subject to §5.

## 2. Method

Each figure was **recomputed**, not merely located. A file that mentions a
number is not the artifact that produced it.

Recomputation was a read-only re-aggregation of the preserved per-row label
files: read the CSV, count the labels, weight by the recorded task mass. No
resampling, no redraw, no model or API calls, USD 0 spent. Nothing was
regenerated — a fresh draw would produce a different number wearing the old
one's name.

The aggregation was written independently rather than by invoking the original
runners, so that no sampling code path could execute. It agrees with the
committed receipts to the last recorded digit.

Receipt: `dax/mapping/w3_provenance_recompute_receipt_20260824.json`, with
`.lineage.json` beside it.

## 3. Disposition of every cited figure

| Figure | Cited | Recomputed | Disposition |
|---|---|---|---|
| Mapping A v2, D | 0/60 | 0/60 | **FOUND** |
| Mapping A v2, F | 24/60 | 24/60 | **FOUND** |
| Mapping A v2, N | 36/60 | 36/60 | **FOUND** |
| Plausible D across audited candidate pairs | 1 of 108 | 1 of 108 | **FOUND** |
| S1 sampled tasks | 120 | 120 | **FOUND** |
| S1 PASS | 13 = 12.79% mass | 13 = 12.786114520412104% | **FOUND** |
| S1 REVISE | 11 = 12.93% mass | 11 = 12.932654583609837% | **FOUND** |
| S1 NON_EVALUABLE | 96 = 74.28% mass | 96 = 74.28123089597807% | **FOUND** |
| S1 interpersonal | 47.55% mass | 47.5527148175118% | **FOUND** |
| S1 physical | 22.84% mass | 22.84296817003696% | **FOUND** |
| S1 constructible instances | 24 of 120 | 24 of 120 | **FOUND** |

`24 of 120` reproduces under both available definitions — PASS + REVISE = 24,
and the two executable evaluable classes (14 simulated-input + 10
supplied-files) = 24. They coincide; the citation is unambiguous either way.

## 4. Two corrections to how these figures are cited

Both figures reproduce exactly. Both are described inaccurately in project
discussion, and the descriptions should be fixed before the paper uses them.

**4.1 — "on development pairs" understates the v2 sample.** The 60 pairs are
36 development plus 24 calibration; the receipt's own scope field says
`development_calibration_only`. Development-only counts are D=0, **F=15,
N=21** — not 24 and 36. The cited `/60` denominators are right, so the numbers
are right and only the phrase is wrong. Cite it as 60 development-and-
calibration pairs.

**4.2 — the 108-pair figure is not the v2 diagnostic.** It comes from the
**v3 source-side audit of 2026-08-23**
(`mapA_v3_source_audit_result_receipt_20260823.json`), a separate exercise over
six prospectively selected O*NET sources, with aggregate counts D=1, F=55,
N=52. The v2 codex diagnostic of 2026-08-21 is a different sample of 60 pairs.
Bundling them as one "v2 diagnostic" merges two studies.

Per-source counts recompute as 18/16/20/17/14/23 candidates, with the single D
isolated to source 5 (`physical_manual`); one source of six carries any
plausible direct substitute.

## 5. What this audit does not establish

Recomputation confirms arithmetic and the provenance chain. It does not upgrade
the evidence.

- The v2 labels remain `PRELIMINARY_SINGLE_CODEX_DIAGNOSTIC_COMPLETE_NOT_FORMAL_VALIDATION`
  — one annotator, not independent, not multi-vendor.
- The S1 pilot remains `S1_CONSTRUCT_VALIDITY_PILOT_COMPLETE_THRESHOLD_UNSIGNED`,
  with `formal_s1_gate_result: UNRESOLVED`, `threshold: null`, and
  `recommendation: PARTIAL_IDENTIFICATION_ONLY`. Its own weight limit says the
  mass shares are `PILOT_DESCRIPTIVE_NOT_DESIGN_WEIGHTED_POPULATION_ESTIMATE`.
- No formal validation performance, candidate recall, or population prevalence
  is claimed by any of these artifacts.

Anything written from these figures must carry those qualifiers. A number being
reproducible is not the same as a number being a population estimate.

## 6. Locators

Committed to this branch by this audit (counts and locators only; scanned for
the guarded task-text fields in `PROTOCOL_mapA_gdpval.md` §7 — none carried
content, and no O*NET or GDPval task statements are present):

    dax/mapping/mapA_v2_codex_diagnostic.py
    dax/mapping/mapA_v2_codex_diagnostic_result_receipt_20260821.json
    dax/mapping/mapA_v2_codex_diagnostic_sampling_receipt_20260821.json
    dax/mapping/MAPA_V2_PRELIMINARY_CODEX_DIAGNOSTIC_2026-08-21.md
    dax/mapping/mapA_v3_source_audit.py
    dax/mapping/mapA_v3_source_audit_result_receipt_20260823.json
    dax/mapping/mapA_v3_source_audit_sampling_receipt_20260823.json
    dax/mapping/run_s1_construct_validity.py
    dax/mapping/s1_construct_validity_spec_20260823.json
    dax/mapping/s1_construct_validity_execution_receipt_20260823.json
    dax/mapping/s1_construct_validity_result_receipt_20260823.json
    dax/mapping/s1_draw_receipt_20260823.json
    dax/mapping/S1_CONSTRUCT_VALIDITY_PROTOCOL_2026-08-23.md
    dax/mapping/S1_CONSTRUCT_VALIDITY_PILOT_REPORT_2026-08-23.md
    dax/tests/test_mapA_v2_codex_diagnostic.py
    dax/tests/test_s1_construct_validity.py

Private row-level inputs, hashed and **not** committed — `s1_sample_120.csv`
carries a `task_statement` column and must stay private:

    w3_mapA_v2_codex_diagnostic/run_20260821/mapA_v2_codex_diagnostic_labels.csv
      b43a9118cc7ec64367a04bf06670251283c451cec2307b9987e6f6a208c53102   60 rows
    w3_mapA_v2_codex_diagnostic/run_20260821/mapA_v2_codex_diagnostic_sample.csv
      160d2a44654530b2096ebfe6a208113aba21ba04467530875c0c38a68cbd07ad   60 rows
    w3_mapA_v3_decision/.mapA_v3_source_audit_labels_private.csv
      19d023d64491d241c741564737602b1d496ee3c70595e2d39d3354e2509c7ced  108 rows
    w3_mapA_v3_decision/source_audit_20260823/mapA_v3_source_audit_candidates.csv
      a481f39de0d44b130d98bc0a561afe538beede7b5f5a14403b9c0ee10cae4655  108 rows
    w3_mapA_v3_s1/run_20260823/s1_construct_annotations.csv
      d79510b9463ae262ddc8b01e14b74a672fa361dc0592246c80720d584796284f  120 rows
    w3_mapA_v3_s1/run_20260823/s1_sample_120.csv
      693cea853e8c22359a50650fea854233897a4b34b8e0c9de461a5f2d4583bc72  120 rows

All are relative to `/usr3/graduate/qluo/dax-private/`.

## 7. Recommended follow-up

1. Amend `W3_DECISION_dwa_transport_2026-08-23.md` §8 — the gap is closed, and
   the stated reason for it (no artifacts) was a branch-visibility artefact.
2. Adopt the §4 citation corrections wherever these figures appear.
3. Consider whether the other thirty-odd `dax/mapping/` files on `main` but not
   on this branch are needed here. This audit brought across only what the three
   cited figures required; it did not survey the remainder.

Item 3 is the general form of the problem: the repo is the shared state only if
everyone is looking at the same branch of it.
