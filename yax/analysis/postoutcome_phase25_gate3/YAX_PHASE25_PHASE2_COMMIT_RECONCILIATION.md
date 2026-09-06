# YAX Phase-2 commit reconciliation

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## Resolution

The two recorded SHAs refer to two consecutive, non-conflicting states.

| SHA | role | contents added at that commit |
|---|---|---|
| `8ebef7c4f443b5f9300ccfa7d1761f822215d790` | Phase-2 substantive result package | final PATH-2B decision memo, Stage-2C aggregate outputs, both fixed figures, rendering code, and result tests |
| `9772a494afc2c1af5630979631c4b67640f4ff3f` | Phase-2 seal/final HEAD | reproducibility receipt, receipt finalizer, and final receipt tests |

`9772a49` has `8ebef7c` as its sole parent. The only file changes between
them are:

- addition of `YAX_PHASE2_REPRODUCIBILITY_RECEIPT.json`;
- addition of `finalize_phase2.py`; and
- receipt-related additions to `test_phase2_precoefficient_gate.py`.

No Phase-2 coefficient, classification, memo conclusion, table, or figure
changed in the seal commit.

## Remote and final state

At Phase-2.5 branch creation, both the local Phase-2 branch and
`origin/task/yax-phase2-20260831` resolve to:

`9772a494afc2c1af5630979631c4b67640f4ff3f`.

This is the true final Phase-2 commit and the immutable parent of Phase 2.5.
It contains the decision memo, all Phase-2 outputs and figures, and the
reproducibility receipt.

## Receipt interpretation

The Phase-2 receipt's `result_package_commit` field intentionally records
`8ebef7c`, the already committed artifact set whose hashes it sealed. The
receipt itself could not be contained in that same commit without a circular
commit reference; it was added by `9772a49`.

The old receipt therefore does not require regeneration or mutation. It is a
manifest of the substantive result-package commit and is itself authenticated
by the subsequent seal commit. All later owner-facing reports and the
Phase-2.5 reproducibility receipt must identify `9772a49` as the final Phase-2
HEAD and `8ebef7c` only as the sealed result-package commit.

No substantive Phase-2 result was altered during reconciliation.
