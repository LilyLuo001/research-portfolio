# March 2017--2021 repair audit

Status: **resolved data-validity audit, 2026-09-05**.

The wide IPUMS request selected Annual Social and Economic Supplement (`03s`) files in March 2017--2021, while the separately hashed repair selected Basic Monthly (`03b`) files. Because both sources contain CPS identifiers, an initial cross-month identifier comparison incorrectly raised a possible append-and-double-count concern. The relevant test is same-month eligibility after the model's Basic-CPS weight and sample restrictions.

An independent SCC scan read `YEAR`, `MONTH`, `CPSIDP`, `ASECFLAG`, `AGE`, `EMPSTAT`, and `WTFINL` from both authenticated files. In every March from 2017 through 2021:

- the wide `03s` file has zero employed age-18--65 records with positive `WTFINL`;
- the `03b` repair has respectively 55,960, 54,009, 52,264, 45,539, and 45,090 eligible records;
- eligible cross-source `CPSIDP` overlap is zero; and
- within-source duplicate `YEAR`--`MONTH`--`CPSIDP` counts are zero.

The pre-existing positive-weight filter therefore made the repair a functional replacement, not an additive duplicate. Corrected-calendar estimates produced before this audit remain numerically valid.

As a defensive, output-invariant change, `build_exact_age_cells` now excludes the base-file March 2017--2021 rows explicitly whenever the repair input is supplied, before applying eligibility restrictions. Its receipt records the policy and counts both all explicitly replaced rows and any positive-weight rows among them. A regression test verifies that only primary-file rows in the five declared months are replaced. This prevents a future upstream weight change from silently turning the append architecture into double counting.

The machine-readable independent scan is `MARCH_OVERLAP_INDEPENDENT_AUDIT.json`. It was generated from private microdata on SCC; no private row-level data are committed.
