# Repository-bounded census of candidate exposure architectures

Status: referee-round-2 treatment-side audit. No raw labor outcome was accessed
and no outcome model was run; only existing source, mapping, admission, and
literature records determine candidate status.

## Scope and status vocabulary

This is a census of what the **verified YAX repository record can currently
classify**, not a claim to enumerate every published AI-exposure measure. The
dated novelty audit itself says the literature search is not timeless
(`yax/literature/NOVELTY_AUDIT_2026-08-28.md:85-97`). A global count would
require a new, updated source search and primary-source review.

The historical external-admission rule mixes four logically distinct screens:
source/integrity, construct scope, mapping/completeness, and representation/
estimation feasibility (`yax/revision/referee_20260905/EXTERNAL_ARCHITECTURE_ADMISSION_RULE.md:7-26`). A "PASS" below therefore means only that a candidate passed that
declared operational rule; it is not a declaration of construct validity or
truth. The distinct-quintile-cut condition is representation-dependent and
should be reported separately in the revision rather than defended as a
construct-validity criterion.

- **INCLUDED--CORE:** selected before the external rule; do not retroactively
  call this a rule pass.
- **PASS--EXTERNAL:** evaluated and passed all six historical operational
  conditions before its YAX outcome model was fit.
- **FAIL--SCOPE:** evaluated enough to establish failure of the AI-construct
  scope condition.
- **PENDING--INSTANTIATION:** a primary source was recorded in the dated
  literature audit, but no hashed score file, complete mapping, support audit,
  or candidate-specific admission row exists in this repository.
- **UNVERIFIED--LOCAL:** named as relevant, but the repository record does not
  contain a sufficient primary-source-and-data audit to characterize it.
- **CONTROL/COMPARATOR:** instantiated, but deliberately not an AI-exposure
  candidate for the architecture comparison.

## A. Evaluated or selected occupation-score implementations

| Candidate implementation | Conceptual family | Status | What the verified record establishes | Criterion not established / limitation | Exact repository evidence |
|---|---|---|---|---|---|
| AIOE administrative/equal | Ability/application | **INCLUDED--CORE** | Same ten-application/52-ability system; published occupation score aggregated across mapped sources | Not independently tested under the later external rule | `yax/manuscript/v5_1/YAX_V51_ARCHITECTURE_MATRIX.md:5-9`; source workbook hash in `yax/measurement/CENSUS2018_EXPOSURE_VARIANTS.csv.lineage.json` |
| AIOE ability/direct | Ability/application | **INCLUDED--CORE** | Reconstructs the same stated AIOE construct on target O\*NET abilities | A same-construct implementation, not an independent architecture validation | Same evidence as above |
| AIOE source-employment weighted | Ability/application | **INCLUDED--CORE** | Uses source-vintage OEWS employment to aggregate mapped SOC-2010 parents | A same-construct aggregation implementation, not an independent construct | Same evidence as above |
| Eloundou alpha, \(D\) | Task/LLM time saving | **INCLUDED--CORE** | Direct LLM task-acceleration share | Technology scope differs from beta/broad because complementary software is excluded | `yax/manuscript/v5_1/YAX_V51_ARCHITECTURE_MATRIX.md:10-12`; source file hash in `yax/measurement/CENSUS2018_EXPOSURE_VARIANTS.csv.lineage.json` |
| Eloundou beta, \(D+S/2\) | Task/LLM time saving | **INCLUDED--CORE** | Direct plus half-weighted software-complemented task share; frozen primary implementation | Same two primitives as alpha/broad; not an independent validation | Same evidence as above; exact family identity at `paper/main/sections/02_literature.tex:7-13` |
| Eloundou broad, \(D+S\) | Task/LLM time saving | **INCLUDED--CORE** | Direct or software-complemented task share; source column is `gamma`, published notation is zeta | Same two primitives; naming alias must not be mistaken for a new construct | `yax/manuscript/v5_1/YAX_V51_ARCHITECTURE_MATRIX.md:10-12`; notation rule in `yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json` |
| Webb AI patent--task overlap | Patent/text overlap | **PASS--EXTERNAL** | Public hashed source; non-title mapping; full-component construction; 448 occupations, 95.73% preperiod employment coverage, distinct cuts | Passed an operational admission screen; does not establish it measures the same construct as LLM task acceleration | `yax/revision/referee_20260905/results/external/EXTERNAL_ARCHITECTURE_ADMISSION.csv` row `Webb_AI_patent_task`; source hash `c2b3dc...6406` in `.../EXTERNAL_ARCHITECTURE_RECEIPT.json` |
| Reversed OECD AI capability gap | Nine-domain capability-to-demand gap | **PASS--EXTERNAL** | Public hashed source; SOC-2018 route; full components; 448 occupations, 94.30% preperiod employment coverage, distinct cuts | Forward-looking horizon and broad cognitive/social/physical scope differ from contemporary LLM tasks; sign reversal requires substantive explanation | `yax/revision/referee_20260905/results/external/EXTERNAL_ARCHITECTURE_ADMISSION.csv` row `OECD_AI_capability_gap_reversed`; source hash `11643c...dcd` in `.../EXTERNAL_ARCHITECTURE_RECEIPT.json`; construct source summarized at `yax/literature/NOVELTY_AUDIT_2026-08-28.md:55-60` |
| Frey--Osborne automation probability | Broad automation risk | **FAIL--SCOPE** | A hashed source and harmonized occupation variable exist | Fails historical admission item 2: undifferentiated automation probability is not relabeled as occupational AI exposure | `yax/revision/referee_20260905/EXTERNAL_ARCHITECTURE_ADMISSION_RULE.md:28-34`; construction receipt `yax/measurement/COMPUTERIZATION_MEASURES_RECEIPT.json` |

### Count that can be defended now

The repository contains **six selected score implementations from two core
families**, **two externally admitted implementations from two additional
families**, and **one explicit scope failure**. The six are strongly dependent:
on the exact 444-occupation common support, the first two weighted principal
components explain 96.11% of their variance
(`yax/revision/referee_round2_20260905/architecture/ARCHITECTURE_STRUCTURE_FINDINGS.md:1-9`). These counts are not a count of all published measures.

## Implemented-architecture construct matrix

Publication vintage and occupational-information vintage are kept separate.
"YAX interpretation" is the comparison the score can motivate in this
application; it is not attributed to the source author.

| Implementation | Technology scope | Occupational primitive / label generation | Publication and occupational-information vintage | Intended horizon in verified YAX record | Mapping route | YAX interpretation |
|---|---|---|---|---|---|---|
| AIOE administrative/equal | Progress in ten AI applications | 52 O\*NET abilities; application--ability crowd judgments; published occupation AIOE | Felten 2018/2021 publications; native SOC 2010 | No explicit forecast horizon is recorded in the architecture ledger | SOC 2010 $\rightarrow$ official SOC 2018 bridge $\rightarrow$ official Census 2018 bridge; equal aggregation, full components | Whether young-relative stocks evolve differently across occupations whose required abilities are more exposed to the ten applications |
| AIOE ability/direct | Same scope | Same application--ability links combined directly with target O\*NET ability importance/prevalence | Felten 2018/2021; target O\*NET 25.1 recorded | Not recorded | Direct target reconstruction, then official Census 2018 bridge; full components | Same maintained construct, alternative reconstruction |
| AIOE source-employment weighted | Same scope | Published SOC-2010 AIOE; May 2018 OEWS weights aggregate source parents | Felten 2018/2021; May 2018 OEWS aggregation basis | Not recorded | Official SOC 2010 $\rightarrow$ 2018 route with source-employment aggregation, then Census 2018; full components | Same maintained construct, alternative source aggregation |
| Eloundou alpha | LLM alone | O\*NET tasks labeled E0/E1/E2 by GPT-4; alpha is E1 share | Eloundou 2024 publication / arXiv v5 checked; O\*NET-SOC 2019 / SOC 2018 | Potential 50% task-time reduction under the source rubric; no adoption forecast horizon is encoded | Six-digit SOC collapse $\rightarrow$ official Census 2018 bridge; full components | Whether the young-relative pattern is ordered by direct LLM task acceleration |
| Eloundou beta | LLM plus limited software complementarity | Same labels; E1 plus half of E2 | Same | Same rubric, with partial weight on complementary-software tasks | Same | Whether the pattern is ordered by the frozen intermediate technology boundary |
| Eloundou broad | LLM plus complementary software | Same labels; E1 plus E2 | Same | Same rubric, including all software-complemented tasks | Same | Whether the pattern is ordered by the broad endpoint of the two-primitive family |
| Webb AI | Patents classified as AI | Patent--task text overlap | Webb 2020; repeated source rows reduce to 737 SOC-2010 codes in the local audit | No explicit forecast horizon is recorded in the admission ledger | SOC 2010 $\rightarrow$ BLS SOC 2018 $\rightarrow$ Census 2018; source-employment aggregation; full components | Whether patent-language susceptibility orders the same fixed downstream comparison |
| Reversed OECD gap | Nine cognitive, social, and physical AI-capability domains relative to occupational demands | Institutional capability indicators mapped to occupational requirements | OECD 2026; 763 source SOC-2018 codes in the local audit | The local architecture/admission ledgers do not record the source's horizon; verify from the primary document before publication | Equal detail mean within six-digit SOC 2018 $\rightarrow$ Census 2018; OEWS/equal component aggregation; full components | Whether a broad capability-to-demand ordering yields the same fixed downstream comparison; not an LLM reliability check |

Evidence for the six core rows is
`yax/manuscript/v5_1/YAX_V51_ARCHITECTURE_MATRIX.md:5-14` and
`yax/literature/NOVELTY_AUDIT_2026-08-28.md:38-44`. Evidence for the external
routes and native row counts is
`yax/revision/referee_20260905/run_external_architectures.py:69-161` and the two
rows of `.../results/external/EXTERNAL_ARCHITECTURE_ADMISSION.csv`.

## B. Verified published candidates not instantiated in YAX

The following rows have a primary-source characterization in the dated novelty
audit, but no candidate-specific hashed source-score file, SOC-to-Census route,
full-component audit, support calculation, or admission record in YAX. Their
status is therefore pending, not failed.

| Candidate/family | Status | What is verified in the repo | What remains unavailable |
|---|---|---|---|
| Yin--Vu--Persico frontier-model replications of a fixed LLM rubric | **PENDING--INSTANTIATION** | The opened source is recorded as a within-rubric annotator-instability study | Candidate score release(s), version hashes, mapping, support, and admission audit (`yax/literature/NOVELTY_AUDIT_2026-08-28.md:42-46`) |
| Yin--Ogut platform-usage construction | **PENDING--INSTANTIATION** | The opened source is recorded as varying platform-user inputs within an observed-use family | A ruling on potential exposure versus realized use under item 2, plus source data, mapping, and support (`.../NOVELTY_AUDIT_2026-08-28.md:45-46`) |
| Budget Lab harmonized metrics / PCA representation | **PENDING--INSTANTIATION** | Seven harmonized metrics and a PCA summary are recorded | Candidate identities and versioned score files must be separated; PCA is a representation/composite, not automatically a new construct (`.../NOVELTY_AUDIT_2026-08-28.md:48-51`) |
| BCC Anthropic usage and other alternatives | **PENDING--INSTANTIATION** | The latest BCC version is recorded as using Anthropic usage and five alternatives | The local audit does not enumerate and instantiate each score; exact ADP mapping is proprietary (`yax/literature/PUBLISHED_MEASUREMENT_AUDIT_2026-08-28.md:7-10`) |
| Mouchel--Bouquet--Sheffi evidence-grounded retrieval | **PENDING--INSTANTIATION** | A distinct O\*NET occupation-task, evidence-grounded family is recorded | Versioned score file, mapping, completeness, coverage, cuts, and matched-support audit (`yax/literature/NOVELTY_AUDIT_2026-08-28.md:55-60`) |
| Tomei--Klein Teeselink RL-feasibility | **PENDING--INSTANTIATION** | A reinforcement-learning feasibility family is recorded | Same six operational checks (`.../NOVELTY_AUDIT_2026-08-28.md:58-60`) |
| Fenoaltea et al. startup-targeted measure | **PENDING--INSTANTIATION** | A market-targeted startup-application family is recorded | Same six operational checks and an explicit decision about technical exposure versus market targeting (`.../NOVELTY_AUDIT_2026-08-28.md:58-60`) |
| Steele--Cruz query-based measure | **PENDING--INSTANTIATION** | A query-based score and multi-projection comparison are recorded | Score artifact, mapping, support, and whether the query measure is one candidate or part of a composite (`.../NOVELTY_AUDIT_2026-08-28.md:61-62`) |
| Eisfeldt and Engberg measures used by EIG/Pulito | **PENDING--INSTANTIATION** | Their use by those studies is recorded | Their primary constructs, local versioned score files, and candidate-specific YAX mapping/admission are not in the audited artifacts (`yax/literature/PUBLISHED_MEASUREMENT_AUDIT_2026-08-28.md:9-13`) |

## C. Referee-named candidates not verified in the local candidate record

The new referee report names Acemoglu--Autor--Hazell--Restrepo, Babina--Fedyk--
He--Hodson, and Hampole--Papanikolaou--Schmidt--Seegmiller as possible
different-primitive additions. The current repository contains bibliographic
metadata for Hampole et al. but no verified occupational score artifact or
candidate admission audit; the other two are not characterized in the dated
YAX measurement/novelty ledgers. They are therefore **UNVERIFIED--LOCAL**.
Nothing in this census treats them as passed, failed, occupationally mappable,
or comparable in unit of observation. A new primary-source/data audit is
required before one can be added.

## D. Instantiated controls and comparators that are not AI architectures

| Variable | Status | Reason |
|---|---|---|
| Webb software-patent exposure | **CONTROL/COMPARATOR** | Software-patent task overlap; retained as a prior-computerization conditioning variable, not Webb AI |
| O\*NET Interacting With Computers--Importance | **CONTROL/COMPARATOR** | Computer-use importance |
| O\*NET Interacting With Computers--Level | **CONTROL/COMPARATOR** | Complexity/level of computer interaction |
| Autor--Dorn routine-task intensity | **CONTROL/COMPARATOR** | Routine cognitive/manual task balance |
| Dingel--Neiman telework feasibility | **CONTROL/COMPARATOR** | Location feasibility, not computerization and not AI exposure |

The first four roles and source hashes are documented in
`yax/measurement/COMPUTERIZATION_MEASURES_RECEIPT.json`; telework appears in the
vintage-aware lookup design at
`yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json`.

## Recommended revision to the admission presentation

Replace one omnibus "admitted/not admitted" label with four reported columns:

1. **source integrity and reproducibility** (public/versioned/hashed);
2. **construct classification** (potential AI susceptibility, observed use,
   computerization, automation, or another boundary);
3. **mapping and support feasibility** (non-title route, component
   completeness, employment coverage); and
4. **representation/design feasibility** (distinct bins if bins are required,
   plus the exact matched downstream comparison).

This preserves the historical rule and its outcomes while preventing a
representation failure from masquerading as construct invalidity.
