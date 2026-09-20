# P3 event-clock evidence

## Result

The 2022-12-30 top-eight roster and all 32 candidate 2023 release groups are preserved. **Zero events are scientifically frozen for intraday response analysis.** Two Exxon issuer pages expose `article:published_time` metadata and are retained as conditional 5m+ technical anchors only; the metadata is not independent proof that this was the first public release.

## Evidence rule

SEC acceptance is a public-filing upper endpoint, never a substitute for the release time. I/B/E/S nominal time is retained only for calendar classification. Closed dates are not moved to the next open. Page modification time, conference-call time, and price behavior are not used.

The two issuer metadata values end in `:00`. The code conservatively represents each as a one-minute interval rather than claiming seconds precision. This rounding convention controls only a technical coverage diagnostic. A scientifically usable event still requires an issuer/wire record whose timestamp and first-public interpretation are documented.

## Gate

| Layer | Count | Scientific eligibility |
|---|---:|---:|
| Candidate release groups | 32 | 0 |
| Conditional issuer-metadata technical anchors | 2 | 0 |
| Other events without a qualifying interval | 30 | 0 |
| Certified 1m/5m/15m/60m events | 0 | 0 |

The next bounded action is to source-lock three AFTER_CLOSE and one additional PRE_OPEN release from the frozen calendar using issuer/wire publication evidence, without looking at responses. The two current anchors and purchased quote windows remain implementation diagnostics, not outcome evidence.
