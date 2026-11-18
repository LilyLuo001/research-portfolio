# Cloud scoring adapter

`cloud_score_adapter.py` is a new mechanical adapter. It does not change any file
in `PROTOCOL_FREEZE.json`, score definition, model output, Kimi reference, or gate.
No model call or cloud execution occurs on import or during any adapter command.

The root already froze the real 135-context frame before Luna began:

* Cloud location: `confirmation_stage5_20261118/execution_v1/FRAME_PRIVATE.jsonl`
* Frame SHA256: `bdf3279fff1d121a073b87368aa62d7bd1b39213f9896ab45337de313e55fe11`
* Its `FRAME_FREEZE_PUBLIC.json` uses `context_count: 135`, which is accepted.

Do **not** run `freeze` again for that frame. The optional `freeze` command is
only a metadata-only preparation helper for a not-yet-started run.

Place the new adapter beside the existing frozen `field_score.py` in the cloud
`execution_v1/protocol` directory. Keep the existing bundle unchanged. Use the
already uploaded repository mirror for the original schema, instructions and
validator source hashes.

1. Save `stage5_validate_kimi.py`'s public JSON stdout as a JSON receipt containing
   `validated_output_sha256`. Supply its validated output JSONL, not transport
   output with `response_text`, to the adapter.
2. Run `join`, providing the original source input JSONL, both model output files,
   both final receipts, the Kimi validation receipt, the existing frame/freeze,
   both legs' latest quarantine exports, the repository mirror, and a new output
   directory. `python3 cloud_score_adapter.py join --help` lists exact arguments.
3. Execute the argument vector written to `SCORING_COMMAND_PUBLIC.json`. It invokes
   the unchanged scorer CLI with the existing frame freeze and repository mirror.
4. Run `report --frame ... --frame-freeze ... --scores ... --inputs ...
   --exclusions ... --output-directory ...` to write the aggregate public summary
   and a private source-only Astra queue. Review its separate runtime admission
   controls before any calls.

`join` verifies output hashes, common roster identity and complete accounting.
Both pinned quarantine exports must be supplied. It scans metadata for both legs
before decoding any input or model payload. It then excludes blocked rows from
full JSON decoding, retaining only `record_id`, `context_sha256`, and
`protection_blocked: true` in the joined case. Scanning aggregate framing still
reads bytes, but protected payload/document values are neither decoded nor
materialized. Synthetic tests enforce this using undecodable blocked strings.

All 135 slots remain in the scorer denominator. A locally invalid field does not
discard the original review or unaffected fields. Missing/invalid outputs stay
explicitly counted. Public artifacts and stdout contain counts, hashes and
measure-level aggregates only; case identifiers stay in private artifacts.

`report` preserves the scorer's deterministic queue of at most six diagnostics.
Late-blocked selections are omitted without replacement. `ASTRA_INPUTS_PRIVATE.jsonl`
contains only the selected original identity/document and transport metadata, with
no candidate/reference labels, score values, measure IDs, or adjudication reasons.
It never overwrites the Kimi reference or changes the primary pass decision.
