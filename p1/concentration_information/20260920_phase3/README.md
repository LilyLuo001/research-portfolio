# P1 concentration-information Phase 3

This directory records the executed, outcome-blind network/event construction and the bounded quote-measurement pilot for the new concentration-information direction. It does not revive MF→ETF conversion, IRR, or Refraction.

Start with [DECISION.md](DECISION.md). The measurement contract was frozen in [MEASUREMENT_CONTRACT.md](MEASUREMENT_CONTRACT.md) before quote responses were decoded.

Raw licensed holdings, identifier-level scores, quote rows, row-level response outputs, and row-level endpoint traces remain on SCC. Git contains code, public configurations, aggregate results, immutable receipts, and aggregate missingness/provenance audits.

Current decision: **HOLD_DATA**. The reported-weight network and balanced 20-stock technical sample pass, but only two PRE_OPEN Exxon issuer-metadata clocks exist and neither is independently certified as first-public. No tested feed supplies a common pre-announcement quote mask for all 20 receivers at those technical anchors, and exact Nasdaq special-rebalance treatment weights remain unavailable.
