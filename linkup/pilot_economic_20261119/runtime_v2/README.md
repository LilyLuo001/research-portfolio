# Additive Luna scheduler amendment: 80k → 200k TPM

**Feasible without changing the policy, scientific payloads, existing output identities, or budgets.** This is a rate-only adapter over the exact original pinned runtime—not a new ledger, a policy replacement, a replay, or a recovery of unknown requests. Preparation of this package made no Azure/model calls and did not apply anything to the live run.

## What changes

- Saved Luna response headers must show the exact provider token limit **250,000**. At least two HTTP 200 responses from the pinned Luna returned model are required; any recorded Luna token-limit header differing from 250,000 rejects this amendment.
- The approved scheduled maximum becomes **200,000 TPM**, preserving 20% headroom. Shared scheduling remains **800,000 TPM**. Kimi/Astra settings, request-byte cost reservations, physical/logical limits, retry policy, scientific instructions/schema and financial caps are unchanged.
- Migration changes **only** `meta['Luna:tpm']` from the original artificial 80,000 clamp to 200,000 and adds `meta['scheduler_rate_amendment_v2']`.
- Every attempt, claim, batch, quarantine row, original ledger identity, timestamp, cooldown, remaining-token observation, saved result SHA, saved HTTP SHA and reservation is preserved. Hash snapshots prove this before/after migration. Existing token-window history is not erased; it still constrains the first new requests.
- The original base `MODELS`, policy SHA, runtime files and carrier policy SHA stay unchanged. An additional immutable amendment binds the original policy, original code hashes, adapter hashes, exact saved-header evidence and a closed-ledger checkpoint.

The adapter reuses the original `Ledger.reserve` and `Ledger.finish` **method bytecode**, with a private globals dictionary whose sole model-setting difference is `Luna.tpm = 200000`. The original constructor, identity, payload, transport, retry, result/cache and CLI logic execute unchanged. This avoids copying or editing the frozen runtime. The method-code identity and single-setting difference are tested.

Later lower provider headers immediately tighten the effective quota. Reapplying the same amendment never raises a subsequently lowered quota, recharges/replays a request, or resets anything. Public status reports the amendment SHA, configured 200k maximum and effective quota; the reported verified 250k is the historical evidence authorizing this amendment, not a fresh cloud probe.

## Required safe transition

1. Deploy this directory **alongside** the existing `runtime/`; do not replace it or change `policy.json`.
2. Drain the old workers after their batch or an explicitly requested stop-file checkpoint. All three original per-leg worker leases must be free. No `forwarding_uncertain`, `transport_uncertain_no_retry`, or existing global hold may remain. Migration will refuse otherwise; it never terminates workers or clears holds.
3. Prepare an immutable amendment from the settled existing ledger:

```sh
python3 -B /home/linkup/migration/pilot_economic_20261119/run01/runtime_v2/rate_amendment.py prepare \
  --directory /home/linkup/migration/pilot_economic_20261119/run01 \
  --output /home/linkup/migration/pilot_economic_20261119/run01/RATE_AMENDMENT_PUBLIC.json
```

4. Inspect the returned amendment SHA and apply that exact file:

```sh
python3 -B /home/linkup/migration/pilot_economic_20261119/run01/runtime_v2/rate_amendment.py apply \
  --directory /home/linkup/migration/pilot_economic_20261119/run01 \
  --amendment /home/linkup/migration/pilot_economic_20261119/run01/RATE_AMENDMENT_PUBLIC.json \
  --amendment-sha256 ROOT_VERIFIED_AMENDMENT_SHA256
```

Prepare does not mutate the database. Apply acquires all original `<Leg>_WORKER.lock` leases, uses one immediate SQLite transaction, and rejects a changed checkpoint. `RATE_AMENDMENT_APPLIED_PUBLIC.json` records preserved counts/hashes. A crash after commit but before receipt writing is recoverable by repeating the exact apply command, without changing the current rate clamp.

5. Only after explicit authorization to resume, clear the operator stop file if one was used. Neither command removes it. Launch the wrapper with the same original policy and normal worker flags:

```sh
python3 -B /home/linkup/migration/pilot_economic_20261119/run01/runtime_v2/pilot_worker_v2.py \
  --rate-amendment /home/linkup/migration/pilot_economic_20261119/run01/RATE_AMENDMENT_PUBLIC.json \
  --rate-amendment-sha256 ROOT_VERIFIED_AMENDMENT_SHA256 \
  --leg Luna \
  --directory /home/linkup/migration/pilot_economic_20261119/run01 \
  --policy /home/linkup/migration/pilot_economic_20261119/run01/policy.json \
  --batch-manifest ROOT_EXISTING_OR_NEXT_PINNED_BATCH_MANIFEST \
  --batch-manifest-sha256 ROOT_VERIFIED_BATCH_SHA256 \
  --field-validator ROOT_ORIGINAL_FIELD_VALIDATOR \
  --frozen-validator ROOT_ORIGINAL_FROZEN_VALIDATOR \
  --workflow-directory /home/linkup/migration/code \
  --max-new-logical 100 --concurrency 2 --max-wall-seconds 14400 \
  --stop-file /home/linkup/migration/pilot_economic_20261119/run01/STOP
```

Resume an interrupted first batch under its existing ceiling to complete the actual physical-row checkpoint. Do not call an interrupted checkpoint “complete.” The original cached results are read by SHA; only unadmitted contexts are forwarded. Later continuation may explicitly raise the cumulative ceiling within the unchanged 10,000/$110 main and $150 pilot bounds and append-only manifest chain.

On the 2-vCPU/4-GB VM, retain concurrency 2 initially. Update supervisor process matching to recognize `pilot_worker_v2.py` and the migration command, not just the old worker path. Use the same durable ledger and existing public status/hold signals. Do not resume the old Luna executable after amendment: it safely limits itself to 80k, but its old header clamp would undo the intended speedup. No adapter startup silently raises a stored lower limit again.

## Offline evidence

Run `PYTHONDONTWRITEBYTECODE=1 python3 -B test_rate_amendment.py`.

The tests reuse original synthetic fixtures, temporary ledgers and mocked identity/HTTP with socket connections forbidden. They verify migration preservation, exact quotas/code/policy pins, active-worker and uncertainty rejection, same-batch cache continuation, original method-code identity, faster bounded scheduling, future quota reduction, idempotency and post-commit receipt recovery. `RUNTIME_V2_TEST_PUBLIC.json` records results and hashes. Original runtime files remain unchanged according to `ORIGINAL_RUNTIME_BEFORE_PUBLIC.json`.
