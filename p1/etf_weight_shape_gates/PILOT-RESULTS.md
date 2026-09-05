# P1 V3 data-contract pilot results

Status: `PASS` for the V3 data-contract pilot only. This is not a Gate 0,
Gate 1, or Gate 2 result. The V1 and V2 pilots are superseded by V3 and cannot
be used for authorization.

V3 narrows the VOO pro-rata evidence scope to 2024-12-31. The 2024-06-30
corporate-action case remains in the golden sample as a negative control, but
is no longer labeled pro-rata verified.

- Pilot ID: `P1_GOLDEN_DATA_CONTRACT_2026-09-05_V3`
- Completion time: `2026-09-05T15:29:57+00:00`
- Execution: small interactive SCC process; no queued Gate job and no archive
  enumeration
- Required golden categories: 7/7 populated
- Testable golden cases: 7 across 6 distinct portfolio-dates
- Registered invariants: 18/18 passed
- Final raw traces: 25/25 reconciled across two portfolio-dates
- Maximum row-level weight error: `0.897134` bp, below the frozen `2` bp
  tolerance
- Maximum median implied-denominator error: `0.268162%`, below the amended and
  frozen `0.5%` tolerance
- Unverified pro-rata exposures constructed: 0

The Git-safe machine-readable receipt is
[`pilot/PILOT_PUBLIC_RECEIPT.json`](pilot/PILOT_PUBLIC_RECEIPT.json). It contains
only non-proprietary statuses, aggregate counts, and hashes. The canonical V3
`PILOT_PASS.json` and its hash-bound licensed evidence are stored at:

```text
/project/econdept/qluo/P1_Refraction_WRDS/GATE_RUN_20260905_CONTRACT_V3/pilot/
```

Licensed row-level values and exact TNA observations are intentionally omitted
from this report and from tracked public artifacts.

The pilot's ETF-class dollar exposures are authorized only as retrospective
accounting demonstrations. Point-in-time dollar exposure remains unresolved
until monthly-TNA availability is documented or a lag rule is separately
validated. Either change requires a newly frozen golden sample and pilot.

No full Gate 0/1 rerun or Gate 2 run followed this pilot. The frozen config
keeps the full entry point disabled, and Gate 2 remains disabled.
