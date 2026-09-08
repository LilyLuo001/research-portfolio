# E03 language, scale, label, and rounding audit

Status: source-level corrections complete; final render review and unresolved
upstream dependencies remain.

The active paper, appendix, and revision documents were checked against the
canonical aggregate results and the V3 reporting requests.

- Dissertation-remnant uses of “chapter” were replaced with “paper.”
- Main Table 2 now describes the grouped-binomial weighted-stock criterion and
  its log conditional-mean-ratio parameter. It does not call an observed log
  ratio the dependent variable, and it states that one-sided zero-stock cells
  remain in the criterion.
- The service diagnostic is SOC35/37/39: food preparation and serving,
  building and grounds cleaning and maintenance, and personal care and
  service. The all-occupation row removes 33 occupations (10, 6, and 17 in the
  three families) and 8.2019 percent of stock; the Q1-only row removes 17
  occupations (5, 3, and 9) and 4.8856 percent. Protective service (SOC33) is
  not in this exclusion and is now explicitly excluded from the prose label.
- The industry table now identifies its baseline as an
  occupation-by-broad-industry-by-age-by-month microcell model. The conditioned
  row adds 13 industry-specific young-by-post shifts; it is not mislabeled as
  the occupation-level baseline.
- Raw Webb software values are 0--100 overlap percentages. Fitted Webb
  interactions use the preperiod employment-weighted standardized score. The
  appendix now states both units.
- AIOE units and the historical fixed-SD audit unit are governed by
  `source_verification/W05_AIOE_UNITS_AND_ATTRIBUTION.md`.
- Canonical core intervals remain rounded consistently to four decimals in the
  principal table and prose: pooled `[-0.2206,-0.0437]`, family-month
  `[-0.1607,0.1173]`, and paired movement `[0.0107,0.2102]`. Shorter appendix
  display precision is labeled table presentation, not a distinct draw set.

Source files checked include
`yax/revision/substantive_r3_20260905/results/baseline_reproduction/OCCUPATION_SERVICE_EXCLUSIONS.csv`
(SHA-256 `0dd47cb59dee2b0531e6289be76d40f1b2d3f12fbd474b6eb9477cf5229db0e0`)
and
`yax/revision/substantive_r3_20260905/heterogeneity/results/HETEROGENEITY_MODEL_RESULTS.csv`
(SHA-256 `e7640a4cfa8580b7f031408e575f5507806cb397138f6aeb218836f8b6ed7ac8`).
The numerical/source audit in `paper/scripts/audit_substantive_revision.py`
binds these corrections to the active sources.

E03 is not marked verified because G07 and W05 are not yet fully resolved and
the changed table notes have not been inspected in a compiled PDF.
