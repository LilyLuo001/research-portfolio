# Literature search and construct-admission ledger

Search date: 2026-09-05. The targeted journal scope was the American Economic Review, Quarterly Journal of Economics, Journal of Political Economy, Econometrica, Review of Economic Studies, Review of Economics and Statistics, American Economic Journal: Applied Economics, Journal of Finance, Review of Financial Studies, and Journal of Financial Economics. Searches combined each journal with occupational AI exposure, early-career/young employment, CPS employment stocks, exposure-measure sensitivity, automation, and AI adoption. This is a targeted search, not proof that no related article exists elsewhere.

## Load-bearing primary sources

| Source | Verified object | Use in revision |
|---|---|---|
| Brynjolfsson, Chandar, and Chen, “Canaries in the Coal Mine?”, revised 2026-08-12, <https://digitaleconomy.stanford.edu/publication/canaries-in-the-coal-mine-six-facts-about-the-recent-employment-effects-of-artificial-intelligence/> | ADP payroll data through June 2026; ages 22--25; reported 19% gap; hiring margin; alternative exposure and remote-work analyses; explicitly descriptive | Establishes that YAX does not discover the young-versus-older pattern. Its data, outcome, treatment, and controls differ from YAX. |
| Humlum and Vestergaard, “Large Language Models, Small Labor Market Effects,” BFI WP 2025-56, <https://bfi.uchicago.edu/working-papers/large-language-models-small-labor-market-effects/> | Representative adoption surveys linked to Danish administrative records; 11 occupations; earnings and recorded hours; difference-in-differences; updated 2025 version | Shows why adoption-linked earnings/hours results cannot be decomposed by changing an occupational exposure index in U.S. CPS stocks. |
| Webb, “The Impact of Artificial Intelligence on the Labor Market,” January 2020, <https://www.michaelwebb.co/webb_ai.pdf> | Patent--task overlap with distinct AI, software, and robot measures | Supports admitting Webb AI as a conceptually distinct external architecture and retaining Webb software as a prior-computerization control. |
| OECD, “The OECD AI Exposure Measure,” 2026-05-26, <https://www.oecd.org/en/publications/the-oecd-ai-exposure-measure_f3da0f0a-en.html> | Gap between nine AI capability domains and occupational demands | Supports admitting the reversed capability gap as an external architecture. |
| Eloundou et al., “GPTs are GPTs,” Science 2024 | Direct and software-complemented task acceleration; primitives D and S | Defines the task-based family and the lambda grid. |
| Felten, Raj, and Seamans, AEA P&P 2018 and Strategic Management Journal 2021 | Ability-based AI occupational exposure | Defines the AIOE family. |
| Andrews, Gentzkow, and Shapiro, QJE 2017, <https://academic.oup.com/qje/article-abstract/132/4/1553/3861634> | Moment-level sensitivity framework | Motivates tracing which construction perturbations supply estimator information; YAX does not claim to implement their exact measure. |
| Rambachan and Roth, Review of Economic Studies 2023, <https://www.jonathandroth.com/assets/files/HonestParallelTrends_Main.pdf> | Sensitivity analysis for violations of parallel trends | Provides trend-uncertainty context; YAX does not borrow causal identification from it. |
| Brynjolfsson, Li, and Raymond, QJE 2025, <https://academic.oup.com/qje/article/140/2/889/7990658> | Staggered deployment to 5,172 support agents; productivity effects and experience heterogeneity | Distinguishes exposure from observed tool access. |

## Top-ten result

The targeted search found close but non-identical work on workplace AI deployment, automation and worker outcomes, task models, firm AI investment, remote work, and knowledge production. It did not locate a peer-reviewed article in the ten declared journals that fixes a national CPS young-versus-older employment-stock design while varying the occupational exposure construction and tracing taxonomy, reference-tail, estimator-information, and mobility consequences. The novelty statement is therefore narrow and search-qualified.

## Architecture admission decisions

- **Admitted:** Webb AI patent--task overlap and the reversed OECD capability gap. Each has a documented construct, public source, non-title mapping, full-component support, distinct quintile cuts, and more than 80% preperiod employment coverage. Both were admitted before estimating their YAX outcomes under the revision rule.
- **Retained as control, not treatment:** Webb software exposure. Its source correlation with Webb AI is 0.7021, so they overlap conceptually but are not identical.
- **Not admitted as AI architecture:** Frey--Osborne. It is useful as an automation-risk/computerization comparator, but its construct bundles broader computerization and robotics rather than isolating AI capability.
- **Not admitted:** newly LLM-annotated alternatives lacking a frozen outcome-independent source/coverage/mapping decision in this revision. Adding them after viewing results would expand rather than audit the declared architecture set.

## Bridge that remains unidentified

BCC and Humlum--Vestergaard differ in country, data source, population, outcome, adoption information, empirical design, and period. YAX changes exposure construction inside one U.S. CPS stock design. It can show that external architectures attenuate the CPS contrast, but it cannot decompose the ADP--Denmark disagreement without aligned outcomes, populations, adoption measures, and treatment definitions.
