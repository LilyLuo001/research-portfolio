# Scoring / Astra readiness — 2026-11-18

Read-only evidence checked: Luna completed 135 physical calls and accounted for
all 135 outputs; 134 carriers completed field-local validation. Its reservation
is $1.1428197. Local Kimi v1 is terminal with zero provider calls and zero reserved
cost. Its 135 input identities, shared roster and every original scientific input
pin match. No original document or model payload was decoded for these checks.

The existing frame remains 135 contexts, SHA
`bdf3279fff1d121a073b87368aa62d7bd1b39213f9896ab45337de313e55fe11`;
shared roster SHA is
`f36abb72675c8ac7fa34b3b7bf72b5d3bdbe93338146e5e9655f2cf0d3bc9faa`.
The frozen scorer/protocol bundle remains unchanged (`fdf07cec…792f11`).

Kimi recovery uses new local `kimi_local_transport_v2`, cloud
`execution_v1/kimi_transport_v2`, and cloud `execution_v1/runtime_transport_v2`.
The new control module transports matching code and input pins and validates with
that matching runtime. It retains scientific `runtime_version` v1, so the original
Astra runtime can verify the repaired Kimi predecessor receipt. Do not use the
unversioned `upload_kimi` / `import_kimi` actions or their old directories.
At this check, repair runtime files were still being prepared; `prepare_kimi_v2`
must wait for `runtime_transport_v2/REPAIR_PUBLIC.json` and its passing tests.

`cloud_score_adapter.py` accepts the actual `context_count: 135` freeze. Join
Luna's `OUTPUTS_PRIVATE.jsonl` with the repaired Kimi's
`VALIDATED_OUTPUTS_PRIVATE.jsonl` and `VALIDATION_PUBLIC.json`, not its transport
file. Keep both quarantine exports. All 135 slots remain accounted, and one local
field error does not erase other fields. Public aggregates contain no case IDs.

Run primary scoring once, then prepare the deterministic at-most-six source-only
Astra inputs. Use the full 135-context roster with the selected Astra subset.
If the selection is empty, skip Astra. Its runtime allows at most six physical
requests, six unique contexts and an $8 leg reservation inside the fixed $50 cap.

New `astra_diagnostic_compare.py` consumes the saved primary cases/scores and
Astra's bounded outputs. It reports per-measure Astra–Kimi / Astra–Luna agreement
and unresolved counts. It checks subset identity, output hashes, quarantine and
six-call cap. It never changes Kimi, reruns a primary gate, chooses a replacement
case, or admits production. Keep `SCORING_PUBLIC.json` and the new
`ASTRA_DIAGNOSTIC_PUBLIC.json` as separate artifacts.

Validation: adapter's eight synthetic tests already pass; two new diagnostic
tests verify unchanged primary files and rejection of a seventh physical call.
No cloud/model command was executed by this readiness task. Exact commands are in
`NEXT_STAGE_COMMANDS.md`.
