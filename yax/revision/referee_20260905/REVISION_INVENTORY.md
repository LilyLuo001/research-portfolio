# Referee-revision inventory

Inventory date: 2026-09-05

## Version boundary

- Revision branch: `task/yax-referee-revision-20260905`
- Parent submission commit: `a31e549be9da06705412f11d4f60f1bbb08590e7`
- Protected design tag: `v1.1-design-freeze` -> `22fbf7924809b7a535e31ae0ab68f5b113ce8078`
- Protected confirmatory tag: `v1.1-confirmatory-results` -> `b16109482c3bf5ca176f6f08976e120b04769945`
- New outcome work authorized by the owner's 2026-09-05 master prompt is post-outcome exploratory. Frozen inputs and outputs remain immutable.

## Available materials

| Class | Available | Principal location or record | Status |
|---|---|---|---|
| Final manuscript | yes | `paper/main/`, `YAX_RESTAT_SUBMISSION.pdf`, and the V5.1 Markdown source | verified parent artifact |
| Online appendix | yes | `paper/appendix/` and `YAX_ONLINE_APPENDIX.pdf` | verified parent artifact |
| Referee reports | incomplete | the master prompt identifies R1/R2 comments and reproduction targets, but the two full original report files are not present in the repository or current attachments | blocker for claiming a literally complete comment-by-comment response |
| Frozen results | yes | corrected frozen run, result ledger, audit receipts, protected tags | immutable baseline |
| Post-outcome audits | yes | age, flow, mobility, hard benchmark, common support, F/G, A/E, two-way covariance, LOCO, and power directories | prior exploratory evidence |
| Analysis code | yes | frozen engine plus versioned post-outcome scripts and tests | executable |
| CPS microdata | yes, private compute only | authenticated wide IPUMS CPS extract and longitudinal-weight patch on SCC | not redistributable |
| Exposure inputs | yes | six architectures, Webb software, O*NET computer use, RTI, Frey--Osborne, Dingel--Neiman, and occupation characteristics | public-source derivatives with receipts |
| Crosswalks | yes | Census 2010-to-2018 bridge, lookup, Rule B values, and mapping receipts | versioned |
| Placebo characteristics | yes | wage, education, cognitive, telework, STEM, physical, RTI, and computer-use columns | 492 occupations before joint support restrictions |
| Webb AI | yes | public source mapped to Census 2018 under the external-architecture rule | outcome model complete; 448 occupations |
| OECD capability measure | yes | official OECD detail scores mapped to Census 2018 | outcome model complete; 448 occupations |
| March 2017--2021 samples | yes in repair extract | original extract selected ASEC `03s`; repair explicitly requested basic `03b` samples | balanced-calendar sensitivity complete |
| October 2025 sample | no | authoritative IPUMS calendar and repository receipt | no CPS was collected during the federal shutdown; not an extract omission |
| Industry | partial | `IND1990` in the wide extract | permits a documented industry exclusion after code-definition verification |
| Education and enrollment | yes | `EDUC`, `SCHLCOLL` | permits entry-age/education diagnostics if kept within declared scope |
| Software | yes | SCC Python environment with NumPy/Pandas/SciPy and TeX Live; local Python and PDF rendering tools | usable |

## Evidence classes

1. **Frozen reproduced:** exact values authenticated by the corrected frozen run and protected-result audit.
2. **Prior post-outcome reproduced:** versioned exploratory artifacts with input and output receipts.
3. **New post-outcome exploratory:** analyses first declared in `ANALYSIS_SPEC_BEFORE_EXECUTION.md` and executed only after this inventory is committed.
4. **Referee-reported target:** a number appearing only in the master prompt until matched to an artifact.
5. **Unresolved:** missing source, missing full report text, non-identical construct, or failed diagnostic.

## Immediate baseline targets

The revision must first reproduce the primary beta/Webb coefficient and full Q2--Q5 vector, 468/444 support counts, the common-support joint-sign outputs, F/G coefficients and `p=.040` for G, the 53.28/52.32 mobility comparison, and the prospective/realized precision ratios. Any mismatch stops new analysis until reconciled.

## Security and reproducibility

Private paths, usernames, API keys, and credentials are not written to tracked files. SCC jobs receive paths through command-line arguments or environment variables. Public artifacts contain counts, hashes, specifications, software versions, and output lineage, never raw IPUMS microdata.
