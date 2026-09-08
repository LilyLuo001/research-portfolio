# ACS extension source evidence

Checked 2026-09-08. These are source facts used by
`ACS_EXTENSION_SPEC.md`; they are not empirical YAX results.

## BCC target

- [Brynjolfsson, Chandar, and Chen, August 2026](https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf),
  Appendix H, Table H.1: each row is the Q5-minus-Q1 difference between 2024
  and 2022 employment growth factors among ages 22--25. The table reports
  -0.022 for all employed and -0.019 after sequential restrictions ending in
  full-time civilian wage-and-salary workers. The paper says its confidence
  intervals use the 80 Census successive-difference replicate weights.
- The same appendix says its ACS figures use the same crosswalk and quintile
  definitions as its ADP analysis. Those complete memberships were not present
  in the public artifacts audited under B02, so YAX labels its reconstruction
  non-exact.

## Official ACS files and inference

- [Census Microdata API inventory](https://www.census.gov/data/developers/data-sets/census-microdata-api.html):
  ordinary ACS one-year PUMS are listed for 2005--2019 and 2021--2024; 2020 is
  absent from that standard series.
- [2024 one-year PUMS user guide](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2024ACS_PUMS_User_Guide.pdf),
  pages 10--11: use `PWGTP` for person estimates and `PWGTP1`--`PWGTP80` for
  replicate estimates; the SDR variance is `(4/80) sum_r (theta_r-theta)^2`.
- [ACS 2020 experimental-PUMS page](https://www.census.gov/programs-surveys/acs/data/experimental-data/2020-1-year-pums.html):
  2020 is explicitly an experimental product, not an ordinary one-year wave.
- [2026 ACS updates](https://www.census.gov/programs-surveys/acs/news/updates/2026.html):
  as of the checked update, the 2025 one-year release date remained under
  determination. The extension therefore ends in 2024.
- [ACS sample-design chapter](https://www2.census.gov/programs-surveys/acs/methodology/design_and_methodology/2022/acs_design_methodology_ch04_2022.pdf):
  addresses are assigned across five annual subframes and are not sampled more
  than once within a five-year period. This motivates the separate no-reuse
  calendar and the explicit limitation on long-panel year-block variance.

## Variable and occupation vintages

- Official one-year PUMS metadata show `TYPE` as the type-of-unit field in
  2017--2019 and `TYPEHUGQ` from 2021 onward. The runner requires the proper
  vintage-specific name and normalizes it only after reading.
- [Census occupation guidance](https://www.census.gov/topics/employment/industry-occupation/about/occupation.html)
  places the 2010 occupation list through the 2017 ACS and the 2018 occupation
  list beginning with the 2018 ACS.
- [Census 2018 comparison guidance](https://www.census.gov/programs-surveys/acs/guidance/comparing-acs-data/2018.html)
  warns that occupation categories changed in 2018 and directs users to a
  crosswalk. The runner therefore routes 2017 through the authenticated
  official bridge and uses 2018+ codes directly.
