# Canaries benchmark provenance audit — 2026-08-21

## Determination

The repository history supports two separate statements about `0.19`:

1. it entered the project as an **unverified web-search-summary claim** about a
   supposed August 2026 revision; and
2. four minutes later it became an **intentional PI specification** in the
   executable standard, still explicitly lacking a page locator.

The history does not establish that an authored August 2026 paper exists or
states 19%. It also does not establish that 19% is a transcription or rounding
error. The external provenance of `0.19` therefore remains **unknown**. The
later PI choice is historically real but is not source evidence.

The executable `power_standard.json` was not modified by this audit and remains
unfrozen with a null benchmark.

## Repository chronology

| Value | Earliest substantive project appearance | Surrounding claim | Locator attached then | Interpretation |
|---|---|---|---|---|
| `0.13` | commit `9f0a91324b96b1b28b2f85cb6ec4a770bbf217df`, 2026-07-08, `docs/DAX_ERE_Proposal_v3.md`, §1 | “13 percent relative employment decline” among workers ages 22–25 in the most AI-exposed occupations | Proposal reference at line 100; no paper page in the initial commit | Pre-existing proposal benchmark, later verified in the authored 2025 paper. |
| `0.16` | commit `b7743a49a574228c4d6d9f7f2e54225688cf396c`, 2026-08-18 12:31:07Z, `dax/memo/PI_DECISION_D3_2026-08-18.md` and `PI_DECISIONS_OPEN.md` | “reportedly 0.16” in a later revision | Explicitly search-summary only; no PDF was read | Version-drift lead, later verified in the official 2025-11-13 revision. |
| `0.19` | same commit `b7743a49...`, same files | “reportedly 0.19” in a supposed August 2026 revision using ADP through June 2026 | Explicitly search-summary only; hosts reported egress-blocked and no version read | Unverified external claim; no authored source attached. |
| `0.19` PI adoption | commit `7e7554a3962df4acbf5590ffd5ad6272cadeb1d1`, 2026-08-18 12:35:52Z, `PI_DECISIONS_OPEN.md` and `power_standard.json` | PI chose 0.19; pass bar is about 46% looser than 0.13 | `locator_status: PENDING_EXCERPT`; caveat says it rests on web-search summaries | Intentional PI specification, not a verified empirical estimate. Later remediated to null/unresolved. |

The first literal `0.19`-prefix values in commit `d64b1ba...` are synthetic
decimal data (for example `0.196...`) rather than the benchmark. They are not
part of the benchmark provenance.

No commit before `b7743a49...` was found that ties 19% to the Canaries paper,
and no commit message supplies a source. The wording in `b7743a49...` says the
claim came from web-search summaries; the repository contains no evidence that
it was copied from a proposal, paper PDF, slide, table, or equation. Therefore
version specificity, copying, transcription, and rounding remain unresolved.

## Primary-source comparison

| Value | Source/version | Exact locator | Estimand and sample | DAX comparability |
|---|---|---|---|---|
| `0.13` | Brynjolfsson, Chandar, and Chen, *Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence*, authored version dated 2025-08-26 | Abstract, printed p.1; §5 Conclusion, printed p.26, fourth bullet. Archived PDF SHA-256 `75012cdca09a734e64e6dd75e635551286549343dd7549252284dea9dc454a7d`. | 13% **relative employment** decline for ages 22–25 in the most AI-exposed occupations, measured in ADP payroll records; payroll is the data source, not the outcome. | Direction, outcome, and focal age group are relevant. It is not an estimate of the DAX dose coefficient: the exposure definition, data source, comparison, time window, and treatment scale differ. It is defensible only as an external effect-size scale. |
| `0.16` | Same title, official revision dated 2025-11-13 | Abstract, printed p.1; §5 Conclusion, printed p.16, fourth bullet. Official PDF SHA-256 `3b342bf604ed5c8fad8a232c9879345bcb7b71583f33d2acead28d531467a188`. | Revised 16% relative-employment result for the same headline young-worker/high-exposure comparison. | Same limited scale comparability as 0.13; it additionally represents a later analysis vintage than the proposal cited. |
| `0.19` | No authenticated authored paper/proposal version located | None. The 2026-06-24 author presentation inspected in the prior audit has a different coefficient/table and does not state a 19% headline relative decline. | Unknown. | Not assessable and inadmissible as an external benchmark without a primary locator. |

Source URLs and prior file identities are recorded in
`benchmark_source_audit_2026-08-19.md`. The DAX proposal's own 13% statement is
at `docs/DAX_ERE_Proposal_v3.md`, §1, with its full reference in the References
section.

## Error/version/choice assessment for 0.19

- **Error:** possible but unsupported; do not label it an error.
- **Version-specific number:** asserted in history, but no primary artifact
  verifies that version or value.
- **Intentional PI specification:** yes, at commit `7e7554a...`, but that does
  not make the empirical claim sourced.
- **Current conclusion:** external provenance unknown; executable use remains
  blocked unless a dated primary locator is found or the PI signs an amendment
  selecting a sourced benchmark.

## Reproducible history checks

```text
git log --all --reverse -G'0\\.13|13 percent|13%' -- docs/DAX_ERE_Proposal_v3.md dax/memo
git log --all --reverse -S'0.16' -- dax
git log --all --reverse -S'0.19' -- dax
git show b7743a49a574228c4d6d9f7f2e54225688cf396c -- dax/memo
git show 7e7554a3962df4acbf5590ffd5ad6272cadeb1d1 -- dax/memo
```
