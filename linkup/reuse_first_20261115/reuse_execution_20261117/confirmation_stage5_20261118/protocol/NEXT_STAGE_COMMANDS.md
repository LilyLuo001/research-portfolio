# Prepared commands — not executed

Local recovery controls, each at its corresponding milestone:

```sh
python3 [private-runtime-path] prepare_kimi_v2
python3 [private-runtime-path] launch_kimi_v2
python3 [private-runtime-path] status_kimi_v2
```

After repaired Kimi is terminal and all 135 outputs are accounted:

```sh
python3 [private-runtime-path] upload_kimi_v2
python3 [private-runtime-path] import_kimi_v2
```

Cloud definitions (place the new adapter and diagnostic script beside the
unchanged frozen scorer first):

```sh
STAGE5_C=[private-runtime-path]
STAGE5_P="$STAGE5_C/protocol"
STAGE5_K="$STAGE5_C/kimi_transport_v2"
STAGE5_S="$STAGE5_C/scoring_v1"
STAGE5_A="$STAGE5_C/astra_diagnostic_v1"
STAGE5_FV="$STAGE5_C/repo/linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py"
STAGE5_OV="$STAGE5_C/repo/linkup/formal800_20261012/code/validate_reviews.py"
```

Join without changing source outputs, then invoke the original scorer:

```sh
python3 "$STAGE5_P/cloud_score_adapter.py" join \
  --frame "$STAGE5_C/FRAME_PRIVATE.jsonl" --frame-freeze "$STAGE5_C/FRAME_FREEZE_PUBLIC.json" \
  --inputs "$STAGE5_K/INPUTS_PRIVATE.jsonl" \
  --luna-outputs "$STAGE5_C/luna/OUTPUTS_PRIVATE.jsonl" --luna-final "$STAGE5_C/luna/LUNA_FINAL_PUBLIC.json" \
  --kimi-outputs "$STAGE5_K/VALIDATED_OUTPUTS_PRIVATE.jsonl" --kimi-final "$STAGE5_K/KIMI_FINAL_PUBLIC.json" \
  --kimi-validation-receipt "$STAGE5_K/VALIDATION_PUBLIC.json" \
  --exclusions "$STAGE5_C/luna/EXCLUSIONS_EXPORT_PRIVATE.json" "$STAGE5_K/EXCLUSIONS_EXPORT_PRIVATE.json" \
  --repo "$STAGE5_C/repo" --output-directory "$STAGE5_S"

python3 "$STAGE5_P/field_score.py" --frame "$STAGE5_C/FRAME_PRIVATE.jsonl" \
  --frame-freeze "$STAGE5_C/FRAME_FREEZE_PUBLIC.json" --cases "$STAGE5_S/JOINED_CASES_PRIVATE.jsonl" \
  --repo "$STAGE5_C/repo" --out "$STAGE5_S/SCORES_PRIVATE.json"

python3 "$STAGE5_P/cloud_score_adapter.py" report \
  --frame "$STAGE5_C/FRAME_PRIVATE.jsonl" --frame-freeze "$STAGE5_C/FRAME_FREEZE_PUBLIC.json" \
  --scores "$STAGE5_S/SCORES_PRIVATE.json" --inputs "$STAGE5_K/INPUTS_PRIVATE.jsonl" \
  --exclusions "$STAGE5_C/luna/EXCLUSIONS_EXPORT_PRIVATE.json" "$STAGE5_K/EXCLUSIONS_EXPORT_PRIVATE.json" \
  --output-directory "$STAGE5_S"
```

Only when `astra_source_only_requests` in `SCORING_PUBLIC.json` is 1–6, prepare
Astra. Keep the full shared roster; its input file is the selected subset:

```sh
python3 "$STAGE5_C/runtime/stage5_prepare.py" --leg Astra --directory "$STAGE5_A" \
  --inputs "$STAGE5_S/ASTRA_INPUTS_PRIVATE.jsonl" --roster "$STAGE5_C/FRAME_PRIVATE.jsonl" \
  --schema "$STAGE5_K/SCHEMA.json" --instructions "$STAGE5_K/INSTRUCTIONS.md" \
  --exclusions "$STAGE5_K/EXCLUSIONS_EXPORT_PRIVATE.json" \
  --field-validator "$STAGE5_FV" --frozen-validator "$STAGE5_OV" \
  --predecessor-receipt "$STAGE5_K/KIMI_FINAL_PUBLIC.json" \
  --predecessor-exclusions "$STAGE5_K/EXCLUSIONS_EXPORT_PRIVATE.json"
```

The authorized root launch control can invoke the following worker once, retaining
its launch receipt/private log and checking for existing admission before dispatch:

```sh
python3 "$STAGE5_C/runtime/stage5_cloud_worker.py" --leg Astra --directory "$STAGE5_A" \
  --field-validator "$STAGE5_FV" --frozen-validator "$STAGE5_OV" --max-wall-seconds 14400
```

After the bounded Astra worker is terminal, write the separate diagnostic summary;
do not rerun primary scoring with Astra substituted for Kimi:

```sh
python3 "$STAGE5_P/astra_diagnostic_compare.py" \
  --frame "$STAGE5_C/FRAME_PRIVATE.jsonl" --frame-freeze "$STAGE5_C/FRAME_FREEZE_PUBLIC.json" \
  --scores "$STAGE5_S/SCORES_PRIVATE.json" --joined-cases "$STAGE5_S/JOINED_CASES_PRIVATE.jsonl" \
  --join-receipt "$STAGE5_S/JOIN_PUBLIC.json" --astra-inputs "$STAGE5_S/ASTRA_INPUTS_PRIVATE.jsonl" \
  --astra-outputs "$STAGE5_A/OUTPUTS_PRIVATE.jsonl" --astra-final "$STAGE5_A/ASTRA_FINAL_PUBLIC.json" \
  --exclusions "$STAGE5_C/luna/EXCLUSIONS_EXPORT_PRIVATE.json" "$STAGE5_K/EXCLUSIONS_EXPORT_PRIVATE.json" "$STAGE5_A/EXCLUSIONS_EXPORT_PRIVATE.json" \
  --repo "$STAGE5_C/repo" --output "$STAGE5_S/ASTRA_DIAGNOSTIC_PUBLIC.json"
```
