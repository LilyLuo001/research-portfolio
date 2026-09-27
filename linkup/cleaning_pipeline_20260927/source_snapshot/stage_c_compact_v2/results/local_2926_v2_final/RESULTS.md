# Local 2,926-row compact V2 repair check

- Runner SHA-256: `27278f9246c18299ff6a48a42884ff827555c4c925a45ed9a15b58a56487a2c8`
- Frozen parser SHA-256: `336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd`
- Ads: 2,926; evidence rows: 11,489; unresolved relation rows: 808
- Statuses: 2,265 candidate, 661 no-candidate, zero errors or truncations
- Exact observed-payload roundtrip: 2,926 checked, zero failures
- Compact four-table Parquet: 1,783,846 bytes
- Compact Parquet plus checkpoint: 1,785,488 bytes
- Same-codec Zstandard full-V5-JSON comparison: 5,839,310 bytes
- Compact/full ratio: 30.55%, with 128-row groups
- Parser/write wall time: 29.010 seconds; 100.86 ads/second

Separate focused tests exercise a forced parser exception and null text, and
confirm their exact roundtrip. They also confirm that an insufficient cap is
rejected before output creation and that actual Parquet footers plus checkpoint
remain within the accepted cap.

This local result does not constitute a Kunshan V2 run or semantic validation.
