# Kimi direct Azure v3: transport-only transition

No OpenCode API, CLI, configuration, process, or gateway is used. The existing
Azure VM's `~/migration/code/workflow.token` helper supplies the Cognitive
Services bearer token in memory. The exact existing Azure deployment and request
contract are retained: NOTICE + full `kimi_prompt`, 16000 output tokens,
`stream:false`. No additional scientific parameters are introduced.

The six-file runtime layout stays compatible with `stage5_prepare.py`. Only the
Kimi worker changes; common/cloud/prepare/validation code is unchanged. The
legacy-named gateway file is a hash-pinned, unused compatibility artifact and is
never imported by the direct worker.

## Preparation and import (no auth or model calls)

1. Run this runtime's unchanged `stage5_prepare.py --leg Kimi` into a NEW
   directory with the same 135 inputs/roster/schema/instructions, frozen
   validators, Luna FINAL and predecessor exclusions. Never reprepare old v2.
2. Import the stopped, SHA-pinned closure and private prior evidence:

```
python -B /ABS/runtime_direct_v3/stage5_kimi_worker.py \
  --directory /ABS/kimi_direct_v3 --import-prior-only \
  --prior-directory /ABS/kimi_direct_transition_v3/prior \
  --prior-closure /ABS/kimi_direct_transition_v3/KIMI_V2_CLOSURE_PUBLIC.json
```

The actual local snapshot was tested: 10 saved provider admissions/visible
responses, $2.2454877 reserved, all carried into the new ledger; 125 untouched
contexts remain. All prior contexts are permanently skipped, even if their old
status was retryable. Imported uncertainty holds every new admission. An imported
filter requires metadata-only preparation with the corresponding merged
exclusion; never restore its source or call it again.

The importer verifies closure/file hashes, approved prior runtime pins,
scientific roster/source/request hashes, identities, claim mappings, per-attempt
reservation arithmetic, caps and visible-response hashes. Rows, IDs, timestamps,
quota/cooldown metadata and charged reservations are copied atomically. Repeated
import of the same closure is idempotent; a changed closure is rejected. Old
inputs, responses and database are never modified.

## Root-authorized execution only

```
python -B /ABS/runtime_direct_v3/stage5_kimi_worker.py \
  --directory /ABS/kimi_direct_v3 --execute \
  --workflow-directory "$HOME/migration/code" --max-wall-seconds 14400
```

Import is mandatory before execution. There is no unauthenticated fallback,
OpenCode fallback or alternative provider. Serial scheduling remains 240k Kimi
TPM / 800k aggregate despite the independently observed 3M deployment quota. The
$40 Kimi cap, 150 logical / 180 physical limits include the carried v2 admissions;
$50 stage aggregate and all other limits remain unchanged. Only confirmed
429/500/502/503/504 responses may retry once within the same uninterrupted direct
case. Restart never replays an admitted context. SIGINT/SIGTERM stops new
admissions and lets the synchronous current request finish; any uncertain
reservation prevents terminal handoff.

Outputs retain the same transport format. Run unchanged
`stage5_validate_kimi.py` on Azure afterwards. `KIMI_FINAL_PUBLIC.json` reports
COMBINED Kimi totals including v2: do not add the prior v2 reservation again.
HTTP 401/403 stop the leg; a bounded symbolic error code is retained privately,
not provider free-text messages or raw/error/reasoning bodies.

## Verification

```
PYTHONDONTWRITEBYTECODE=1 python -m unittest test_stage5_runtime test_stage5_direct -v
```

Three OpenCode-only tests are explicitly skipped because that route is removed.
Direct tests use synthetic fixtures and fake provider responses only. The actual
prior snapshot was separately imported into a disposable local ledger without
authentication or inference. See `ACTUAL_IMPORT_PROOF_PUBLIC.json` and
`DIRECT_REPAIR_PUBLIC.json`. The earlier repair receipt digest is preserved
verbatim in `REPAIR_PUBLIC_ORIGINAL_6bc66b0b.json`, without editing v2.
