# Targeted external/source verification for V3

Checked for this prompt on 2026-09-06. Recheck changing release and software information when executing. These notes resolve specific feasibility/method issues; they are not a new literature review or empirical replication.

## 1. Disputed row count: attached PDF, not external research

Current appendix, physical/printed pages 3 and 4: page 3 ends before the count and has footer 3. Page 4 begins with 6,188,956. Main Table 1 also shows 6,188,956. The supplied A-report's 36,188,956 appears to concatenate that footer with the next page's count. Rendered inspection images are included under `inputs/inspection/`. Verify the source calculation as a separate matter.

## 2. Earnings after March 2023

IPUMS CPS, EARNWEEK2 description: this variable provides rounded weekly earnings and applies the comparable rounding rules to earlier observations. Comparability, changing topcodes, rotation-group differences, allocation and earnings weights still require attention. The existence of the variable does not establish that it is already in the author's extract.

Source: `https://cps.ipums.org/cps-action/variables/EARNWEEK2`

Additional official notes: `https://cps.ipums.org/cps/outgoing_rotation_notes.shtml`

## 3. Enrollment universe

IPUMS SCHLCOLL's universe list gives 16–54 from 2013 onward, while parts of its descriptive prose mention ASEC specifically. Do not resolve such ambiguity from a search snippet alone. Census's December 2019 and August 2025 Basic CPS dictionaries explicitly list PESCHENR's edited universe as PRPERTYP=2 and PRTAGE=16–54. In the August 2025 PDF, this is printed page 6-72, physical page 94; the December 2019 continuation is printed 6-73, physical page 94. These checks support the need to avoid treating ages 55–65 as observed non-enrolled people. Audit the actual monthly variables and dates before implementation.

Sources:

- `https://cps.ipums.org/cps-action/variables/SCHLCOLL`
- `https://www2.census.gov/programs-surveys/cps/techdocs/cpsdec19.pdf`
- `https://www2.census.gov/programs-surveys/cps/techdocs/cpsaug25.pdf`

## 4. BTOS source and question change

BTOS is produced by the U.S. Census Bureau. The Census Bureau documents that the core AI-use question changed on November 17, 2025 from producing goods/services to any business function. Source/wording continuity must be checked before treating the series as measured adoption growth. No causal interpretation follows merely from observing use.

Sources:

- `https://www.census.gov/programs-surveys/btos.html`
- `https://www.census.gov/hfp/btos/about`
- `https://www.census.gov/library/stories/2026/05/ai-use-businesses.html`

## 5. ACS availability and 2020 comparability

The official 2026 updates page states that the 2025 ACS one-year release date is being determined; do not assume those microdata are available. Ordinary one-year products and overlapping five-year products are different objects. Official comparison guidance says not to compare 2020 one-year experimental estimates with other data. An annual extension must address this rather than silently splicing 2020 into the ordinary series.

Sources:

- `https://www.census.gov/programs-surveys/acs/news/updates/2026.html`
- `https://www.census.gov/programs-surveys/acs/guidance/comparing-acs-data.html`
- `https://www.census.gov/programs-surveys/acs/data/experimental-data.html`

## 6. Public adoption products

The St. Louis Fed documents public RPS/Bick–Blandin–Deming adoption products, including occupation/industry series. Verify the level of aggregation, exact variable, dates, and sampling uncertainty; public broad categories do not establish a precise detailed-occupation panel.

Sources:

- `https://news.research.stlouisfed.org/2026/07/fred-adds-data-about-the-adoption-of-generative-artificial-intelligence/`
- `https://fred.stlouisfed.org/data/RPSGENAIUSAGESHAREOCC5`
- `https://www.nber.org/system/files/working_papers/w32966/w32966.pdf`

## 7. BCC public benchmark

The August 2026 paper contains public CPS and ACS comparisons in Section 5 and Appendix H. Its data-availability statement distinguishes proprietary ADP data, public derived outputs, and code available from the authors on request. Inspect exact public targets and feasible reconstruction before claiming novelty or exact replication. A request-only statement is not authorization to contact authors on the user's behalf.

Source: `https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf`

## 8. HonestDiD

The authors' methodological paper defines the target as a linear combination of post-treatment effects. The usual relative-magnitude restriction bounds post consecutive-period changes in the counterfactual differential trend by a multiple of the largest pre consecutive-period change. Smoothness bounds second differences; zero smoothness allows an exactly linear differential trend. These definitions are not interchangeable with the largest plotted coefficient or a simple level bound. Use the exact published/installed version and full covariance.

Sources:

- `https://asheshrambachan.github.io/assets/files/hpt-draft.pdf`
- `https://cran.r-project.org/web/packages/HonestDiD/refman/HonestDiD.html`

## 9. Omitted-variable sensitivity

Oster's published coefficient-stability framework and Diegert–Masten–Poirier's work impose specific model/selection assumptions. The latter's current paper develops linear-regression sensitivity with endogenous controls; it is not a plug-in justification for grouped-binomial pseudo-R-squared calculations. Verify applicability before implementation. Also check Masten–Poirier's distinction between sensitivity of magnitude and sign.

Sources:

- `https://www.tandfonline.com/doi/full/10.1080/07350015.2016.1227711`
- `https://arxiv.org/html/2206.02303v6`
- `https://mattmasten.github.io/research/`
- `https://www.aeaweb.org/articles?id=10.1257/aer.20230242`
