# Recruitment Demand and Job Requirements Around Generative AI Diffusion

## An interim descriptive analysis using LinkUp

**Working manuscript, 16 November 2026.** This draft assembles completed results. It is not a causal AI-effects paper, a claim that the full delivery has been semantically processed, or a finished manuscript. Proposed analyses are explicitly separated from estimates already produced. No new model judgments were generated for this draft.

## Abstract

This study examines two distinct dimensions of online recruitment: the volume and composition of advertisements, and the experience and responsibilities described within them. We combine existing LinkUp Records aggregates with a separately defined, previously reviewed text reference sample. In the Records series, newly first-observed US advertisements fall from 25.33 million in December 2021–November 2022 to 22.55 million in December 2022–November 2023, a decline of 10.97%. Mean month-end active advertisements decline by 13.82% under the specification retaining missing deletion dates as open. In a separate technology-screened reference frame, advertisements mentioning generative-AI use have higher occupation/task and tool-specific experience prevalence within the reference-known domains than the software comparison group. However, uncertainty about group membership and outcomes prevents identification of the direction of these contrasts for the full candidate frame. Explicit graduate or no-experience eligibility can coexist with current job responsibilities: the existing occupation-standardized estimate is 51.08% in its restricted reference-known domain. These results establish descriptive patterns, not an effect of AI on hiring, entry-level opportunities, or historical job requirements.

## 1. Introduction

Changes in recruitment may occur through both the number of opportunities advertised and the requirements attached to those opportunities. These are different empirical margins. A decline in advertisements does not establish that employers demand more experience, while a text mentioning junior applicants alongside substantive responsibilities does not establish that junior opportunities have become less accessible over time.

Our research separates these margins. The first module measures first-observed advertisement flows, observed active stocks, and occupational composition. The second uses evidence-linked text measurements to distinguish general work, occupation/task, industry/domain, and tool-specific experience, as well as explicit entry eligibility and responsibilities of the advertised position. Maintaining these distinctions avoids treating all references to experience or junior workers as equivalent requirements.

The completed evidence currently supports a descriptive contribution. We do not treat the late-2022 comparison date as an exogenous assignment of AI adoption. Nor do we treat an advertisement's AI wording as a verified measure of its employer's technology adoption. A causal design and a connection to worker-level outcomes remain subsequent research tasks. The literature review and externally sourced institutional chronology are not yet incorporated; this draft does not substitute unverified citations for them.

## 2. Data and sample boundaries

### 2.1 Records-based recruitment panel

The macro module reuses completed, source-verified LinkUp Records aggregates, rather than reprocessing advertisement descriptions. The available all-history US Records count is 253,210,047; 199,644,730 first-observed records fall from 2016 onward. The assembled reporting series contains 129 monthly and 11 annual observations for 2016–2026. The delivery ends on 6 September 2026, so 2026 is incomplete. January–August 2026 contains 15,029,705 first-observed advertisements; the available-year total of 15,496,940 additionally includes the partial September boundary. Neither is compared with a complete prior year as if the exposure windows were equal.

An observation is an advertisement record, not a count of vacancies, hires, or workers. We use `CREATED` as a **first-observed posting-time proxy**. Updates and later checks do not create a new first-observed advertisement in this definition. The proxy does not establish the creation date of the currently retained text. All temporal comparisons therefore remain conditional on this measurement convention.

### 2.2 Existing text-processing assets

The completed canonical US text-processing base contains 204,774,035 advertisements in 2,464 shards. A later 69-shard additive field wave covers 5,804,936 advertisements, with its retained metadata joins already completed. These are overlapping assets and are not added together to obtain a larger sample size. The base's engineering completion is not certification of every fine semantic field.

The Records universe, canonical text universe, and the user's approximately 500-million-row delivery are not interchangeable denominators. The full-delivery reconciliation remains open. In particular, the difference between two such counts is not an established queue of unique documents awaiting a model call.

### 2.3 Bounded semantic reference frame

The existing fixed10k reference comprises 10,000 advertisements and 7,617 normalized complete-input contexts. It retains the original unknowns, exclusions, and field-specific acceptance masks. Fourteen isolated contexts correspond to 16 advertisements and are not deleted from the sample denominator. Reference judgments were produced by models and reviewed under their recorded procedures; they are not independent human ground truth.

The primary micro comparisons reproduced below target the original technology-screened candidate frame of 1,157,573 advertisements across 69 sampling cells. They retain the original inclusion probabilities and design weights, with SOC major groups 11, 13, 15, and 17 each assigned a weight of 0.25. They are not nationwide estimates. Formal800 overlaps the fixed10k reference and is not an independent replication. Previously completed supplemental relation judgments likewise are not automatically assumed to have entered the estimates reproduced here.

## 3. Measurement and accounting

### 3.1 Flows, stocks, and exits

New advertisement flow is the count first observed in a calendar month. Month-end active stock uses the existing convention that an advertisement has been created by month-end and has a deletion date after that point. Missing deletion dates are treated in two separate specifications: retained as open, or excluded. Direct exits require a compatible deletion-date aggregate. A residual derived from flows and changes in stocks is retained as an accounting diagnostic, not labeled as directly observed exits.

Occupational composition uses the classification attached to the delivered snapshot. It is not a verified reconstruction of each advertisement's historical occupational code. Missing, unmapped, and residual categories remain explicit. Changes in coverage, employer composition, geographic posting practices, and later occupational recoding are potential competing explanations.

### 3.2 Experience, eligibility, and responsibility

Text measures retain the object to which an experience requirement applies, literal duration, required/preferred strength where defined, and qualification alternatives. Multiple conditional clauses are not compressed into an unconditional minimum number of years. A responsibility to mentor junior staff does not by itself identify the advertised job as entry-level.

The entry-eligibility analysis below concerns explicit graduate or no-experience eligibility, including its original conditional and unconditional forms. It is not a count of all junior jobs. Responsibility measures concern the advertised position's current independent judgment, client ownership, personnel supervision, and training/mentoring. The existing responsibility schema does not encode required/preferred strength; responsibility co-occurrence is therefore not described as a mandatory entry requirement.

### 3.3 Reuse and unknowns

Existing accepted fields are retained through complete-input identity, measurement version, and source acceptance masks. Unknown is not a negative label, and a stored but unverified output is not accepted merely because its JSON passes validation. Protected inputs and outputs remain excluded from re-inference. Exact-context reuse can propagate a compatible existing judgment to additional recorded advertisement mappings without counting a new judgment.

The updated workflow does not require the user to conduct human review. Mechanical evidence checks and independent model comparisons remain identifiable as such; model agreement is not presented as measured population accuracy. New production fields will enter analysis only with a documented, field-specific acceptance decision.

## 4. Completed descriptive results

### 4.1 Advertisement volume around late 2022

**Table 1. Equal-length descriptive windows in the US Records series**

| Outcome | Dec 2021–Nov 2022 | Dec 2022–Nov 2023 | Change |
|---|---:|---:|---:|
| First-observed advertisements | 25,328,196 | 22,549,332 | −10.97% |
| Mean month-end active stock, missing deletion dates retained as open | 4,180,547.4 | 3,602,666.9 | −13.82% |
| Mean month-end active stock, missing deletion dates excluded | 4,140,658.4 | 3,510,360.6 | Sensitivity levels reported separately |

*Source:* Existing Azure macro run004, `PREPOST_CHANGE_PUBLIC.json`, verified in the original delivery. These are descriptive differences, not fitted structural-break tests, and no causal standard errors are asserted.

The first-observed flow declines between the two equal-length windows. The active-stock comparison also declines under the open-ended missing-deletion convention; the alternative specification is reported to expose sensitivity to incomplete exit information. Neither measure identifies a change in employment or successful hiring.

In the existing snapshot-based occupational comparison between calendar years 2022 and 2023, the shares of major groups 15, 11, and 13 decline by 2.293, 1.538, and 1.413 percentage points, respectively. Groups 35, 53, and 29 increase by 0.926, 0.834, and 0.779 points. These are composition shifts in the available advertisements, not estimated treatment effects on occupations.

### 4.2 Experience composition in the bounded reference frame

**Table 2. GenAI-use wording minus software-comparison wording, percentage points**

| Experience object | Reference-known contrast | Approximate 95% design interval | Full-target unknown envelope |
|---|---:|---:|---:|
| General work | −0.38 | [−4.98, 4.22] | [−16.71, 84.43] |
| Occupation/task | 9.96 | [5.90, 14.03] | [−71.17, 21.60] |
| Industry/domain | −1.70 | [−11.49, 8.09] | [−50.47, 45.82] |
| Tool-specific | 23.42 | [15.35, 31.50] | [−54.70, 38.57] |

*Source:* Completed design-correction `CORE_Q1`, as reconciled in the 26 October research decision. The GenAI group may also mention traditional software; the comparison uses the original software-without-active-AI definition. Four occupational groups receive equal weights. Fields have different reference-known domains. Original estimates are reproduced, not recomputed with new labels.

Occupation/task and tool-specific contrasts are positive within their reference-known domains. General-work and industry/domain contrasts do not have a clear direction under the original design intervals. This difference in patterns is not itself a test that the experience categories have different effects, and it does not establish substitution between tools and general experience.

All four full-target unknown envelopes cross zero. Consequently, the direction of these contrasts remains unidentified for the full technology-screened candidate frame under the recorded uncertainty treatment. The envelopes are neither confidence intervals nor demonstrated sharp bounds. Design intervals reflect the original sampling assumptions and do not incorporate common errors in model-produced reference labels.

### 4.3 Entry eligibility and current responsibilities

In the original reference-known pooled domain, 186 advertisements have explicit graduate or no-experience eligibility, and 110 of them contain at least one measured current responsibility. The existing four-major-standardized, design-weighted estimate is **51.08%**, with an approximate 95% design interval of **34.22–67.95%**. It is not 110 divided by 186. The corresponding full-target unknown envelope is **39.68–63.37%** and must not be interpreted as another confidence interval.

This finding establishes that explicit entry eligibility and substantive current responsibilities can coexist within the defined reference domain. It does not imply that all entry-level jobs have these characteristics, that responsibilities are mandatory admission criteria, or that requirements have risen over time. The original standardized GenAI-versus-software responsibility comparison is unavailable because required occupational support is missing; we do not drop unsupported groups to manufacture that estimate.

## 5. Analyses not yet estimated

The next deliverables are an expanded, provenance-bound measurement panel and a national explicit-entry-eligibility series with a defensible same-frame denominator. Existing sequential production queues and the technology-screened fixed10k sample are not substitutes for that denominator. Missing direct-exit aggregates and classification membership checks also remain to be completed.

For temporal micro analysis, we will use the agreed `CREATED` proxy rather than make reconstruction of all historical text snapshots a prerequisite. The corresponding limitation remains explicit: the retained text may have changed since first observation. Temporal estimates will require support and sensitivity checks and will not be labeled causal solely because they compare dates before and after late 2022.

A later worker-side module may connect employer, occupation, geography, and time to Revelio data, subject to verified coverage and entity mappings. No Revelio data have been analyzed in this draft, and no worker mobility or entry estimates are claimed. An AI causal design will additionally need a justified exposure measure and comparison strategy; those are not supplied by the present descriptive tables.

## 6. Interim conclusion

The completed evidence separates a decline in observed advertisement volume from the content of recruitment requirements. The bounded text results show heterogeneous experience composition and the coexistence of explicit entry eligibility with current responsibilities, while preserving substantial uncertainty about broader populations. The next step is to connect and extend existing assets—not to re-extract every advertisement or treat a small model benchmark as a new population result.

## Provenance and remaining manuscript work

The macro tables reuse the completed Azure Records run004. Micro estimates reuse the completed design-correction release and its subsequent research reconciliation. Historical weights, masks, schemas, and estimates remain unchanged. The evidence register accompanying this draft records source SHA digests and the scope of each claim. Literature integration, a defensible expanded-label denominator, the new temporal micro estimates, a causal identification design, and the later Revelio module remain unfinished; this manuscript is not a declaration that those tasks are complete.
