# Frozen design execution receipt

**State:** outcome seal intact; protected post-period outcomes not yet opened.

| item | frozen value |
|---|---|
| Frozen commit | `22fbf7924809b7a535e31ae0ab68f5b113ce8078` |
| Frozen tag | `v1.1-design-freeze` |
| Unit | occupation × age-group × month cell |
| Outcome | `WTFINL`-weighted employment stock |
| Young | ages 22–25 |
| Comparison | pooled ages 26–65 |
| Static post | 2023-01 through 2026-07 |
| Transition | 2022-12, event study only |
| Known gap | 2025-10 excluded |
| AI primary / contrast | Eloundou GPT-4 beta / alpha |
| Other frozen AI measures | three AIOE mappings and Eloundou gamma |
| Computerization primary | Webb software-patent exposure |
| Computerization alternatives | O*NET computer importance and level, Autor–Dorn RTI, Frey–Osborne |
| Remote-work exposure | Dingel–Neiman occupation teleworkability |
| Coverage primary | Rule A strict; Rules B and C required sensitivities |
| Fixed effects | occupation×age, occupation×month, age×month |
| Inference | occupation-cluster Rademacher wild bootstrap, 999 draws |
| Test A | frozen construct/ranking/correlation audit |
| Test B | frozen residual-variation concentration and named identifying occupations |
| Test C | paired beta-minus-alpha Q5–Q1 coefficient difference on common support |

Authenticated hashes:

- microdata: `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9`
- sealed pre-period cells: `4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800`
- exposure lookup: `c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8`
- computerization measures: `352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd`

The tagged commit was reconstructed in a clean SCC worktree. All 12 gates
passed and the full tagged-state suite returned 769 passed, 3 skipped before
implementation began.

