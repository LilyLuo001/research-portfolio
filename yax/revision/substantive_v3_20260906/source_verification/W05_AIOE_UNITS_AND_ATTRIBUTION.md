# W05 AIOE units and implementation-attribution audit

Status: source-unit and attribution checks complete; the current-contract
mapping rerun required by W01 remains outstanding.

## Source scale

The vendored AIOE data appendix is available at
`yax/measurement/AIOE_DataAppendix.xlsx` (SHA-256
`c123b4c64840aff3568ae6c97256678719b88a74d45b6362dbefb5af34667b95`).
Appendix A contains 774 occupation-level AIOE values. Recomputing the moments
from the workbook's cached numeric cells gives an unweighted mean of
`-6.85e-09` and sample standard deviation of `0.9999999992`. The raw score is
therefore a standardized source-occupation index, not a probability or
percentage. One raw unit is approximately one unweighted source-occupation
standard deviation.

For a transparent common increment, the source-workbook 25th and 75th
percentiles are `-0.86454515` and `1.014434`, respectively. Their difference is
`1.87897915` raw AIOE units. This source-distribution increment is descriptive;
it is not a smallest effect of interest and is not silently transferred to the
distinct direct-ability implementation.

## Historical four-row audit

The retained four-row mapping decomposition is in
`yax/analysis/audit/MAPPING_DECOMPOSITION_AUDIT.csv` (SHA-256
`60ce9e364ccf370e64283ca27626d3e375f35c0f8ee4eba4f2d7aec9ed826647`).
Inspection of `yax/analysis/run_frozen_v11.py` shows that it first computes an
employment-stock-weighted mean and standard deviation of repaired
equal-administrative AIOE on the 495-occupation expanded AIOE-plus-Webb support,
using all 113 static-analysis months. That same reference scale is then used in
all four rows. Accordingly, the reported coefficients are per one fixed
full-window employment-stock-weighted standard deviation; they are not per raw
AIOE point.

The retained result does not store the numerical value of that weighted
standard deviation. A raw-point conversion cannot be recovered from the result
file alone and is not manufactured here. The current-contract W01 rerun must
store both the raw weighted scale and the raw-unit conversion.

Rows 1 and 2 hold the original 410-occupation support fixed and change only the
score implementation. Rows 2 and 3 keep the repaired score but expand support
from 410 to 495 occupations. Row 4 excludes SOC major group 15 from the expanded
support. Thus the score-repair and population-expansion statements are distinct
and mechanically supported by the implementation.

## Attribution boundary

The literal exact-code merge is an invalid historical implementation in this
project. Neither the manuscript nor appendix attributes that merge to a
published paper, because no external paper's implementation code and universe
have been inspected sufficiently to establish that claim.

## Reproduction

Run:

```sh
python3 yax/revision/substantive_v3_20260906/source_verification/verify_aioe_units.py --pretty
```

The verifier reads the XLSX ZIP/XML directly, checks the source moments and
occupation count, pins both historical mapping artifacts, and checks the
fixed-support/fixed-scale implementation tokens. It reads no CPS microdata or
protected post-period cells.

The disclosures are integrated in `paper/main/sections/03_measurement.tex`,
`paper/appendix/sections/r3_B_mapping.tex`, and
`paper/appendix/sections/r3_H_bcc_architecture.tex`.
