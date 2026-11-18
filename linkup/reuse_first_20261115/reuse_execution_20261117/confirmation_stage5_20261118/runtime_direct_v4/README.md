# Direct Kimi v4: exact deployment-scoped identity resolution

This is an execution-only successor to frozen v3. No model request is rerun.
The one held HTTP 200 response is complete, unfiltered, usage-reported, and ends
with `stop`; its actual returned identifier is exactly `Kimi-K3.1`. Independent
SHA-pinned ARM metadata identifies the exact requested deployment
`linkup-kimi-k3-1-pro` as MoonshotAI `Kimi-K3.1-Pro`, version `2026-11-04`.
This permits a narrowly scoped identity resolution; it is NOT a claim that the
short identifier is an officially documented model alias.

Only `stage5_kimi_worker.py` changes. The common policy, scientific request,
roster, schema, instructions, validators, rates, caps and six-file runtime layout
remain unchanged. Direct Azure MI remains the only inference route; no OpenCode.

## Offline resolution, preparation and import

With `T4` equal to the root's sealed transition directory:

```
python -B /ABS/runtime_direct_v4/stage5_kimi_worker.py \
  --create-identity-resolution --prior-directory "$T4/prior" \
  --prior-closure "$T4/KIMI_V3_CLOSURE_PUBLIC.json" \
  --arm-metadata "$T4/DIRECT_ARM_DEPLOYMENT_PUBLIC.json" \
  --identity-resolution "$T4/IDENTITY_RESOLUTION_PUBLIC.json"
```

The creator performs no authentication or inference. It checks the hard-pinned
ARM receipt, v3 input pins, prior closure, exact attempt 11, frozen request hash,
exact detail hash, visible-output hash and all completion/filter/usage fields.

Run unchanged `stage5_prepare.py --leg Kimi` into a NEW `kimi_direct_v4` directory,
using the same 135 inputs/roster/schema/instructions/validators and Luna
predecessor. Then:

```
python -B /ABS/runtime_direct_v4/stage5_kimi_worker.py \
  --directory /ABS/kimi_direct_v4 --import-prior-only \
  --prior-directory "$T4/prior" \
  --prior-closure "$T4/KIMI_V3_CLOSURE_PUBLIC.json" \
  --identity-resolution "$T4/IDENTITY_RESOLUTION_PUBLIC.json"
```

Import changes ONLY the identified row's state in the NEW ledger from
`returned_model_identity_mismatch_hold` to `response_saved`. Its ID, timestamp,
request hash, token/cost fields, usage, raw detail bytes and actual returned
identifier stay identical. `prior_contexts` retains the original prior state and
the resolution receipt is SHA-bound in both the new import receipt and database.
Every old file, ledger and v3 nonterminal receipt remains unchanged.

The new ledger carries all 11 paid admissions and $2.4748966 reserved; all 11
contexts are skipped permanently, including the resolved response. Its visible
bytes are reused, not generated again. There are 124 untouched contexts left.
Any other uncertainty, filter or identity hold remains blocked. A different
resolution cannot be substituted into an already imported ledger.

## Root-authorized direct execution

```
python -B /ABS/runtime_direct_v4/stage5_kimi_worker.py \
  --directory /ABS/kimi_direct_v4 --execute \
  --workflow-directory "$HOME/migration/code" --max-wall-seconds 14400
```

Future exact `Kimi-K3.1` response identifiers are accepted only with the validated
resolution profile bound to this exact ARM-verified deployment. Case variants,
prefix matches and other identifiers are not accepted. The actual provider
identifier remains explicit in private detail; no alias rewrite occurs.

All v3 controls remain: 240k Kimi / 800k aggregate scheduled TPM, $40 Kimi cap
including prior reservations, 150 logical / 180 physical caps including prior,
$50 total new stage cap, source-only blinded payloads, no restart replay, and
uncertainty blocks terminal handoff. Final Kimi totals include prior calls;
do not add v2/v3 reservations a second time. Run unchanged
`stage5_validate_kimi.py` on Azure after transport completion.

## Offline verification

```
PYTHONDONTWRITEBYTECODE=1 python -m unittest \
  test_stage5_runtime test_stage5_direct test_stage5_identity -v
```

49 tests run: 46 pass; 3 obsolete OpenCode-only tests explicitly skipped.
Identity tests use synthetic fixtures only. The actual cloud import/resolution
must still be executed and verified by root. No live inference is performed by
this repair. See `DIRECT_REPAIR_PUBLIC.json` for exact code/evidence hashes.
