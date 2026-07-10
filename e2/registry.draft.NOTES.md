# registry.draft.csv — PROMOTED 2026-07-10; this file is now historical

`e2/registry.csv` now exists and is the C0 sole authority. Promotion was by
**owner formal sign-off, 2026-07-10 in-session** ("With that correction
applied, I formally sign off on the draft registry rows for promotion to
e2/registry.csv"), with one owner-directed correction applied:

- syrupUSDC/Base: token address owner-verified
  (`0x660975730059246a68521a3e2fbd4740173100f5`, hex-identical to the draft
  value); the pack-reconstructed **market_id cleared to UNKNOWN** per C0
  (the reconstructed bytes32 was a fabrication — see original defect list
  below, preserved for the record).

## Residual risks carried into registry.csv (owner accepted at sign-off)
1. All other market_id values remain pack-generated and unsighted — the
   source_url column points at *token* pages, which do not display Morpho
   market ids. The E2-T2 acceptance check (row counts vs. Morpho UI; 5
   market_ids hand-checked on an explorer) is the downstream catch.
2. mTBILL uses the identical address on ethereum and base — plausible via
   deterministic deployment, unconfirmed on both explorers.
3. syrupUSDC/Base market_id = UNKNOWN — fill from the T2-Q1 Dune output or
   Morpho UI once available.

## Original quarantine record (2026-07-10, pre-promotion)
The pack was produced by a model run, not direct owner explorer capture;
this session could not verify any row (explorers + RPC 403). Defects at
quarantine time: (1) syrupUSDC/Base market_id admitted-reconstructed
("abbreviated ... reconstructed the full slot only partially from
context"), structurally non-keccak (long zero run); (2) mTBILL dual-chain
identical address unconfirmed; (3) no row human-sighted on the cited
explorer page.
