# YAX V3 execution state

Updated: 2026-09-06 Asia/Shanghai

## Authoritative locations

- Instruction root: `revision_inputs/`
- Immutable seed: `revision_inputs/requirements_seed.json`
- Working status ledger: `requirements_status.json`
- Source/access inventory: `source_inventory.json`
- Contract code: `scripts/spec_contract.py`
- Run dependency code: `scripts/dependency_guard.py`
- Numerical/claim ledger code: `scripts/validate_claim_ledger.py`
- Canonical stamped specifications: `contracts/specs/`

## Stage state

- Package and repository inventory: completed and recorded; ledger disposition
  pending evidence hashing/review integration.
- Gate 0 understanding contract: completed; reviewed by a separate agent on the
  same execution team, explicitly not independent scientific review.
- Gate 1 contract/dependency/ledger engineering: in progress.
- Gate 1 restricted-data reconstruction and numerical existence audit: not run.
- Gates 2--5: not run under V3.

No V3 empirical row is currently represented as verified. Existing R3 outputs
are reference artifacts only until each V3 acceptance check is rerun or
explicitly validated under an immutable V3 specification.

## Verified inputs and blockers

The source inventory records authenticated CPS extracts 9, 10, 11, and 12,
the public/versioned measurement inputs, and SCC access. `EARNWEEK2`, ACS
microdata, exact BCC code membership, proprietary BCC outcomes, and an adopted
external-adoption analysis input are not currently available. Absence from the
current extracts is not evidence of absence from the survey.

## Operational rule

Use a fresh SCC worktree beneath the verified `/project/econdept/...` compute
tier. Do not reuse the stale dirty SCC checkout. Do not cancel, kill, or alter
pre-existing SCC jobs or sessions. Restricted inputs remain read-only.

## Next resumable tasks

1. Stamp and test the first canonical specification.
2. Build the source-text request registry; the generated acceptance-check map
   alone does not resolve G02.
3. write engineering receipts and update eligible Gate 0/1 ledger rows.
4. commit and push the foundation before launching a fresh SCC V3 worktree.
5. reproduce the canonical baseline, then run N01--N03 before dependent models.
