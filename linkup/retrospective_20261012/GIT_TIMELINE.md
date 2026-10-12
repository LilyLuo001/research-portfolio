# LinkUp Git timeline and decision audit

Audit date: 2026-10-12. Scope: read-only review of `reproducibility_git` history and adjacent research decision files from 2026-09-24 through 2026-10-12. No remote state was changed.

Current repository state:

- HEAD: `356564eb61e4c01bd81647641c8fab4b0b2dc719` (`main`)
- `origin/main`: same commit; working tree was clean at audit time.
- Remote: `https://github.com/LilyLuo001/research-portfolio.git`

## Chronology

- Sep 24–27: initial cleaning/research contract and methods snapshot. The durable sources are [RESEARCH_AND_CLEANING_PLAN.md](/Users/lilyluo/Documents/LinkUp_Research_20260924/RESEARCH_AND_CLEANING_PLAN.md), [STAGE_B_RESEARCH_ALIGNED_PLAN.md](/Users/lilyluo/Documents/LinkUp_Research_20260924/STAGE_B_RESEARCH_ALIGNED_PLAN.md), and the Git commit `f5e7ae5` (`Add LinkUp cleaning methods snapshot`). Early work centered on Stage C enrichment, validation, and model diagnostics.
- Sep 28–30: regional transfer/recovery and transition planning. Key documents are [analysis_transition_20260930/README.md](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/README.md), [analysis_transition_20260930/dual_source_execution_v2/RESEARCH_CONTRACT.json](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/dual_source_execution_v2/RESEARCH_CONTRACT.json), and [analysis_transition_20260930/NEXT_ANALYSIS_AGENDA.md](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/NEXT_ANALYSIS_AGENDA.md). Commit `6f517aa` froze the transition and resumable-table gate.
- Oct 3–4: the first complete semantic/narrow release and bounded comparison package were published. Commit `a0ed226` published the full experience/technology aggregates; [pre_revelio_execution_v1/DECISION_REGISTER.md](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/pre_revelio_execution_v1/DECISION_REGISTER.md) records measurement limits. Commits `f0df6b5`, `6ff5dcb`, and `758687e` closed the six-table release and D63 findings.
- Oct 8–9: rule-first production and cloud-control policy were published (`20c297e`, `6484670`, `92a6e1f`, `2c28057`, `e348513`). The project moved toward scheduled cloud execution and explicitly prohibited unapproved paid API/model work. D58/D59/D60 receipts preserve the production, transport, and future-execution boundaries.
- Oct 10: D64 was adjudicated (`5330ead`), then corrected by D65. The authoritative correction is [reuse_audit_20261010/ROOT_REUSE_DECISION.json](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/reuse_audit_20261010/ROOT_REUSE_DECISION.json): the old 2,464-shard extraction was already complete, while the newer rule-first controller represented a distinct incremental measurement. D66 then performed exact-key overlap and bounded comparisons (`5a1aea8`), followed by D67 additive projections (`7989998`, `232465c`).
- Oct 11: D68 closed the rule-only baseline with bounded adjudication (`2e51035`). Its public contract is [reuse_expansion_20261010/FINAL_CLOSEOUT_CONTRACT_PUBLIC.json](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/reuse_expansion_20261010/FINAL_CLOSEOUT_CONTRACT_PUBLIC.json). It explicitly states that semantic validation was not performed and that no CLI/API inference was claimed.
- Oct 12: the first bounded Pro review batch and Wave02 were published. Commits `834a9c8` and `c9c3d94` published 14 reviewed records plus validation/archive provenance. Commit `356564e` published 96 Wave02 reviewed contexts, impact outputs, duplicate-aggregate resolution, and private-archive cleanup provenance. The final Wave02 interpretation is [pro_review_wave02_20261012/RESULTS_AND_DECISIONS.md](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/pro_review_wave02_20261012/RESULTS_AND_DECISIONS.md).

## Abandoned, superseded, and final branches

- The original broad cleaning/enrichment and model-evaluation branch remains historically documented under `cleaning_pipeline_20260927/`, `cleaning_pipeline_20260928/`, and `pre_revelio_execution_v1/`. Its outputs were retained, but later work did not treat every later rule-first gap as unfinished base extraction.
- D63/D64’s “remaining extraction” interpretation was superseded by D65. The correction preserves D63/D64 execution history while changing the default action to reuse the completed old base and add only named fields.
- The D64 successor controller was held; D66/D67/D68 are additive/reuse branches, not a restart of the 2,464-shard base extraction.
- The Pro/CLI setup branch was stopped. Public receipts state no CLI research computation and no paid API/model inference. Wave01 and Wave02 Pro reviews are bounded, purposive semantic decisions; they are not population accuracy samples or whole-corpus certification.
- Failed or superseded jobs remain visible in public receipts: Wave02 selection `124251525` failed and was replaced; partial validation `124252906` was rejected despite exit 0 because schema validation was false; impact attempts `124260742` and `124263976` failed before successful `124267010`; aggregate submissions `124253429` and `124253432` both completed after SSH ambiguity, with the stale self-referential receipt hash rejected and five non-self outputs independently verified.

## Why the earlier base extraction was missed

The durable evidence was present in Git: commit `a0ed226` published the full experience/technology aggregates, and D65’s [ROOT_REUSE_DECISION.json](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/reuse_audit_20261010/ROOT_REUSE_DECISION.json) identifies the completed source as `pre_revelio_execution_v1/results/full_semantic_narrow_v1/BATCH_RECEIPT.json` with 2,464 source shards and 204,774,035 canonical ads. The miss arose because later D63/D64 scheduler counts referred to a new rule-first extractor and were read as overall corpus incompleteness. The distinction between “new rule version still running” and “old base extraction already complete” was not carried into the active execution narrative until D65. There is no single persistent task ledger that superseded the Git records; decisions were distributed across commit messages, `analysis_transition_20260930/`, root AGENTS rules, cloud receipts, and adjacent local task directories. This fragmentation, plus treating scheduler continuation counts as a corpus denominator, explains the earlier failure of memory/retrieval rather than an absence of the completed receipt.

## Persistent decision sources located

- Project rules: `/Users/lilyluo/Documents/LinkUp_Research_20260924/AGENTS.md` and `reproducibility_git/linkup/AGENTS.md`.
- Transition decisions: `/Users/lilyluo/Documents/LinkUp_Research_20260924/analysis_transition_20260930/`.
- Base-reuse audit: `/Users/lilyluo/Documents/LinkUp_Research_20260924/analysis_transition_20260930/reuse_audit_20261010/`.
- D66 reuse contract/results: `/Users/lilyluo/Documents/LinkUp_Research_20260924/analysis_transition_20260930/reuse_analysis_20261010/`.
- D67/D68 expansion and closeout: `/Users/lilyluo/Documents/LinkUp_Research_20260924/analysis_transition_20260930/reuse_expansion_20261010/`.
- Pro Wave01/Wave02 public contracts and receipts: `/Users/lilyluo/Documents/LinkUp_Research_20260924/analysis_transition_20260930/pro_review_20261012/` and `/Users/lilyluo/Documents/LinkUp_Research_20260924/analysis_transition_20260930/pro_review_wave02_20261012/`.
- Local planning files outside Git: `/Users/lilyluo/Documents/LinkUp_Research_20260924/PLAN_COMPLETION_AUDIT.md`, `/Users/lilyluo/Documents/LinkUp_Research_20260924/ROUND_PLAN_20260928.md`, and `/Users/lilyluo/Documents/LinkUp_Research_20260924/PLAN_COMPLETION_AUDIT.md`.
