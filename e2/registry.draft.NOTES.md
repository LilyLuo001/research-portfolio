# registry.draft.csv — QUARANTINED DRAFT, NOT the C0 registry

**This file is NOT `e2/registry.csv`.** Per C0, `registry.csv` is the sole
authority for addresses and nothing may enter it without explorer/official-page
verification. This draft fails that bar and must not be consumed by any task
(E2-T2-dune q4 included) until promoted row-by-row.

## Provenance
Owner-relayed answer pack, 2026-07-10. The pack was produced by a model run
(vendor unstated), not by direct owner explorer capture. This session cannot
verify any row: etherscan.io / basescan / polygonscan and public RPC eth_call
are all 403 (org egress policy, same as e2/t1_union_check.md §冲突2).

## Why quarantined (specific defects, from the pack's own notes + inspection)
1. **market_id integrity**: the pack's own note says the syrupUSDC/Base
   market_id "was abbreviated and I reconstructed the full slot only
   partially from context." A reconstructed bytes32 is a fabricated bytes32 —
   Morpho market ids are keccak256 hashes and cannot be reconstructed.
   Structurally, `0x52f04b0000…48a5` (long zero run) does not look like a
   keccak digest. Other market_ids carry no per-id source either (the
   source_url column points at the *token* page, which does not display
   Morpho market ids).
2. **mTBILL** has the identical address on ethereum and base
   (`0xDD629E…e438`). Possible via deterministic deployment, but must be
   confirmed on both explorers before either row is trusted.
3. No row has been sighted by a human on the cited explorer page.

## Promotion checklist (per row, owner or an explorer-capable session)
- [ ] token_address: open the cited explorer URL; confirm symbol + contract.
- [ ] market_id: verify via Morpho UI/API or on-chain
      `idToMarketParams(market_id)` returning the matching collateral token
      (on-chain read = first-hand, per union-check evidence tiering).
- [ ] Fix or drop the syrupUSDC/Base row (defect 1) — do not promote as-is.
- [ ] Confirm mTBILL dual-chain address (defect 2).
- [ ] On promotion, move the row into `e2/registry.csv` (create with the same
      header) and record retrieval date of the *verification*, not of the pack.
