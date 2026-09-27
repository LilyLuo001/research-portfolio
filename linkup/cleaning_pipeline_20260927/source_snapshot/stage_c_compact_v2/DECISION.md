# Stage C compact V2 bounded repair

Status: active compact-storage candidate after a bounded local repair. The
frozen V5 parser was not modified. V1 code and its measured 16,000-row Kunshan
result remain immutable historical evidence; V2 supersedes V1 for future runs.

V2 fixes only the two V1 storage edge cases. The source index now retains the
actual raw and normalized SHA-256 values separately from the fingerprints
declared in the parser payload. The same deterministic runner exception wrapper
is used during writing and roundtrip verification, so a caught exception whose
payload declares null fingerprints reconstructs exactly. Null source text is
also covered.

Caps below the 1,000,000-byte fixed format budget are rejected before an output
directory is created. Batch mode verifies that all four per-input budgets meet
that minimum before creating its root. After Parquet writers emit footers, the
runner computes actual Parquet plus checkpoint bytes and refuses to publish a
checkpoint if the cap would be exceeded.

Verification on the fixed 2,926-ad fixture used final runner SHA-256
`27278f9246c18299ff6a48a42884ff827555c4c925a45ed9a15b58a56487a2c8`
and frozen parser SHA-256
`336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd`.
All 2,926 payloads reconstructed field-for-field with zero failures. The compact
four-table output was 1,783,846 bytes; the same-codec Zstandard full-V5-JSON
comparison was 5,839,310 bytes, a ratio of 30.55% at 128-row groups. Compact
Parquet plus its checkpoint was 1,785,488 bytes.

Five focused tests pass: normal candidate roundtrip, forced parser exception,
null text, pre-creation insufficient-cap rejection, and actual footer plus
checkpoint cap accounting.

V2 has not been run on Kunshan. Its result is storage-integrity evidence only,
not semantic validation, a formal variable release, or a population-scale
capacity forecast. V5 outputs remain model-assisted research candidates.
