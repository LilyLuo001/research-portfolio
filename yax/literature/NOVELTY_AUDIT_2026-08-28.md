# YAX latest-version novelty audit

**Audit date:** 2026-08-28  
**Outcome seal:** intact. No protected post-period YAX outcome was opened.  
**Question audited:** whether prior work already completes the full chain

> cross-family exposure construction → construct comparison → identifying-
> variation audit → mapping/common support → same-data/same-specification
> downstream consequence with direct paired inference.

## Result

**PASS, with a materially narrowed claim.** No source found completes the full
chain. YAX may not claim that it is the first study to compare exposure
measures, to harmonise them, or to show that exposure choice changes a
coefficient. Those components already exist.

The closest new boundary is Pulito, Pytlikova, Schroeder and Lodefalk (2026),
which predicts one observed firm-adoption outcome with five standardised
occupation-based exposure measures under a common design. Brynjolfsson,
Chandar and Chen's August 2026 revision is also closer than the inherited plan:
it studies the exact 22--25 employment debate, uses alternative exposure
measures, improves its crosswalk, controls for remote work, and benchmarks ADP
against CPS and ACS.

YAX's remaining contribution is therefore the **integration and inference**:

1. compare the economic constructs represented by major exposure families;
2. name and quantify the occupations that supply identifying residual variation;
3. separate construction, taxonomy mapping and common-support transformations;
4. hold the public outcome, support and specification fixed;
5. infer coefficient differences directly with common bootstrap draws and a
   pre-specified equivalence bound.

This is a real but narrower contribution. The novelty gate would fail if the
paper reverted to any of the retired claims above.

## Latest-version checks

| Source | Latest version opened | What the primary source actually establishes | Boundary for YAX |
|---|---|---|---|
| Felten, Raj & Seamans (2018) | AEA P&P 108, May 2018, DOI 10.1257/pandp.20181021 | Method linking AI applications to O\*NET abilities and then occupations | Foundation for AIOE construction, not a cross-measure consequence study |
| Felten, Raj & Seamans (2021) | *Strategic Management Journal* 42(12), published online 2021-04-28, DOI 10.1002/smj.3286 | Ten EFF AI applications are related to 52 O\*NET abilities by MTurk; ability exposure is aggregated with occupation-specific importance and prevalence and normalised by the ability portfolio | Establishes AIOE's ability architecture; agnostic about complement/substitute and does not run YAX's chain |
| Eloundou et al. (2024) | *Science* 384(6702), 2024-06-21; methods checked against arXiv v5, 2023-08-21 | Humans and GPT-4 score O\*NET tasks by potential for at least a 50% task-time reduction at equal quality; alpha is E1, beta is E1 + 0.5 E2, and the broad published notation is zeta = E1 + E2 | Establishes task/LLM architecture; the repository's `gamma` label is a data-column alias, not the paper's notation |
| Yin, Vu & Persico (2026) | NBER WP 35110, April 2026 | Holding the rubric fixed while changing the annotating frontier LLM produces large score and downstream-coefficient instability | Very close within-rubric measurement-error study; no cross-family mapping/support/influence chain |
| Yin & Ogut (2026) | arXiv v2, 2026-05-27 | Holding the observed-use design fixed while changing platform-user inputs materially changes exposure and employment estimates; BLS reweighting attenuates estimates | Very close input-selection study; it varies platform composition within one family rather than the full cross-family chain |
| Rai (2026) | MPRA 129904, modified 2026-07-08 | Across 773 occupations AIOE and Eloundou load strongly on cognitive content (0.85 and 0.70); Webb behaves differently; wage relationships change with cognitive controls | Direct construct-validity predecessor; no fixed post-ChatGPT Y/specification, influence audit or paired contrast |
| Frank et al. (2025) | *PNAS Nexus* 4(4), pgaf107, published 2025-04-02 | Several scores disagree and individually predict 2010--2020 unemployment risk poorly; an ensemble adds predictive value | Same outcome across scores, but pre-ChatGPT and without mapping/common-support/influence/paired-difference audit |
| Eckhardt & Goldschlag (2025) | EIG report, 2025-08-10; public code checked at 2026-07-27 commit | Five measures are used for CPS unemployment, labour-force exit and switching; code explicitly implements alternative mapping rules | Important public-data predecessor. Measure-specific regressions filter on each measure's availability and do not use one common support or paired direct coefficient differences |
| Budget Lab (2026), measurement | 2026-02-19 | Harmonises seven metrics to SOC 2018, reports 867 occupations on any metric and 710 on all, standardises and constructs PCA summaries | Strong mapping/harmonisation predecessor; no downstream outcome on this page |
| Budget Lab (2026), outcomes | 2026-05-07 | Uses harmonised exposure/PCA in CPS-style public outcomes and synthetic-DID analyses; finds no clear effects and explicitly discusses remote work | Downstream public-data predecessor, but not the full construct/influence/common-support/paired-comparison chain |
| Pulito et al. (2026) | Örebro WP 3/2026, 2026-03-27 | In 2,799 Danish firms, the same observed Core-AI-adoption design is estimated with five standardised exposure measures; predictive associations differ across measures | **Closest same-Y/same-spec source.** No construct-content, mapping/support or influence audit; separate coefficients are not compared with paired inference; Y is firm adoption, not the contested young-worker outcome |
| Brynjolfsson, Chandar & Chen (2026) | Stanford DEL working paper, revised 2026-08-12, data through June 2026 | 22--25 employment stocks diverge by exposure; the revision uses Eloundou GPT-4 beta, Anthropic usage and five alternatives, an improved SOC mapping, remote-work controls, and CPS/ACS benchmarks | Exact debate and multiple-X predecessor. It does not report the full measurement architecture, fixed common support, identifying influence, or direct paired differences |
| Emanuel, Harrington & Pallais (2026) | *QJE* 141(3), published 2026-05-12, issue August 2026, DOI 10.1093/qje/qjag027 | National CPS DDD compares young (<29) with older college graduates in remotable occupations; the 2022--2024 gap predates broad generative-AI diffusion and persists after a generative-AI exposure control | Makes remote work a core rival. It does not compare AI-exposure architectures |
| Lund et al. (2026) | arXiv v1, 2026-06-22 | Reviews temporal, geographic and ontological limits of static exposure scores | Conceptual synthesis, no fixed downstream design |
| Merola et al. (ILO, 2026) | ILO brief, 2026-04-17, DOI 10.54394/00033279 | Distinguishes construction concepts and stresses that susceptibility is not realised impact | Institutional measurement critique, no downstream chain |
| OECD (2026) | OECD AI Papers No. 59, 2026-05-26, DOI 10.1787/f3da0f0a-en | Maps nine AI-capability domains to occupational requirements in an updateable capability-gap measure | New construction family, no downstream Y |
| Mouchel, Bouquet & Sheffi (2026) | arXiv v1, 2026-05-14 | Evidence-grounded retrieval measure for O\*NET occupation-task pairs, contrasted with model-prior scores | New construction family, no downstream Y |
| Tomei & Klein Teeselink (2026) | arXiv v1, 2026-05-04 | Reinforcement-learning feasibility measure for O\*NET tasks, expert validated and divergent from existing indices | New construction family, no downstream Y |
| Fenoaltea et al. (2026) | *PNAS Nexus* 5(6), pgag185, 2026-06-23 | Startup-backed applications are matched to O\*NET occupations to measure market-targeted rather than purely technical exposure | New construction family; explicitly does not estimate adoption or net employment effects |
| del Rio-Chanona et al. (2025) | arXiv v1, 2025-09-18 | Reviews and quantitatively compares ex-ante exposure measures and ex-post evidence | Broad synthesis, not one fixed empirical chain |
| Steele & Cruz (2026) | arXiv v1, 2026-07-16 | Compares six projections, adds a query-based measure, and averages five for career guidance | Cross-measure comparison, but no post-event labour design or paired inference |

## Boundary table

Legend: **Yes** means the paper makes that component an empirical object;
**Partial** means it contains a related analysis but not YAX's specified test.

| Paper | What definition/input of X varies? | Construct validity tested? | Identifying variation audited? | Mapping/common support audited? | Same downstream Y/spec held fixed? | Downstream coefficient consequence? | What YAX still uniquely adds |
|---|---|---:|---:|---:|---:|---:|---|
| Yin--Vu--Persico | annotating LLM, same rubric | Partial | No | No | Yes | Yes | cross-family constructs, mapping/support, occupation influence, paired inference |
| Yin--Ogut | platform-user input, same observed-use family | Partial | No | Partial (reweighting) | Yes | Yes | cross-family chain and identifying occupations |
| Rai | AIOE, Eloundou, Webb | Yes | No | No | No | Partial | downstream fixed design and paired inference |
| Frank et al. | several exposure scores and ensemble | Partial | No | No | Yes | Yes | post-ChatGPT fixed design, mapping/support and influence |
| EIG | five published measures and mapping approaches | Partial | No | Partial | Partial | Yes | common support, direct paired differences and influence audit |
| Budget Lab | seven harmonised measures/PCA | Partial | No | Yes | Partial | Yes | individual cross-family Test C on common support with paired inference |
| Pulito et al. | five indices predicting observed adoption | Partial | No | No | Yes | Yes | construct, mapping/support and influence audits; young-worker consequence; paired inference |
| BCC Aug. 2026 | Eloundou, Anthropic use, five alternatives | Partial | No | Partial | Partial | Yes | transparent cross-family architecture, common support, influence and direct paired differences |
| EHP QJE | remotability plus one generative-AI control | No | No | No | No | Partial | multiple AI architectures and measurement-consequence chain |
| Lund / ILO / OECD | conceptual or capability architecture | Yes/Partial | No | No | No | No | empirical integrated chain |
| Mouchel / Tomei / Fenoaltea | evidence, RL feasibility, startup targeting | Yes/Partial | No | No | No | No | fixed downstream comparison and influence/support audit |
| del Rio-Chanona review | multiple ex-ante scores | Partial | No | No | No | Review | one frozen empirical chain |
| Steele--Cruz | six projections plus query input | Partial | No | No | Partial | Partial | post-event outcome and paired common-support inference |

## Search record and negative-result interpretation

Searches included combinations of: `occupational AI exposure measures compare
coefficients common support crosswalk employment 2026`, `AI exposure same
outcome specification multiple measures`, `AI exposure identifying variation
occupation`, `AI exposure score measurement downstream coefficient`, and
citations/references in the latest BCC, ILO, OECD, Budget Lab, Rai and Pulito
sources. Published articles, institutional reports and current working-paper
registries were searched.

No source located by 2026-08-28 performs every element of the boxed chain. This
is a dated search result, not a timeless claim. Pulito et al. and BCC are
prominently disclosed because omitting either would overstate novelty.

