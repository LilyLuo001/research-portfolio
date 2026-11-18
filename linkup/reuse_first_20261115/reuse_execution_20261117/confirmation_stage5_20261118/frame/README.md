The cloud probe is ready for the existing Azure VM Agent, running as `linkup`.
It performs no network, base-Parquet, raw-text, model, or Git operations.

Execute `cloud_probe_finite_frame.py` source through the current VM control.
It writes new files under `~/migration/confirmation_stage5_20261118/frame_probe_v1`
and refuses to overwrite that directory. Any partial output must be preserved.

The public receipt identifies the highest cached preparation batch with an
SHA-bound manifest, its exact `next_cursor`, and a maximum 150 canonical-row
window pinned to the original catalog, base register, Description-source map,
and verified migration ledger locations. Newer preparation artifacts in the
ledger block use of a stale cursor. Missing cached metadata locators are saved
privately for a targeted follow-up.

The saved context exclusion union includes every state in `final_status`
(including `not_reconciled`), blocked contexts, all nonprotected cached prepared
manifests, and exact known exposure/state files. It deliberately makes no claim
of complete coverage: add the original 10,000-reference context hashes and
confirm current runtime/exposure registry coverage before any model call.
The original reference SHA is
`733875307de475a296e3da4531ad64ba99351f5e2dff109b757ad80b80b34adb`.
Protected batch035 metadata is not opened; its hashes remain excluded through
the existing status/block indexes. The protected chat is never accessed.

Because the 49-column base has no normalized-context SHA, this is a finite
source window, not a certified new-context frame. The subsequent Azure pass
must use the exact rows and pinned normalizer, exclude canonical identities
where available before reading source text, and exclude the resulting context
hashes before model exposure. Keep fewer than 150 if rows duplicate, match the
exclusion union, are missing, or have incomplete text; do not silently replace
them or expand the source window.

Validation: `python3 smoke_probe_synthetic.py` passed using only generated
fixtures, covering cursor binding, the 150-row limit, unresolved/prepared
exclusion, protected-file isolation, and the no-overwrite guard.

The subsequent preparer is `cloud_prepare_fresh_inputs.py`. It defaults to the
actual successful source-window SHA and writes a fresh Azure directory at
`~/migration/confirmation_stage5_20261118/fresh_inputs_v1`. Required arguments
are `--normalizer <cloud frozen legacy_v5_frozen.py>`, `--scorer <cloud field_score.py>`,
and `--scorer-sha <frozen scorer SHA>`. The normalizer is checked against
`336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd`.

The preparer locates the exact original reference artifact through the existing
verified migration ledgers, downloads at most 64 MiB for that artifact, verifies
its whole SHA, and decodes only the four canonical keys and normalized-context
SHA. It refreshes bounded known exposure registries and the status index before
source access and again before saving fresh inputs.

For base and raw Description sources it reads the footer and required column
chunks using the existing managed-identity Blob transport. Snapshot ledger SHA,
size, stable ETag, individual downloaded-range SHA, canonical SOURCE_FILE,
SOURCE_ROW, and JOB_HASH all remain bound. It does not claim to have recomputed
the whole raw source SHA. Parquet row groups necessarily decode extra rows at
storage granularity; only the fixed window's at most 150 source values are
selected or normalized. Hard limits are two base row groups, four raw row
groups, 256 MiB network total, 256 MiB projected uncompressed chunks, and
128 KiB per complete source value. Breaching a limit stops the run without
expanding the window. Oversized, empty, reused, or duplicate contexts are not
replaced.

Outputs include three-field rows in `INPUTS_PRIVATE.jsonl`, a `confirmation`
partition `FRAME_PRIVATE.json` with frozen source-unit hashes, refreshed
`EXCLUSIONS_PRIVATE.json`, private provenance/rejections/range receipts, and a
sanitized public preparation receipt. The runtime may add its required
assignment object without modifying the normalized source text.

`python3 test_fresh_inputs_synthetic.py` passed the fake Blob/Parquet pipeline:
150 fixed rows yielded 145 unique fresh contexts, with five excluded for prior
canonical identity, prior reference/exposure SHA, duplication, and emptiness.
No private data, cloud operation, or network call was used in that test.
