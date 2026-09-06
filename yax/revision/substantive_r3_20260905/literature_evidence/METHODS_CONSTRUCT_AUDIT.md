# Methods and exposure-construct audit

**Audit date:** 2026-09-05
**Purpose:** establish what each cited method or exposure measure actually supplies, and prevent the manuscript from converting an exposure score into observed adoption or a trend-sensitivity method into a causal test.

## Rambachan–Roth trend sensitivity

### Verified source

Ashesh Rambachan and Jonathan Roth, “A More Credible Approach to Parallel Trends,” *Review of Economic Studies* 90(5), 2023, 2555–2591.

- [Publisher/DOI](https://doi.org/10.1093/restud/rdad018)
- [Author-hosted paper](https://jonathandroth.github.io/assets/files/HonestParallelTrends_Main.pdf)
- [Official `HonestDiD` repository](https://github.com/asheshrambachan/HonestDiD)

The published title is **“A More Credible Approach to Parallel Trends.”** “An Honest Approach to Parallel Trends” was an earlier title and should not be used as the final bibliographic title.

### Required inputs and design choices

A valid `HonestDiD`-style analysis requires, at minimum:

1. an event-study coefficient vector `betahat`;
2. the corresponding **full covariance matrix** `sigma`, not only marginal standard errors;
3. correctly ordered pre- and post-period coefficients with the omitted reference period documented;
4. explicit `numPrePeriods` and `numPostPeriods`;
5. a vector `l_vec` defining the post-period linear functional (for example, a selected endpoint or an average with stated weights);
6. a declared restriction family and parameter grid.

The smoothness restriction bounds changes in the slope of differential trends; its (M) values inherit the chosen event-time units. The relative-magnitude restriction bounds post-treatment violations relative to deviations observed in the preperiod; its \(\bar M\) values require an economically explained grid. Neither grid should be selected after inspecting which value preserves a preferred conclusion.

### Applicability to YAX

The static YAX grouped-binomial Q5–Q1 coefficient is nonlinear and is not automatically an average of event-time coefficients. Feeding that coefficient and its single standard error to `HonestDiD` would be an implementation error. A defensible analysis must estimate a compatible dynamic companion estimand, validate the event-study covariance and its rank, define the post functional, and explain how the companion estimand relates to the headline static coefficient.

If the conventional confidence interval already contains zero at the no-deviation benchmark, there is no positive zero-exclusion robustness threshold to “lose.” Report that fact directly. Failure to reject pretrends does not validate parallel trends, and a sensitivity interval does not identify AI adoption as the cause of a post-2022 break.

## Webb exposure measures

### Verified source

Michael Webb, “The Impact of Artificial Intelligence on the Labor Market,” working paper, January 2020.

- [Author-hosted paper](https://www.michaelwebb.co/webb_ai.pdf)

### Construct

Webb uses text overlap between patent descriptions and occupational task descriptions to build distinct exposure measures for software, industrial robots, and artificial intelligence. The exercise measures the relationship between patent language and occupational tasks; it does not observe realized firm adoption, deployment intensity, or worker-level use of generative AI during YAX's postperiod.

### Manuscript rule

The software and AI scores are useful as architectures with different technological content. They cannot be described as realized software or AI treatment. A difference between Webb AI and Webb software coefficients is a difference across constructed exposure definitions, conditional on common support and scale—not direct evidence that one technology was deployed and the other was not.

## Eloundou et al. GPT task-exposure measures

### Verified source

Tyna Eloundou, Sam Manning, Pamela Mishkin, and Daniel Rock, “GPTs are GPTs: Labor Market Impact Potential of LLMs,” *Science* 384, 2024; preprint first posted in 2023.

- [arXiv record and versions](https://arxiv.org/abs/2303.10130)
- [Science DOI](https://doi.org/10.1126/science.adj0998)

### Construct and notation

Tasks are assessed against a rubric asking whether an LLM or LLM-powered system could reduce completion time by at least 50 percent while maintaining quality. In the published notation:

- \(\alpha=E1\): direct LLM exposure or exposure through a simple interface;
- \(\beta=E1+0.5E2\): direct exposure plus half-weighted exposure requiring complementary LLM-powered software;
- \(\zeta=E1+E2\): direct plus complementary-system exposure.

If the YAX source column is named `dv_rating_gamma`, the article should say that this is a repository column name corresponding to the published \(\zeta\) construction. It should not silently rename the published quantity gamma.

### Manuscript rule

These are task-level capability/exposure assessments. They do not measure firm adoption, usage, output substitution, or a dated deployment path. The distinction between E1 and E2 can motivate architecture comparisons, but coefficient monotonicity over \(\alpha,\beta,\zeta\) does not reveal which capabilities were actually deployed in 2023–2026.

## Felten–Raj–Seamans AIOE

### Verified source

Edward Felten, Manav Raj, and Robert Seamans, “Occupational, Industry, and Geographic Exposure to Artificial Intelligence: A Novel Dataset and Its Potential Uses,” *Strategic Management Journal* 42(12), 2021, 2195–2217.

- [Publisher/DOI](https://doi.org/10.1002/smj.3286)
- [Open Princeton copy](https://oar.princeton.edu/bitstream/88435/pr11551/1/OccupationalIndustry.pdf)

### Construct

AIOE maps ten AI application areas to 52 O*NET abilities using human judgments collected through Mechanical Turk. Occupation exposure combines the AI–ability relatedness values with O*NET information on the prevalence and importance of abilities. The paper constructs scores for 832 detailed O*NET-SOC occupations, aggregates to 774 six-digit occupations by taking means, and standardizes the occupation index without employment weighting. The paper uses O*NET 24.3 (May 2020).

### Manuscript rule

AIOE is a general AI–ability exposure measure. It is not intrinsically an automation/substitution score and does not observe generative-AI adoption. AIOE's high correlation with computer use or teleworkability is a measured overlap property, not proof that AIOE “is computerization.”

## Cross-construct interpretation

The four source families answer different measurement questions:

| Construct | What is directly encoded | What is not directly encoded |
|---|---|---|
| Webb | Patent–task textual exposure by technology family | Actual adoption or task displacement in YAX dates |
| Eloundou \(\alpha/\beta/\zeta\) | Assessed LLM capability to accelerate tasks, with/without complementary software | Firm use, equilibrium substitution, realized employment effect |
| Felten AIOE | AI-application relatedness to occupational abilities | Automation direction, GenAI timing, adoption |
| Dingel–Neiman | Feasibility of performing occupational tasks from home | Computerization or AI exposure |

Dingel–Neiman teleworkability may be a useful diagnostic proxy for digital/desk-work overlap, but it must not be labeled a computerization measure. A direct computerization analysis requires a separately validated preperiod measure such as an archived O*NET computer-use item, Webb software exposure, or a clearly specified routine-task index.

### Safe common interpretation

> The measures encode different relationships between technologies, tasks, and occupational abilities; none records realized adoption in the CPS. We therefore interpret coefficient differences as sensitivity of an occupational exposure comparison to the score construction, support, and scaling—not as a causal horse race among deployed technologies.
