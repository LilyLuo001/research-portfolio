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
3. The repository freezes retrieval and sampling, but it contains no frozen
   classifier/calibrator that turns retrieval features into predicted `D`
   labels. Therefore PPV and FPR currently have no executable prediction
   denominator. The protocol itself says a calibrator "may" be fit and that no
   final calibrator becomes binding without approval.
4. Candidate recall cannot be evaluated without an independently adjudicated
   complete-pool set of true `D` relations for sampled source tasks.
5. Task-mass/family coverage and transport sensitivity likewise require final
   adjudicated `D/F/N/U` relations and, for PI-15 crossing diagnostics, later
   W4 inputs.

## Gate determination

`BLOCKED_LABELS_AND_FROZEN_PREDICTION_RULE_ABSENT`

It would be scientifically invalid to manufacture labels, select a classifier
after seeing them, or report blank fields as validation results. Before the
authorized one-time opening can run, the project needs:

- two independent vendor-family round-1 labels and the specified third-family/
  human adjudication, produced without paid work unless separately authorized;
- a prospectively committed prediction/calibration algorithm, feature list,
  fit split, decision rule for `D`, and exact evaluation schema; and
- a release-safe evaluator that consumes the signed threshold JSON and emits
  only aggregate metrics and PASS/FAIL statuses.

The signed numerical thresholds remain binding. This blocker does not reopen
or relax any PI decision and does not authorize production Mapping A.
