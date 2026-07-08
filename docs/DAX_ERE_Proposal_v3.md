# Dynamic AI Exposure: Capability, Cost, and the Timing of U.S. Labor-Market Adjustment

**A Research Proposal Submitted to the OpenAI Economic Research Exchange**
Priority area: Labor-market effects | Timeline: Medium term, 6–12 months
Principal Investigator: [PI NAME], Professor of Economics, Boston University
Research Assistant: Qingyan Luo, PhD Candidate in Economics, Boston University

---

## 1. Research Question and Motivation

Which occupations has AI begun to displace, augment, or expand, and can model releases and price changes predict which occupations will adjust next? Existing evidence gives sharply different answers. Field experiments report productivity gains above 15 percent (Brynjolfsson, Li, and Raymond 2025). Danish administrative data rule out aggregate earnings effects larger than 2 percent (Humlum and Vestergaard 2025). U.S. payroll data, by contrast, show a 13 percent relative employment decline among workers ages 22–25 in the most AI-exposed occupations (Brynjolfsson, Chandar, and Chen 2025). These findings are difficult to reconcile unless current exposure measures miss the timing of economically relevant AI adoption.

This proposal argues that the apparent contradiction reflects a measurement problem. Widely used exposure scores, including Webb (2020), Felten, Raj, and Seamans (2023), and Eloundou et al. (2024), fix technology at a single point in time, often around 2022. Such measures can rank occupations by long-run vulnerability, but they cannot identify when an occupation crosses the adoption frontier. That timing is central to the Exchange's labor-market priority: identifying which occupations are already experiencing augmentation, displacement, new task creation, or employment growth as model capabilities improve. To position the object precisely, the index we build measures the *displacement frontier* — the set of tasks where substitution has become privately cost-effective — not the net general-equilibrium employment effect, which also reflects productivity, reinstatement, and demand channels (Acemoglu and Restrepo 2022; Acemoglu 2024).

We construct a publicly documented, monthly, cost-thresholded Dynamic AI Exposure index (DAX). For each occupation-month, DAX measures the wage-bill share of tasks for which AI substitution has become economically feasible. The index updates mechanically with each model release and price change. It therefore serves as a maintained public measurement instrument, rather than a one-time exposure score. We validate threshold crossings against OpenAI usage aggregates and test whether changes in DAX predict U.S. employment and hours adjustment when static exposure levels do not. Because the price margin is the index's most distinctive feature, the May 2024 GPT-4o launch — which halved the effective price with little contemporaneous capability change — serves as the lead identification event: a near-pure price experiment that no capability-only exposure measure can exploit.

## 2. Research Design

### 2.1 The Dynamic AI Exposure Index

A cost-minimizing firm substitutes AI for labor on a task when the expected AI cost per successful completion falls below the labor cost:

$$c/\pi + f(1-\pi)/\pi < w,$$

where $c$ denotes inference cost per attempt, $\pi$ the task success probability, $f$ the cost of a failed attempt, and $w$ the wage cost per completed task. Each input follows a transparent measurement rule. We measure $w$ using OEWS mean wages prorated to O\*NET tasks with importance-and-frequency time shares. We measure token footprints, and therefore $c$, by executing each mapped task prompt on each model vintage. For each occupation-month, DAX equals the wage-bill share of the occupation's O\*NET tasks satisfying the inequality.

One structural limitation is stated up front: the inequality is an average-cost, whole-task substitution condition, while firms can route easy sub-instances of a task to AI before the average condition holds. DAX is therefore a full-task feasibility frontier. A single pre-specified distributional variant, which draws within-task difficulty from item-level benchmark score dispersion, bounds the sensitivity of crossing dates to sub-task heterogeneity.

Four design choices discipline the construction. First, we measure $\pi$ using public capability evaluations mapped to tasks. GDPval and its open gold subset provide the primary mapping (OpenAI 2025); the month-one design memo files the full mapping protocol — matching algorithm, similarity scores, coverage rates, and human-validation procedure — and headline results are re-estimated on the top quartile of match quality. We also implement two independent alternatives: a benchmark-to-ability layer following Tolan et al. (2020), and Eloundou-style task annotation rescored for each model generation. Headline results must survive all three mappings under the quantitative standard filed in Section 7. Because benchmarks measure single-shot accuracy while production deployments use retries, retrieval, and human review, we additionally apply a deployment adjustment $\delta$ that scales the failure rate, $\pi_{\mathrm{eff}} = 1 - \delta(1-\pi)$, reported at $\delta = 1.0$, $0.8$, and $0.6$ as bracketing bounds; benchmark-only $\pi$ dates crossings too late, which would masquerade as pre-trends. We estimate both average-case and perturbation-robust success probabilities because firms condition adoption on reliability, not only average accuracy.

Second, we measure $c$ from API price histories converted into cost per task using observed token footprints. Two cost refinements matter. For reasoning models that bill chain-of-thought tokens separately, we disaggregate footprints and report DAX under both $c_{\mathrm{billed}}$ (all tokens) and $c_{\mathrm{effective}}$ (completion only), bracketing a cost bias that would otherwise concentrate in complex, high-wage tasks. And because list prices overstate costs for enterprise and open-weight deployment, we construct three cost variants — API list, enterprise-discounted ($0.6 \times$ list), and open-weight marginal cost — and require the crossing chronology to be robust across them.

Third, because the adoption condition requires a dollar-valued failure cost, we specify $f$ as a multiple of the task wage: $0.25w$, $1w$, and $4w$ for low, medium, and high O\*NET consequence-of-error tiers. We test robustness across a grid that halves and doubles these values and includes the $f=0$ pure-retry bound. The O\*NET ordinal tier determines only which multiple applies; no result may depend on a single cardinal choice. As a discipline on the threshold structure itself, we report the share of occupation-event cells whose crossing status flips anywhere on this grid; a pre-registered flip rate above 20 percent triggers a redesign of the threshold before any outcome analysis.

Fourth, we freeze O\*NET task bundles, OEWS wages, and wage-bill weights at 2021 vintages, so all variation in DAX comes from capability and price, not from occupational reclassification or contemporaneous wage movements. Two vintage checks accompany the freeze. A "live" DAX variant with annually updated O\*NET bundles is reported as a decomposition of technology-driven versus reorganization-driven exposure change — updating the bundles conditions on an outcome of the technology, so the live variant is informative rather than corrective. And because 2021 wages embed pandemic distortions, especially in hospitality and health care, we report a 2019 OEWS alternative wage baseline and flag occupations where the two vintages diverge materially.

DAX functions as a reduced-form adoption-frontier proxy. It jumps at dated, public events, including the GPT-4 release in March 2023, the launch of GPT-4o at half the GPT-4 Turbo price in May 2024, o1 in September 2024, and subsequent releases and price changes. Recent work emphasizes that AI exposure evolves over time rather than remaining fixed (Svanberg et al. 2024; Dominski and Lee 2025; Wang, Wei, and Wang 2026). DAX differs from existing dynamic measures in two economically important respects. It moves with price as well as capability, so a price cut can move an occupation across the frontier without changing model performance. It also has threshold structure, which produces discrete, dateable crossings suitable for event-study estimation.

### 2.2 Identification

We estimate stacked event studies around capability and price events. Treatment intensity equals $\Delta\mathrm{DAX}$ for an occupation-event: the wage-bill share of tasks newly crossing the feasibility threshold at that event. We estimate effects using monthly IPUMS-CPS microdata from November 2021 through 2026, heterogeneity-robust difference-in-differences methods (Callaway and Sant'Anna 2021), and Rambachan-Roth sensitivity analysis for deviations from parallel trends (Rambachan and Roth 2023). The primary outcomes are employment and hours among workers ages 22–25, where recent payroll evidence locates the adjustment margin. Wages are secondary outcomes, occupational switching is auxiliary, and multiple-testing corrections cover the primary outcome set. A pre-specified secondary analysis splits the 22–25 sample by college attainment, since displacement of routine entry-level tasks and credential substitution are distinct mechanisms; education cells are thin, so this analysis carries its own power budget and makes no headline claims.

Because $\Delta\mathrm{DAX}$ is a continuous dose realized at common calendar dates, rather than a staggered binary treatment, we state the design explicitly. For each event, we estimate a dose-response event study that interacts $\Delta\mathrm{DAX}$ with event-time indicators and includes occupation, month, and industry-by-month fixed effects. We stack events using event-specific clean windows so that one event's post-period does not contaminate a later event's pre-period, and occupations accumulate dose across events. Identification relies on the strong parallel-trends condition for continuous treatments (Callaway, Goodman-Bacon, and Sant'Anna 2024), which we state as a numbered identifying condition in the design memo: conditional on static-exposure decile, industry-by-month fixed effects, and occupation-level interest-rate sensitivity, average untreated potential outcomes evolve identically across occupations with different doses. Because this condition is stronger than binary parallel trends, nonparametric binned dose-response plots accompany every parametric estimate as required figures, which also tests whether the response is linear or a step function in the dose. Comparisons occur between higher- and lower-dose occupations within the same static-exposure decile, with same-decile occupations that experience no crossing at the event serving as the untreated contrast. The month-one memo pre-specifies the four stacking parameters — window length, event-inclusion criteria including the minimum $\Delta\mathrm{DAX}$ for an event to count, the dose-accumulation function across events, and the handling of occupations that crossed at earlier events when constructing later clean windows — together with an event-by-event table of crossing counts, dose distributions, and window bounds.

CPS density for workers ages 22–25 cannot support precise estimates at the three-digit occupation-by-month level. We therefore estimate at the level of $\Delta\mathrm{DAX}$ dose bins and cluster inference by occupation. Because CPS occupation codes map many-to-many into O\*NET-SOC codes, many-to-many cells receive employment-weighted average doses, and we report within-code dose dispersion as a measurement-quality diagnostic. The month-one design memo reports ex ante power calculations, including cell counts, baseline variances, crosswalk treatment, and minimum detectable effects benchmarked against the 13 percent payroll estimate, before we estimate the main outcome models.

The central horse race is intentionally demanding. $\Delta\mathrm{DAX}$ must add predictive content beyond four alternatives: an ensemble of static scores from Felten, Raj, and Seamans (2023), Eloundou et al. (2024), and Webb (2020); the same static scores interacted flexibly with event dates; a capability-only dynamic index that removes the price margin; and a non-AI benchmark — a prediction model built only from occupation characteristics (wage, education, routine-task intensity, import penetration) — which tests whether $\Delta\mathrm{DAX}$ adds content beyond repackaged routine intensity. We assess incremental value using leave-one-event-out prediction rather than in-sample fit. Within the horse race, the lead specification isolates the price margin at the GPT-4o event, where price moved sharply and capability little. This comparison answers the key policy question: do changes in exposure predict adjustment where flexibly interacted exposure levels do not?

We address two main identification threats. The first is macroeconomic and sectoral confounding. Hiring in AI-exposed occupations may have declined before ChatGPT because of monetary tightening, and within a static-exposure decile, high-dose occupations may cluster in sectors hit by the 2022–2024 technology hiring correction. Our identification therefore comes from cross-occupation dose variation within narrow event windows, not from aggregate time-series movements. We control for occupation-level interest-rate sensitivity, include industry-by-month fixed effects in the primary specification, and report the within-decile correlation between $\Delta\mathrm{DAX}$ and industry composition, showing primary estimates with and without the industry fixed effects so readers can see how much identifying variation they absorb. We exploit multiple events under different macroeconomic conditions and estimate three placebo designs: event studies at Federal Open Market Committee announcement dates; pseudo-release dates drawn between true events; and a placebo-dose test that keeps true event dates but assigns falsified doses (permuted capability mappings and backward-shuffled price histories), which isolates the economic content of DAX from generic event-window dynamics. All estimates are reported leave-one-event-out, so no result can depend on a single coincident shock. As a complementary check on the non-API adoption channel, we test whether dose responses differ by establishment size using the March CPS-ASEC, noting its annual frequency limits power for this comparison.

The second threat is task reorganization. Postings evidence attributes roughly 40 percent of measured exposure change to within-job task reconstruction rather than technology (Wang, Wei, and Wang 2026). We treat this as a first-order concern. Frozen task bundles remove task reorganization from DAX by construction, the live-vintage decomposition in Section 2.1 quantifies it, and we directly test whether $\Delta\mathrm{DAX}$ is orthogonal to the within-job reorganization component measured from postings data.

## 3. Data: Public Backbone and Requested OpenAI Signal

The labor-market design relies on data the team already has or can obtain publicly: O\*NET task statements and consequence-of-error descriptors; IPUMS-CPS monthly microdata; BLS Occupational Employment and Wage Statistics; the GDPval open gold subset; open-weight models for reconstructing historical capability vintages; and published API price histories. Neither the index nor the event studies require privileged data access. This feature supports both feasibility and credibility for the public data release.

We request from OpenAI the validation and mechanism layer that public sources cannot provide: monthly counts or shares of U.S. work-related ChatGPT messages aggregated to O\*NET task or Intermediate Work Activity cells, together with Asking/Doing, or augmentation/automation, classification shares at the same aggregation. Chatterji et al. (2025) demonstrate the relevant privacy-preserving pipeline. We request aggregates as shares of total U.S. work-related messages within each month, which nets out platform-wide adoption growth, interface changes, and subscription shifts. Where feasible, we request splits by plan or channel. The project requires aggregates only: no conversation content, no user-level records, minimum cell sizes and noise infusion at OpenAI's discretion, and hands-on analysis only by the named team under NDA. Privacy parameters — minimum cell sizes, the noise mechanism, and suppression rules — will be negotiated during month-one onboarding, and the design memo pre-registers how suppressed cells are handled and the minimum estimability condition the first stage requires, since suppression of rare task cells would otherwise select the test toward high-volume occupations.

We do not use usage data to define exposure. Platform-selection critiques show that reweighting usage-derived exposure measures to workforce shares attenuates estimates by 42–93 percent (Yin and Ogut 2026). We instead use usage data for first-stage behavioral validation. The tests ask whether tasks that cross the DAX threshold show relative jumps in usage shares, and whether composition shifts from Asking toward Doing after crossing. ChatGPT messages capture only one adoption channel; firms may automate tasks through APIs, enterprise deployments, or embedded integrations without changing consumer message volume. We therefore pre-register an asymmetric interpretation: a positive first stage strongly confirms that feasibility translates into behavior at dateable moments, while a null result localizes adoption to non-ChatGPT channels rather than refuting feasibility. Even under this narrow interpretation, the validation cannot be produced without OpenAI data.

## 4. Timeline and Milestones

**Months 1–2:** complete data-governance onboarding, including negotiation of privacy parameters, and produce a pre-registered design memo fixing event dates and windows, the four stacking parameters, the mapping hierarchy and full mapping-protocol documentation, the failure-cost grid and its flip-rate trigger, quantified validation and first-stage thresholds and the mapping tiebreaker rule, the primary outcome set, and ex ante power calculations.

**Months 3–4:** release DAX v1, including capability and price panels and the cost and deployment-adjustment variants. Interim readout 1 validates the index against static scores and published usage indices and decomposes exposure growth into capability-driven and price-driven threshold crossings.

**Months 5–8:** estimate first-stage tests with OpenAI aggregates and CPS event studies for the primary outcomes, led by the GPT-4o price event. Interim readout 2 includes the first working-paper draft.

**Months 9–12:** complete robustness analyses, including alternative mappings, the live-vintage decomposition, interest-rate sensitivity controls, reorganization orthogonality tests, and placebo-dose designs. Mobility-network spillovers are elevated to a pre-specified auxiliary result using occupational skill-distance measures (Gathmann and Schönberg 2010). Final outputs include a working paper, a public policy brief, and a documented public release of the DAX dataset through the agreed review path.

## 5. Team, Feasibility, and Resources

The Principal Investigator is [PI NAME], Professor of Economics at Boston University [one line: field and representative publications]. The Research Assistant is Qingyan Luo, a PhD candidate in economics at Boston University. The project constitutes the labor chapter of her dissertation, and she will conduct all hands-on data work under the PI's supervision and OpenAI's governance requirements. The team commits PI supervision, full-time RA effort, participation in Exchange readouts, and written output at every milestone.

The PI's existing grant covers the two largest inputs: compute for the capability panel and RA time for O\*NET mapping and CPS construction. The request to OpenAI is therefore for data access, not funding. Dependencies remain limited by design. The project requires approval of the aggregate usage signal by month two, but it does not require conversation data, user-level records, non-public model access, or new OpenAI engineering beyond the existing aggregation pipeline.

## 6. Expected Contributions

For research, the project delivers one of the first publicly available monthly, cost-thresholded dynamic AI exposure indices, together with quasi-experimental evidence on whether exposure changes predict labor-market adjustment. The design identifies price-driven changes separately from capability-driven changes, a margin that capability-only measures omit and that the GPT-4o event isolates almost exactly.

For OpenAI, the project provides a validated external complement to GDPval and internal usage measurement: an updatable indicator of which occupations have just become economically automatable, refreshed with each release and price change. For policy audiences, it provides a public early-warning dataset that distinguishes technical feasibility from adoption; the policy brief adds a minimal descriptive decomposition of measured adjustment into involuntary non-employment versus voluntary reallocation, using CPS unemployment-reason and search-duration variables, without welfare claims. The project treats the opening contradiction as an empirical object: most occupations may not yet have crossed the frontier, and recently crossed occupations may adjust first at the hiring margin. That interpretation will be reported as a result, not assumed as the paper's thesis.

## 7. Success Criteria and Pre-Specified Failure Conditions

Success requires three conditions, each filed numerically in the month-one design memo before any outcome data are analyzed. First, DAX must validate: a minimum rank correlation with the static-score ensemble, filed in advance, with threshold crossings visible at known release and price events. Second, the first stage must show relative usage jumps at crossings that meet a pre-filed minimum effect size. Third, event-study estimates must satisfy the pre-specified pre-trend standard: pre-event dose coefficients jointly indistinguishable from zero, with conclusions reported under Rambachan-Roth sensitivity at $\bar{M} = 0.5$, $1$, and $2$ and under the relative-magnitudes restriction; $\bar{M}=1$ is the headline standard. "Survive all three capability mappings" is likewise defined quantitatively in advance — consistent sign under all three and significance at the 10 percent level under at least two — with the tiebreaker rule filed in the memo.

Each pre-specified failure condition remains informative. If $\Delta\mathrm{DAX}$ adds no predictive content beyond the benchmark set, including the non-AI characteristics model, the result provides a disciplined defense of existing exposure measures. If usage shares do not respond at crossings, either unit economics has not become the binding adoption margin or adoption occurs through non-ChatGPT channels; either outcome directly informs the Exchange's questions about adoption frictions. If CPS power binds for the 22–25 age cells, we will report minimum detectable effects against payroll benchmarks; the index, capability-versus-price decomposition, and first-stage results will remain deliverables.

## 8. Scope

The project covers the United States from November 2021 through 2026. It studies occupation-level employment, hours, wages, and mobility; OpenAI-model capability and price events; and ChatGPT usage aggregates for validation. It excludes conversation content in any form, user- or firm-level records, non-U.S. outcomes except as robustness, welfare analysis beyond the descriptive decomposition in the policy brief, and claims about individual users. The intended stakeholders are OpenAI Economic Research, academic labor economics, and workforce-policy audiences.

## References

Acemoglu, D. 2024. "The Simple Macroeconomics of AI." *Economic Policy*.

Acemoglu, D., and P. Restrepo. 2022. "Tasks, Automation, and the Rise in U.S. Wage Inequality." *Econometrica*.

Brynjolfsson, E., B. Chandar, and R. Chen. 2025. "Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence." Working paper.

Brynjolfsson, E., D. Li, and L. Raymond. 2025. "Generative AI at Work." *Quarterly Journal of Economics*.

Callaway, B., A. Goodman-Bacon, and P. Sant'Anna. 2024. "Difference-in-Differences with a Continuous Treatment." Working paper.

Callaway, B., and P. Sant'Anna. 2021. "Difference-in-Differences with Multiple Time Periods." *Journal of Econometrics*.

Chatterji, A., T. Cunningham, D. Deming, Z. Hitzig, C. Ong, C. Shan, and K. Wadman. 2025. "How People Use ChatGPT." NBER Working Paper 34255.

Dominski, J., and Y. Lee. 2025. "Dynamic AI Exposure Measures." Working paper.

Eloundou, T., S. Manning, P. Mishkin, and D. Rock. 2024. "GPTs Are GPTs: Labor Market Impact Potential of LLMs." *Science*.

Felten, E., M. Raj, and R. Seamans. 2023. "How Will Language Modelers like ChatGPT Affect Occupations and Industries?" Working paper.

Frank, M., Y.-Y. Ahn, and E. Moro. 2025. "AI Exposure Predicts Unemployment Risk." *PNAS Nexus*.

Gathmann, C., and U. Schönberg. 2010. "How General Is Human Capital? A Task-Based Approach." *Journal of Labor Economics*.

Humlum, A., and E. Vestergaard. 2025. "Large Language Models, Small Labor Market Effects." NBER Working Paper 33777.

OpenAI. 2025. "GDPval: Evaluating AI Model Performance on Real-World Economically Valuable Tasks."

Rambachan, A., and J. Roth. 2023. "A More Credible Approach to Parallel Trends." *Review of Economic Studies*.

Svanberg, M., W. Li, M. Fleming, B. Goehring, and N. Thompson. 2024. "Beyond AI Exposure." Working paper.

Tolan, S., A. Pesole, F. Martínez-Plumed, E. Fernández-Macías, J. Hernández-Orallo, and E. Gómez. 2020. "Measuring the Occupational Impact of AI." *Journal of Artificial Intelligence Research*.

Wang, P., L. Wei, and S. Wang. 2026. "The Dynamics of AI Exposure in Job Postings." Working paper.

Webb, M. 2020. "The Impact of Artificial Intelligence on the Labor Market." Working paper.

Yin, R., and B. Ogut. 2026. "Platform Selection and Usage-Based AI Exposure Measures." Working paper.
