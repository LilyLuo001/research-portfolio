# Mapping A v2 locked-validation preflight — 2026-08-21

## Decision and seal

The prospective PI decision was committed at
`4577fecab7b4e142cb28d78d4aec0800637c7b05` before this preflight. Binding
thresholds are serialized in `mapA_v2_binding_thresholds_20260821.json`.

No locked-test result has been opened and the one-time result opening has not
been consumed. This preflight inspected repository code and the sanitized
private manifest only; it did not inspect a task pair, task text, relation
label, validation metric, W5 value, power result, treatment effect, or outcome.

## Mechanical findings

1. The SCC private manifest status is
   `BLIND_SAMPLE_FROZEN_LABELS_ABSENT`: 2,586 validation pairs exist across
   development (1,513), calibration (540), and locked test (533), but the
   frozen artifact is an unannotated sample.
2. No round-1 dual-vendor label artifacts, adjudication artifact, or qualified
   human audit artifact exists in the approved private validation directory.
3. Superseding pre-label work on the same date now freezes the executable
   classifier/calibration procedure in `mapA_v2_prediction.py` and
   `mapA_v2_prediction_spec_20260821.json`: ten retrieval-only features, L2
   logistic regression, development-only five-fold PR-AUC model selection,
   calibration-only Platt scaling, and the signed PPV/FPR constrained cutoff
   rule. No fitted parameters or cutoff exist because labels remain absent.
4. The independent exhaustive Recall@40 source sample is now frozen privately:
   60 primary tasks plus two prospective 20-task reserves, each against all 220
   GDPval tasks. Every source task used by any classifier split was excluded.
   Candidate recall remains unevaluable until these full pools are adjudicated.
5. Task-mass/family coverage and transport sensitivity likewise require final
   adjudicated `D/F/N/U` relations and, for PI-15 crossing diagnostics, later
   W4 inputs.

## Gate determination

`NEED_PI_BUDGET_AUTHORIZATION`

It would be scientifically invalid to manufacture labels or report blank fields
as validation results. The provider preflight found three technically reachable
independent API vendor families, but did not certify zero incremental cost. The
exact capped request is recorded in `mapA_v2_labeling_preflight_receipt.json`.
Before the authorized one-time opening can run, the project needs:

- two independent vendor-family round-1 labels and the specified third-family/
  human adjudication, produced without paid work unless separately authorized;
- development/calibration fitting under the now-frozen algorithm, followed by
  an immutable parameter and cutoff receipt; and
- a release-safe evaluator that consumes the signed threshold JSON and emits
  only aggregate metrics and PASS/FAIL statuses.

The signed numerical thresholds remain binding. This blocker does not reopen
or relax any PI decision and does not authorize production Mapping A.
