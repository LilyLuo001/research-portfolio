# Checkpoint 09 independent delta review

Date: 2026-09-15. Final verdict: **PASS; HOLD_DATA upheld.**

Both finite findings below were corrected and the affected final prose/hashes rechecked. The secondary remains an explicitly non-decision artifact; no new implementation or broad audit was required.

Routing: reviewer is the separate `p1_final_scientific_referee` agent. Actual backend model ID and reasoning-effort telemetry are **NOT_OBSERVED** in this review; no model/effort is inferred from the task request. No delegation occurred.

## Finite findings resolved

1. **Secondary diagnostic quarantine: PASS.** The primary aggregate exposes unfiltered clock counts: UTC low POST nominal RTH-60 is **62 keys / 7 stocks**, while the secondary interval-contained count is **64 / 8**; primary Eastern high PRE nominal RTH-60 is **2 keys**, while secondary interval-contained is **3**. Under the same clock/calendar, interval containment cannot add records outside the nominal upper-endpoint set. The final `DECISION.md` now explicitly says these differences are not explained solely by analyst filtering, identifies the differing containment rule, labels the secondary `NON_DECISION_DIAGNOSTIC`, and disclaims its use as corroboration or a decision input. The secondary receipt/aggregate denominator is **984 PRE/POST keys**, and its classification discrepancy remains unresolved but has no role in the verdict. No claim of a validated independent reproduction remains.

2. **Full-manifest provider request: PASS.** `STATUS.md` and `DECISION.md` now request semantics for the **full frozen manifest coverage**, removing the unsupported 2019–2024 restriction. Both retain reclassification of all **1,082** keys with the versioned answer and calendar. The fixed projection's input hash is recorded in the existing receipts.

Final affected hashes (secondary artifacts preserved, explicitly quarantined):

| Artifact | SHA-256 |
|---|---|
| DECISION.md (both wording corrections) | `e91258236dfb8720ef102f5a5b049f55e6fd944765da13765fda86ce4697249b` |
| STATUS.md (full-manifest request) | `a1b6bb5f503b7307bad75d5ab0f4d0a5c97e8ce71539d3cd52445b7123430f79` |
| SECONDARY_CLOCK_SENSITIVITY_BY_TIER_SIDE.csv (unreconciled evidence) | `38af94389c9b2b873d96f0217ea543152e11bea04b2a1a2099ffe8b0931ba396` |
| SECONDARY_CLOCK_SENSITIVITY_STAGE_A.csv | `a5abcdd9a5b8d11a224e0cbd3f2165a1c522d5ffb3e26a11aabec56955f0ede9` |
| SECONDARY_CLOCK_SENSITIVITY_RECEIPT.json | `ca97130096e11a3b0a4ff30d69e6a3357bca9df4cfc534cdb34c60bdbf37869b` |

## Findings that pass

- Primary code applies DIRECT/EPS_BASE `OBSERVED_AT_LEAST_2_LOWER_BOUND`, preserves PRE/POST versus transition/boundary-UNKNOWN labels, uses historical local open/close, and counts stocks with support on both sides. Its four hypothetical scenarios each sum independently to **1,082 keys**, **1,033** analyst-qualified keys, and PRE/POST/transition/boundary counts **613/371/96/2**. The stock-support table reports H/L **0/0**, **0/0**, **7/7**, **0/0**, with UTC illustrative 8-PRE/4-POST counts **6/7**. Published group aggregates cannot independently reconstruct individual-stock intersections; these counts are receipt/code-supported, not a fresh protected-row reproduction.
- Hypothetical clocks are explicitly distinguished from source certification. The receipt-lag interval is expressly illustrative. The initial projection leaves all **1,082** clocks uncertified; zero certified support is not asserted to prove non-RTH timing. No favorable clock is selected from the scenario results.
- Formal **HOLD_DATA** is supported. An authoritative Eastern first-public clock that reproduces the supported classification would imply **HOLD_DESIGN for this frozen W021 RTH comparison**. An authoritative UTC clock with adequate semantics would permit only the remaining competing-conversion/calendar/control/dependence checks. Actual certified uncertainty must be applied before either conditional branch; timezone naming alone is insufficient. No quote purchase, realized rank, calibration or power should begin from this checkpoint.
- The corrected public-rescue receipt reports **one** bounded round, **24** selected and unresolved keys, **zero** certified timestamps, and two directional schedule findings. The safe aggregate sums to **24**; the public evidence explicitly says those findings are not exact release timestamps. It does not promote SEC acceptance, call time or scheduled direction into first-public certification. Search exhaustiveness or the protected manifest was not independently inspected.
- All checkpoint files inspected contain code, aggregate counts, hashes, public issuer/source references and decision prose. No row-level licensed metadata, raw market records, financial values, outcomes or credentials were observed. The primary code reads only metadata/count flags and exports aggregates; its input hashes identify protected sources without exporting their contents. No network, SCC, sealed-data access, new search or publication operation was performed by this reviewer.

## Hash verification

All available primary/secondary/initial-projection/rescue aggregate hashes match their supplied receipts. Primary code: `3d2c03715c4c91e00e19458d590750092fd503e0796128674ed44cf10ef465bb`; primary aggregate: `471071b46bfd4e24587fa3a47e70bdd4a13b128abfefb16816cdcf31e161f62b`; primary support: `9b3b91a6ed58cc5fe9b52b3954bd2a86bc1be7c9c3372f9155895fc9da1cebb9`. Public-rescue aggregate: `128045ff21cabef35591b71871280925330ce1a7d1e3751de20806260af5acc6`; rescue receipt: `9beb76ec58c0407cec9cfdab8e1bfd72660faa8a0fc35fb8e2b873d74a8f0f7f`; public evidence: `110bbefe9cf28e56bfa89d1feddf65734f53fb9fbf8fc02f76a7076d43dd8c22`. The referenced full-calendar file and receipt also match `dd6fc11ab324f8e19fdd3ab977d6789ae099272ad32e3a75b8f6fa6845fc3562` and `1ab366c5cef380ed6758c3e001ac9eb20da5f7f605ee7283109611e6bf9c8a91`. Protected input hashes were not recomputed. This review is limited to checkpoint 09 and its explicitly referenced calendar hash, and does not reopen earlier scientific audits.
