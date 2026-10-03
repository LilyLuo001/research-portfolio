# CPS historical occupation/task benchmark

Status: **complete descriptive benchmark**, limited to occupational composition and a frozen historical routine-task measure. This is a **2004–2025 later computerization/AI-era occupational-composition benchmark**, not a reconstruction of the original 1980s–1990s computer revolution.

The actual local CPS extract contains ASEC-weighted records for every year from 2004 through 2025. Positive `ASECWT` exactly coincides with `ASECFLAG=1` in this file (4,109,155 rows). The benchmark uses those records, employed-at-survey `EMPSTAT` codes 10 or 12, and harmonized `OCC2010`. It compares the earliest and latest nonoverlapping three-year windows, 2004–2006 and 2023–2025. The task measure is the existing Autor–Dorn routine-task intensity (`rti_autor_dorn`), not a modern O*NET backfill. Quartile cutpoints are fixed once from the 2004–2006 weighted distribution.

| result | 2004–2006 | 2023–2025 | late minus early |
|---|---:|---:|---:|
| RTI-mapped share of weighted employment | 98.87% | 98.69% | -0.18 pp |
| Weighted mean RTI among mapped employment | 1.013 | 0.789 | -0.224 |
| Low-RTI quartile share of all employed | 25.01% | 27.62% | +2.62 pp |
| Second quartile share | 24.69% | 26.85% | +2.15 pp |
| Third quartile share | 24.93% | 23.98% | -0.95 pp |
| High-RTI quartile share | 24.24% | 20.24% | -4.00 pp |
| Unmapped share | 1.13% | 1.31% | +0.18 pp |

The machine-readable totals are explicitly `pooled_asec_weighted_person_years`: sums of three annual cross-sections, not a count of U.S. workers at one date. The CSV also reports the three-year annual average. These are changes in the occupation composition of CPS respondents employed at the survey date under static occupation scores, not annual job counts or employment flows. They do not identify a computerization effect, do not measure workers' realized tasks, and are not directly subtractable from LinkUp text measures. No significance test is reported. The verified CPS schema has no workplace computer-use field, so no computer-use proportion is reported. Earnings fields exist in the file but were not read or analyzed.

Exact inputs, sample rules, cutpoints, annual ASEC counts, hashes, and limitations are in `CPS_BENCHMARK_RECEIPT.json`. `CPS_BENCHMARK.csv` is the machine-readable result, and `build_cps_benchmark.py` reproduces it while failing closed on missing schema.
