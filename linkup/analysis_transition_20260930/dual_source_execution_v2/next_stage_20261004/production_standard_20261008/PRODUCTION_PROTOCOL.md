# D43: staged, field-level candidate production

This is an execution amendment, not a new research plan. It supersedes the whole-record unanimity gate in D42 for **candidate production only**. Original data, T1–T6, probabilities, labels and receipts remain immutable. No validated causal or historical-text claims are added.

## Why the previous gate failed

The previous 20-document diagnostic mixed source/format errors, differences in extraction detail, and substantive concept errors. Held-out main-presence agreement was 15/16 for general experience, 14/16 for occupational/task experience, and 13/16 for industry/domain experience. These are AI-reader agreement counts, not accuracy. Full mention-list equality is not the estimand. A redundant state quotation should not invalidate unrelated fields; a role-specific year amount mislabeled general experience is a substantive error.

## Fixed measurement boundary

The current release measures three experience objects. Tool experience and technology/role classification retain their earlier candidate status; this release does not validate the original four-object/technology system. Do not silently treat excluded tool evidence as absent general, task, or industry requirements.

1. General work: explicitly unrestricted total work history. Relevant, job-related, role, task, tool or sector restrictions exclude a clause from this object.
2. Occupation/task: role, function or task-specific past experience, including alternative roles. Relevant/job-related experience belongs here unless the modifying context resolves to another object; unresolved context is unknown.
3. Industry/domain: business sector, application sector, market, customer population. IT, AI, algorithms, software or a technical subject alone do not establish industry experience. Explicit experience working in software companies/IT services as an industry can qualify; working in IT as a function alone cannot.

Knowledge is separate from prior experience. Preferences are separate from requirements. Education-or-experience branches are conditional, not unconditional. Years bind to their own clause and qualification branch. A ratio of work years per education year is not an absolute required duration. These decisions are conceptual rulings, not learned facts about treatment effects.

## Minimal production output and deterministic handling

Reuse the compact schema; use the revised prompt in this directory. Models read full original text. Preserve raw model output and source SHA. Code derives IDs, exact offsets, and estimand flags. Do not ask models to invent offsets or perform arithmetic. No quote normalization, fuzzy repair, inferred duration or silent semantic relabeling.

Each object has independent `candidate`, `unknown`, or `error` status. Candidate means mechanically supported under the frozen codebook, not externally validated. Unknown/error contributes null to the relevant derived outcome, never zero. `not_mentioned` is a model absence claim, retained as such and sampled for omission review. A valid mention can be retained as an evidence atom even when another mention leaves the object outcome unresolved.

A redundant exact `state_quote` on a positive finding may be preserved as auxiliary evidence with a logged formatting normalization. This does not remove or resolve contradictory semantic labels. Invalid duration is isolated from an otherwise sound binary experience indicator when the evidence and required/prior/unconditional labels are intact. Missing sources, wrong hashes or ambiguous row bindings quarantine the entire affected row; unrelated rows remain usable.

## One-way execution, not repeated pilots

1. Preserve the previous 20 as development/diagnostic material. Never relabel them a fresh holdout.
2. Start batch001 with 24 previously unreviewed exact texts, eight each from fixed A/B/C processing strata. This is processing order within the fixed 10,000, not a replacement probability sample and not an estimate of population prevalence.
3. Sol/medium is the primary reader for this contract based on observed task-specific failures of the cheaper reader. Luna performs deterministic bookkeeping. A second Sol/medium reviews a predeclared six-item random subset, blinded to primary labels, plus at most six flagged high-risk cases. Root adjudicates only material conflicts, at most twelve per batch. No full dual labeling.
4. An audited, clear systematic error (the same economic misclassification in two independent documents) pauses only the affected field/stratum. One confirmed error is corrected locally and its rule is checked across the current batch; it does not automatically halt all production. Source-binding corruption pauses the affected batch immediately. These are project operational rules, not literature-mandated accuracy thresholds.
5. Each field receives one corrective pass if necessary. Remaining uncertainty is queued as null with a reason. A second unresolved systematic problem downgrades that field; it does not trigger another prompt-development cycle or erase valid outputs of other fields.
6. After batch001, logical batches are 128 unique exact texts, with a fixed random audit of 16 per batch plus at most eight triggered cases. Each batch is checkpointed by text SHA, prompt/schema/code version, reader, raw output, outcome status and audit status. Resume only unfinished hashes. Exact duplicate texts reuse extraction; ad keys and weights remain separate. No fuzzy deduplication.

The size and audit caps above are cost-control and debugging choices, not a statistical certification of 95% accuracy. Always report the actual audit denominator and uncertainty. Do not increase the pilot until every reader agrees.

## Quality reports and scientific claims

Every release reports source/quote integrity; unresolved share; absence/positive proportions; audit-selected versus triggered cases; semantic corrections by error type and A/B/C; and main-indicator changes after adjudication. At scale also report occupation/cohort composition of unknowns. Audit coverage must include negatives to detect omissions. Report disagreement by meaningful binary/years fields, not just exact JSON equality.

For weighted prevalence, retain the original eligible denominator: lower candidate bound = weighted known positives / eligible weight; upper candidate bound adds unresolved weight. A/B difference bounds follow from the two arm intervals. These bound missing/abstained labels **conditional on correctness of decided labels**; they do not bound all semantic measurement error. The tiny staged processing batch cannot stand in for the full probability sample.

Candidate production may proceed before gold-standard accuracy is known. An economic conclusion is not released merely because production completed. AI-only review supports transparent candidate measurements and sensitivity analysis; it does not establish unbiased measurement, independent truth, or prediction-powered inference. Historical job-text validity remains unresolved because URL hashes can retain updated text. No Revelio individual analysis is represented as completed.

## Capacity boundary

Existing Codex agents can execute this bounded first batch. There is no configured paid API, and the prior local 8B CPU route was slow and substantively unsuccessful. Do not advertise an unattended full-corpus job unless a real execution process and resumable receipt exist. The 7,635-unique-text queue is ready infrastructure, not proof of 7,635 inferences. Remaining execution must use a measured compatible service/runtime; do not silently launch hundreds of card-hours or install another model as a substitute for the acceptance decision.

## Literature versus project choices

The accompanying evidence file records primary sources. Application-specific construct validation, explicit codebooks, error characterization and reproducibility are literature-supported. Our field-level queue, batch sizes, correction limits, audit caps and production-versus-claims release states are project decisions. Model consensus is not a universal validity standard. Hansen (2026) proposes a no-external-benchmark reconstruction test with backtranslation and separation prerequisites; this project does not claim to have implemented or passed that framework. Evidence entailment and negative/control cases are useful diagnostics, not an equivalent validation theorem.
