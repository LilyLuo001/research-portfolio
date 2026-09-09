# RPS detailed-occupation adoption source evidence

Accessed: 2026-09-09

The author-maintained Real-Time Population Survey data page links the public
occupation workbook used here. The downloaded file is retained unchanged as
`inputs/rps_adoption_rates_by_occupation_20260806.xlsx`, SHA-256
`2212465781179782c6f69750af21b00bd545edc21581d9577fbf7affc1bf0c43`.
Its download endpoint is recorded in `ADOPTION_EXTENSION_SPEC.md`.

The workbook README states that:

- the data pool the August 2025, November 2025, February 2026, and May 2026
  RPS waves;
- the population is employed respondents with valid detailed occupation,
  at-work GenAI-use responses, and survey weights;
- `adoption_rate` is the survey-weighted share answering yes to whether they
  use generative AI for their job;
- `number_observations` is the unweighted pooled respondent count; and
- rates with fewer than 20 observations are suppressed.

The workbook contains sheets for 2018 SOC major, minor, and broad occupations
and for 2018 Census occupation codes. The last sheet has 505 data rows and the
four fields fixed in the specification. It supplies pooled point estimates and
counts, not detailed-cell standard errors, replicate weights, or quarterly
detailed-occupation rates. The workbook's citation row still contains a
placeholder, so the paper should cite the associated RPS measurement paper and
the author data page rather than reproduce the placeholder as a completed
citation.

These limitations rule out detailed-cell inferential claims and an occupation-
by-time adoption treatment. They do not prevent the fixed descriptive
occupation-level validation in `ADOPTION_EXTENSION_SPEC.md`.
