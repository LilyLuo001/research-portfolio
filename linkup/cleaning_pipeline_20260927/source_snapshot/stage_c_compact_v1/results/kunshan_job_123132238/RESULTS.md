# Kunshan bounded V5 compact-storage trial

Job `123132238` completed on `kshctest02` with exit `0:0` in 00:04:02.
It requested 8 CPUs and 12 GB; Slurm reported batch-step MaxRSS 953,496 KiB.

The run used frozen parser SHA-256
`336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd`
and runner SHA-256
`b131da9a4fc708cff3332b9b762d25f4e79b74c8b59268cd22187a49f713987d`.
The job identity is
`f54f3d48d08a72b8c31bac9be077cb6a4b04b16c3853555ca77c60f620a59e65`.

The same four Kunshan source prefixes as the preceding bounded batch were
processed: 16,000 ads, 73,613 evidence rows, and 6,116 unresolved relation
candidate rows. Status counts were 13,284 candidate and 2,716 no-candidate,
with zero parse-error rows, zero truncated rows, and zero pending rows.

All 16,000 compact payloads were reconstructed from the raw source,
fingerprints, normalization, typed fields, exceptional extras, and offsets.
They matched the frozen parser payload field-for-field; failure count was zero.
Because this observed run had no parser errors, this check does not clear the
documented runner-caught-exception limitation.

The sixteen compact Parquet files total 7,663,387 bytes. Including identity
and checkpoint receipts, the persistent directory was 7,672,134 bytes, well
under the 250,000,000-byte cap. End-to-end wall time including the second-pass
roundtrip check was 236.223 seconds (67.73 ads/second). The parser/write pass
worker times were 118.48 to 122.59 seconds.

An independent remote post-run check rehashed all sixteen Parquet files and
compared each hash, byte size, and metadata row count with its checkpoint.
All sixteen passed and the independently summed size was 7,663,387 bytes.

Before submission, full-home usage was freshly measured at 472,597,678,388
bytes. Relative to the stated 498,000,000,000-byte ceiling, that left
25,402,321,612 bytes. This confirms headroom for this bounded <=250 MB job; it
does not establish capacity for a future full-corpus run.

No Parquet output was downloaded. Local receipts are `COMPLETE.json`,
`IDENTITY.json`, and the two small Slurm logs. Remote output remains at
`/public/home/lilysharp/linkup_analysis_v1/stage_c_compact_v1/outputs/kunshan_bounded_v1`.

This is a computational and storage trial, not an independent semantic
validation or formal research-variable release. Candidate/no-candidate status,
qualification presence, requirement strength, and unresolved OR relations
retain the frozen V5 candidate semantics.
