# Outcome-blind manifest overlap census

This completed census reads only SCC-private download-manifest metadata and
the already-built historical roster mapping. It did not read DBN bodies,
prices, quotes, returns, EPS values, or forecasts. The complete safe aggregate
record is [safe_manifest_overlap_summary.json](safe_manifest_overlap_summary.json).

The native manifest parsed symbols as explicit semicolon-delimited fields.
Manifest states were preserved only as metadata; they do **not** certify DBN
body validity. The candidate clock uses the accepted nominal Eastern/DST
interpretation of `anntims`; whether it is the earliest public release and its
time precision remain UNKNOWN. Each candidate window is [-15,+75] minutes.

Actual historical name-interval matching produced 50
release/security/symbol candidate rows for 32 issuer/date/time release-group
candidates. Eight release groups have multiple valid PERMNO candidates and
four have multiple historical symbol candidates; no class was silently chosen.

Eight release groups had a historical-symbol manifest match in each venue
(ARCX, BATS, XNAS, and XNYS). In each venue, four release groups intersected
the nominal issuer-event date and four security-symbol candidates had positive
window overlap. The union of documented manifest intervals within the specified
windows totals 21,600 seconds per venue. This is coverage of manifest-declared
request intervals, not evidence of usable quotes.

Historical CRSP name-interval comparator identities were found for SPY and QQQ
at all 32 candidate dates. SPY had manifest symbol matches for all 32 groups in
four venues; QQQ had none. These are comparator-identity and manifest-coverage
diagnostics only.

No archived verified 2023 trading calendar was located during this bounded
inspection. The observed nominal buckets are 16 pre-open and 16 after-close,
with no RTH candidates; the classification is explicitly coarse and not
trading-calendar-certified.

SCC-private artifacts remain under:

```text
/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/derived/p1_concentration_information/20260920/roster/
```

They are `private_2023_top8_release_security_historical_symbol_candidates.parquet`,
`private_2023_top8_manifest_overlap_by_venue.parquet`, and
`private_2023_comparator_identity_manifest_summary.parquet`.
