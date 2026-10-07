# Methods notes for the appendix and footnotes

These notes distinguish completed work from conditional text. They do not supersede execution receipts or certify the candidate semantic measures.

## Completed: sample and descriptive statistics

We retain a probability subsample of 4,000 GenAI-use candidate advertisements and 4,000 software-use candidates with no AI detected under the original screening rules. Both groups span the same 69 occupation–region–first-observation-cohort cells. Sampling weights account for the original and subsequent selection stages. An additional 2,000 observations represent residual advertisements **within the originally technology-screened frame**; they do not represent all other advertisements in these occupations. Cell-standardized proportions and inverse-probability-weighted statistics target different comparisons and are reported separately.

Numeric-year summaries use the existing rule-derived side tables and match the complete canonical locator, including the source file and source row. We retain the experience object, requirement strength, and numeric-bound interpretation. Clause-level means may give multiple contributions to advertisements containing several clauses. Lack of a numeric match is not coded as zero experience. The estimates are descriptive candidate-measure results, not independently validated semantic prevalence or causal effects.

## Footnote draft: text timing

LinkUp informed us that JOB_HASH is generated from a listing URL and may remain unchanged when the description changes. Our delivered descriptions do not establish when every observed phrase first became effective. We therefore use first-observation dates for cohort diagnostics, not as historical dates of the saved requirements. Similar postings appearing under new hashes in successive years do not by themselves establish that earlier saved text was never overwritten. Source: vendor correspondence supplied by the researcher; date not supplied.

## Footnote draft: model-assisted measurement

We distinguish model-assisted labeling from validation against independently established targets. Work on LLM-based economic measurement highlights the role of validation when using generated labels in downstream estimation ([Ludwig, Mullainathan, and Rambachan, NBER33344](https://www.nber.org/papers/w33344)). Strong performance in other tasks, including human-annotated benchmarks reported by [Asirvatham, Mokski, and Shleifer](https://shleifer.scholars.harvard.edu/sites/g/files/omnuum10626/files/2026-02/Paper%20PDF%20%28February%202026%29.pdf), is not validation of our own extraction task. Our AI-only checks must therefore be described as agreement and evidence-consistency checks, not human-grounded accuracy or measurement-error correction. No claim of such corrected inference is made.

## Exact-text preparation and model execution

Completed text preparation: all 10,000 sampled source texts were retrieved and checked against the frozen canonical keys. Exact-text hashing identified 7,635 distinct texts, leaving 2,365 repeated rows beyond the unique texts. All 10,000 advertisements and their original sampling and analysis weights remain in the merged dataset; the separate cache can avoid repeated inference without merging analysis units. No fuzzy matching or whitespace normalization was applied. One embedded NUL required a binary-capable CSV reader; the original text was preserved. The three private Parquet artifacts were also transferred to Wuzhen and checked remotely against their SHA-256 hashes. See the full-cache, independent-QA, and remote-handoff receipts. This completes text preparation, not model extraction.

A pinned Qwen3-8B Q4_K_M model and llama.cpp CPU runtime were subsequently staged and executed. Of four preselected, previously adjudicated difficult advertisements, two were attempted: one completed and one remained partial when the run was stopped; two were not started. The first completed prediction assigned task-specific tenure to general experience, confused domain knowledge with prior work experience, and missed explicit generative-AI-use evidence. The configured route was therefore not accepted for unattended production. The stop was a failure-triggered engineering and measurement decision, not an estimate of population accuracy. The completed case took 450.35 seconds. Full-sample extraction was not started. Completed and partial outputs are stored separately, with model/runtime hashes and actual allocation totals in the public completion receipt.

Postprocessing is limited to removing a known runtime end marker and recomputing offsets for unchanged, uniquely located exact quotations. An exploratory procedure that deleted conflicting fields was rejected; its apparent structural pass does not count as acceptance. Even offset-only repair left the completed real prediction invalid. The four pilot inputs contained no NUL; the argument-based prototype cannot carry embedded NUL and is not approved as a full-corpus transport. This input limitation does not alter the preserved exact-text corpus.

## Sources and rulings

- Ludwig, Jens; Sendhil Mullainathan; Ashesh Rambachan. *Large Language Models: An Applied Econometric Framework*. NBER Working Paper33344,2025; online record revisedDecember2025. [DOI](https://doi.org/10.3386/w33344).
- Asirvatham, Hemanth; Elliott Mokski; Andrei Shleifer. *GPT as a Measurement Tool*. NBER Working Paper34834,February2026. [DOI](https://doi.org/10.3386/w34834).
- Qwen official [model card](https://huggingface.co/Qwen/Qwen3-8B-GGUF) and llama.cpp official [build documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), accessed2026-10-07. These establish documented deployment options, not compatibility with every Hygon environment or task-specific model accuracy.
- [Decision ledger](DECISION_LEDGER.json) records which judgments are our design choices rather than findings established in these sources.

## Operational update: bounded local-runtime attempt

The compute probe (job 123914479) completed. The one main local-runtime attempt (job 123914627; 16 CPUs, 32 GB, one-hour limit) failed after seven seconds because the configured compute-node proxy was unreachable during the runtime bootstrap download. A secondary failure-receipt initialization defect was identified. No model weights were downloaded and no inference was run. This is an infrastructure failure, not evidence about model performance or measurement validity; no full-sample model result is claimed. The sanitized execution receipt and corrected script are retained separately.

## Completed compact diagnostic and interpretation ruling

A subsequent authorized round simplified model output to concept labels and quotations, leaving source identifiers, hashes and offsets to code. The diagnostic consisted of four earlier difficult examples and sixteen previously unused texts from the existing A/B candidate frame, eight per group. Two blinded AI readers each read all twenty once. Agreement on all three required, unconditional prior-experience presence indicators was12/16 in the unused subset (general15/16, task14/16, domain13/16). These are diagnostic agreement counts, not estimates of accuracy or population prevalence. Full mention-set comparisons were sensitive to one reader's shorter coverage and are not interpreted as independent error rates.

Original semantic judgments were retained when later schema-driven edits altered duration kinds, removed conflicting evidence, or nulled amounts. A single targeted root review covered the four earlier examples, four unused cases with main-indicator disagreement, and two unused cases with agreement. The review clarified that generic technical topics such as AI or IT do not alone establish industry or customer/business-domain history. This is an interpretation ruling narrowing ambiguous subject-area wording for the intended eventual linkage to worker histories; it is not an executed, validated reclassification of the full corpus. The original labels and frozen contract remain available. No new cluster jobs, card-hours, paid API calls or full-corpus inference were incurred in this round. Formal production remains unaccepted for this configuration.
