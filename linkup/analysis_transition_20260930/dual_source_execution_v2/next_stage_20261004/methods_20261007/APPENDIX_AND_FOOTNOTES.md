# Methods notes for the appendix and footnotes

These notes distinguish completed work from conditional text. They do not supersede execution receipts or certify the candidate semantic measures.

## Completed: sample and descriptive statistics

We retain a probability subsample of 4,000 GenAI-use candidate advertisements and 4,000 software-use candidates with no AI detected under the original screening rules. Both groups span the same 69 occupation–region–first-observation-cohort cells. Sampling weights account for the original and subsequent selection stages. An additional 2,000 observations represent residual advertisements **within the originally technology-screened frame**; they do not represent all other advertisements in these occupations. Cell-standardized proportions and inverse-probability-weighted statistics target different comparisons and are reported separately.

Numeric-year summaries use the existing rule-derived side tables and match the complete canonical locator, including the source file and source row. We retain the experience object, requirement strength, and numeric-bound interpretation. Clause-level means may give multiple contributions to advertisements containing several clauses. Lack of a numeric match is not coded as zero experience. The estimates are descriptive candidate-measure results, not independently validated semantic prevalence or causal effects.

## Footnote draft: text timing

LinkUp informed us that JOB_HASH is generated from a listing URL and may remain unchanged when the description changes. Our delivered descriptions do not establish when every observed phrase first became effective. We therefore use first-observation dates for cohort diagnostics, not as historical dates of the saved requirements. Similar postings appearing under new hashes in successive years do not by themselves establish that earlier saved text was never overwritten. Source: vendor correspondence supplied by the researcher; date not supplied.

## Footnote draft: model-assisted measurement

We distinguish model-assisted labeling from validation against independently established targets. Work on LLM-based economic measurement highlights the role of validation when using generated labels in downstream estimation ([Ludwig, Mullainathan, and Rambachan, NBER33344](https://www.nber.org/papers/w33344)). Strong performance in other tasks, including human-annotated benchmarks reported by [Asirvatham, Mokski, and Shleifer](https://shleifer.scholars.harvard.edu/sites/g/files/omnuum10626/files/2026-02/Paper%20PDF%20%28February%202026%29.pdf), is not validation of our own extraction task. Our AI-only checks must therefore be described as agreement and evidence-consistency checks, not human-grounded accuracy or measurement-error correction. No claim of such corrected inference is made.

## Conditional methods text — use only after actual completion

If the text-cache receipt verifies completion: “To reduce repeated inference, we cached outputs for exactly identical saved text while retaining every sampled advertisement and its original analysis weight. We did not merge merely similar templates. Duplicate texts were identified by hashes of the unmodified decoded text.”

If local inference becomes operational: record the model repository and immutable revision, weight-file SHA256, license, runtime commit, quantization, context limits, decoding configuration, exact prompt/schema hashes, timeouts, failures, and the actual processed-document denominator. Model execution alone is not validation. The proposed local runtime is an operational candidate; it is not the formal model selected by a successful measurement evaluation.

## Sources and rulings

- Ludwig, Jens; Sendhil Mullainathan; Ashesh Rambachan. *Large Language Models: An Applied Econometric Framework*. NBER Working Paper33344,2025; online record revisedDecember2025. [DOI](https://doi.org/10.3386/w33344).
- Asirvatham, Hemanth; Elliott Mokski; Andrei Shleifer. *GPT as a Measurement Tool*. NBER Working Paper34834,February2026. [DOI](https://doi.org/10.3386/w34834).
- Qwen official [model card](https://huggingface.co/Qwen/Qwen3-8B-GGUF) and llama.cpp official [build documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), accessed2026-10-07. These establish documented deployment options, not compatibility with every Hygon environment or task-specific model accuracy.
- [Decision ledger](DECISION_LEDGER.json) records which judgments are our design choices rather than findings established in these sources.

## Operational update: bounded local-runtime attempt

The compute probe (job 123914479) completed. The one main local-runtime attempt (job 123914627; 16 CPUs, 32 GB, one-hour limit) failed after seven seconds because the configured compute-node proxy was unreachable during the runtime bootstrap download. A secondary failure-receipt initialization defect was identified. No model weights were downloaded and no inference was run. This is an infrastructure failure, not evidence about model performance or measurement validity; no full-sample model result is claimed. The sanitized execution receipt and corrected script are retained separately.
