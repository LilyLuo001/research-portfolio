# Independent bounded build review

2026-09-15. Scope: the executed P0/P1 metadata build, P2 interface evidence, P3 synthetic packet, and two source-display-clock diagnostics. This is one finite review, not a reopened Gate 1 or whole-project audit. Requested Astra/high acceptance telemetry: **NOT_OBSERVED**.

## Verdict

**Accept the reproduced metadata findings within their stated scope; HOLD_DESIGN + HOLD_DATA for the research pilot. The implemented pilot is not ready for empirical power.** Neither synthetic tests nor a connectivity success certifies a research sample, inference procedure, or permission to inspect protected values. The evidence does not support NO_GO for all RTH events or all conversions.

## Independent reproduction

`review/verify_support.py` parses only explicit allowed metadata `usecols`, checks source SHA256 values before parsing, checks unique keys and exact joins, and independently computes counts, calendar cells, and graph components. It imports source declarations but does not call production counting functions. Its receipt records full input paths, hashes, projected columns, and code hashes. Integer-valued PERMNO metadata are normalized across integer/decimal serialization before source-universe comparisons; nonintegral identifiers fail closed. No network, SCC, protected financial/dose/liquidity/price/quote/SUE values, power, effects, or Git operations were used by this review.

| Quantity | Independently reproduced |
|---|---:|
| Projected candidate universe, all tiers | 4,191 |
| Projected HIGH/LOW tail | 2,794 |
| Tail represented in v1 metadata | 2,592 |
| Tail absent from v1 representation | 202 |
| v1 represented → 8 PRE/4 POST → proposed clean → clean and all12-min2 | 2,592 → 2,088 → 508 → 182 |
| Parallel all12-min2 branch within 2,088 | 895 |
| Separate v2 represented / 8-PRE-4-POST | 4,186 / 3,246 |
| Capped v1 rows / nominal [09:30,15:00] / nominal with min2 | 29,729 / 465 / 207 |
| Proposed-clean rows / nominal / nominal with min2 | 6,096 / 101 / 38 |
| Clean-and-all12 rows / nominal / nominal with min2 | 2,184 / 11 / 11 |
| Acquisition union rows / nominal / nominal with min2 | 852 / 18 / 5 |
| Union nominal PRE / POST | 12 / 6 |
| Common HIGH/LOW quarter cells / missing | 860 / 13 |
| Broader all-quarter diagnostic cells / missing | 910 / 59 |
| One-tier-only wave/regime quarters excluded | 4 |
| Event-stock/date graph component sizes | 828, 12, 12 |
| Additional wave-edge proxy component size | 852 |

The 202 unrepresented tail units are W002 H59/L73, W016 H24/L29, W025 H6/L11. Absence from the snapshot is not evidence of no earnings. The separate v2 representation omits five projected candidates. Neither represented denominator is the full initial universe.

In every wave, **zero proposed-clean HIGH stocks have at least one nominal-band/min2 event on each side**. LOW has two such stocks in W002 and one in W016; the other waves have zero. This is a stronger immediate warning than merely having few nominal events, but remains conditional on the capped snapshot, provisional tier/overlap labels, and displayed clocks.

## Scientific interpretation and finite fixes

The 8-PRE/4-POST cap can discard older or otherwise additional source-period candidates inside the same original window. Nominal displayed-clock counts do not identify exchange timezone, actual session, first public release, early close, or full release uncertainty. Consequently, 465 and 38 are not upper bounds for a full-window RTH census, and zero clean HIGH two-sided support is not a certified RTH impossibility result.

The 13 common-quarter holes establish a necessary-support problem if every acquired stock receives positive weight under that cell construction. Missing historical industry, final weights/population, and real signed-SUE variation prevent full standardization and numeric-rank adjudication. The base graph's 828/852 component shows concentration under observed stock/date links; neither its three components nor the single wave proxy is ESS or a valid independent-cluster count.

P3's 11 passing synthetic cases support the implemented interface and failure checks, not real covariance transport or confirmatory power. P2 reports 16 synthetic cases and all 852 strict session classifications UNKNOWN; this review accepts that as interface evidence and did not reopen the adapter audit.

The bounded denominator correction is necessary: label 2,592 and 4,186 as represented snapshots, and retain 2,794 and 4,191 as projected source denominators. No scientific rule needs changing to make that correction. The independent verifier also confirms agreement between the overlap table and intersection flags; no count discrepancy remains.

## One next action and authority boundary

**Prepare and execute one uncapped, metadata-only census for the original approved candidate IDs and exact original approved date bounds.** First freeze those existing IDs/bounds in a versioned manifest, including unrepresented candidates with UNKNOWN coverage. Preserve source provenance, candidate economic-event ambiguity, clock uncertainty, and unverified overlap; report event-level analyst-count support separately from the all12 acquisition screen. Reuse existing local metadata wherever complete. Stop after this bounded batch and recompute only affected support rows.

Manifest preparation and already authorized metadata projections can proceed without another scientific decision. Any remote dispatch must match the documented existing metadata authority and original bounds; current evidence does not itself authorize expanding IDs/windows, raw-value access, or purchases. This action tests whether the cap caused the support collapse. It does not promise to solve clock certification.

A switch to non-RTH, relaxed overlap/controls, changed target waves, new inference assumptions, or an economic sufficiency threshold is a PI scientific choice. PRE calibration and native quote scanning require their own applicable custodian/entrypoint authority. None should be inferred from the decision to continue this metadata build.

## Final code provenance

Full SHA256 values for the reviewed design, both nominal counters, measurement implementation/tests, synthetic implementation/tests, and this independent verifier are pinned in `review/INDEPENDENT_VERIFICATION_RECEIPT.json` under `code_hashes`. The receipt is the machine-readable companion to this review; source hashes and explicit columns are under `input_projections`.

Final design code SHA256: `71fbd6cb8e0facb9e0eee13b3e2b834fb82e5d045ad618a872fe48581522b15a`. Independent verifier SHA256: `7dac5509291d06c761750f208f3e7c35ea6f7bad3403b3aec6b919ee64fa892b`. The final verifier exited 0 after the denominator correction; every current design output matches its build-receipt hash.
