# Manuscript-safe factual statements

**Prepared:** 2026-09-05
**Use:** these are bounded formulations supported by the accompanying source audits. Numerical YAX results must still come from the canonical empirical results ledger.

## BCC comparison

### Version and estimand

> We compare our results with the August 12, 2026 revision of Brynjolfsson, Chandar, and Chen, which uses ADP payroll data through June 2026. Their primary sample consists of full-time, positive-earnings worker–firm matches at firms observed throughout the relevant balanced-panel window. Our CPS employment-stock population and survey-weighted national target therefore remain different even when age bands, exposure definitions, and endpoints are aligned.

> BCC reports several distinct quantities. Its widely cited 19 percent figure compares employment of highly exposed 22–25-year-olds with the path it would have followed had it kept pace with less-exposed workers of the same age. Its occupation-level long-difference regression instead estimates Q2–Q5 coefficients relative to Q1, with occupation employment weights. We do not treat the 19 percent figure as a regression coefficient or a hiring-rate estimate.

### Approximate grouping bridge

> The official Canaries Dashboard describes exposure groups formed with equal occupation weights, whereas the paper's occupation-level outcome regressions are employment weighted. The public paper does not provide a complete cutoff, tie, and membership algorithm. We therefore distinguish the weights used to form groups from the weights used to estimate outcomes and label our construction an approximate BCC-style bridge unless complete occupation-membership concordance can be verified.

### Stocks and flows

> BCC studies both employment stocks and employer-match flows. Its hiring measure counts new worker–firm matches over the preceding year relative to the cell's headcount one year earlier. A CPS transition from nonemployment to employment has a different risk set and excludes some employer-to-employer hiring transitions; the quantities are not directly interchangeable.

### Existing public evidence

> The August 2026 BCC appendix already presents monthly CPS age-by-exposure paths through June 2026 and ACS comparisons through 2024. Our contribution is not the first use of public CPS data to examine young workers in AI-exposed occupations. It is to hold a specified CPS employment-stock design fixed while auditing sensitivity to named exposure architectures, mapping/support constructions, and occupational conditioning restrictions.

## CPS production discontinuities

> CPS employment levels cross documented population-control changes in January 2025 and January 2026. BLS did not revise the official prior-month estimates onto the new bases. We consequently treat these boundaries as level-series discontinuities and report endpoint and window sensitivities rather than mechanically applying aggregate adjustment factors to age-by-occupation cells.

> October 2025 CPS data were not collected during the federal funding lapse. November 2025 used delayed and extended collection, a modified weighting procedure, lower sample overlap, and a 64.0 percent response rate. We preserve October as a missing calendar month, use elapsed calendar rather than row-adjacency lags, and report a sensitivity excluding September and November 2025.

> IPUMS subsequently processed a reissued January 2026 file and later corrections to longitudinal identifiers. We record the extract creation date, DDI, requested weights and link identifiers, and file hash so that readers can determine which revisions are incorporated.

Do not add: “these revisions explain the estimate.” The documents establish discontinuities and revisions, not their effect on YAX's coefficient.

## Exposure constructs

> Webb's scores measure textual overlap between technology patents and occupational tasks; Eloundou et al.'s scores assess whether LLMs or LLM-powered systems could substantially accelerate tasks at constant quality; and Felten, Raj, and Seamans map AI application areas to O*NET abilities. None directly records realized firm adoption in the CPS. We interpret differences across these measures as design sensitivity across exposure constructions, not as a causal horse race among deployed technologies.

> In Eloundou et al.'s published notation, alpha equals E1, beta equals E1 plus one-half E2, and zeta equals E1 plus E2. Our source column named `dv_rating_gamma` corresponds to the last construction; the column name should not be mistaken for the published symbol.

> Dingel–Neiman measures occupational teleworkability. We may use it to diagnose overlap with digital and desk work, but we do not relabel it as computerization. Direct computerization diagnostics use separately validated measures and retain their own vintages and support restrictions.

## Trend sensitivity

> Our Rambachan–Roth companion analysis uses the joint event-study coefficient vector and covariance matrix, an explicitly omitted reference period, and a stated postperiod linear functional. Because the headline grouped-binomial coefficient is not automatically an average of event-time coefficients, we report the dynamic sensitivity result as a companion estimand and explain its relationship to the static contrast.

> A failure to reject preperiod coefficients does not validate parallel trends. The sensitivity analysis instead reports how conclusions for the dynamic companion estimand change over economically interpreted smoothness or relative-magnitude restrictions.

## Novelty

Preferred affirmative contribution sentence:

> We hold a national monthly CPS young-versus-older employment-stock design fixed and quantify how its result changes across named occupational exposure architectures, mapping/support constructions, and occupational conditioning restrictions.

If a dated search statement is needed:

> In targeted publisher-site searches through September 5, 2026, we did not locate a peer-reviewed article in the declared ten journals that combines this national monthly CPS design with systematic within-design variation across named exposure architectures and mapping/support constructions. This search is not exhaustive and does not establish priority for the broader young-worker or public-CPS pattern.

Avoid:

- “first CPS evidence”;
- “first public-data test”;
- “no prior study varies exposure measures” without the narrow dated scope;
- “the literature has ignored crosswalks” unless a particular published implementation is verified;
- “our invalid exact-code merge reproduces published work.”

## References to include or update

- Brynjolfsson, Erik, Bharat Chandar, and Ruyu Chen. 2026. *Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence*. August 12 revision.
- Eloundou, Tyna, Sam Manning, Pamela Mishkin, and Daniel Rock. 2024. “GPTs are GPTs: Labor Market Impact Potential of LLMs.” *Science* 384.
- Emanuel, Natalia, Emma Harrington, and Amanda Pallais. 2026. “The Power of Proximity to Coworkers.” *Quarterly Journal of Economics* 141(3): 1825–1870.
- Felten, Edward, Manav Raj, and Robert Seamans. 2021. “Occupational, Industry, and Geographic Exposure to Artificial Intelligence: A Novel Dataset and Its Potential Uses.” *Strategic Management Journal* 42(12): 2195–2217.
- Rambachan, Ashesh, and Jonathan Roth. 2023. “A More Credible Approach to Parallel Trends.” *Review of Economic Studies* 90(5): 2555–2591.
- Webb, Michael. 2020. “The Impact of Artificial Intelligence on the Labor Market.” Working paper, January.

Use DOI or official URLs in the bibliography as recorded in the companion audits.
