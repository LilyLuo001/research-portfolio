# Frozen Formal800 research comparisons

Design fixed on 2026-10-13; scheduled execution completed on 2026-10-16.

This release adds two descriptive finite-frame comparisons using the frozen 800-ad Formal800 measures and 719 bound structured reviews. Q1 compares four existing experience dimensions between the frozen GenAI-use and traditional-software-use groups within occupation majors 11, 13, 15 and 17, then standardizes both groups to a fixed 25% composition in each major. Q2 reports strict current-duty and experience-wording co-occurrence among the 33 ads with explicit new-graduate wording, with the existing 54-ad broad waiver-or-graduate domain retained as a secondary sensitivity.

The target remains the 9,282 eligible ads in the realized fixed-10k frame. Estimates use `w3=1/pi3`; no parent weight is used. The phase performed no text extraction, new review, relabeling, resampling, model inference, or semantic change. Unknown fields remain unknown, and sampling intervals exclude semantic-classification and support-selection uncertainty. Full estimand decisions are in [ANALYSIS_DECISIONS.md](ANALYSIS_DECISIONS.md).

Wuzhen scheduler job `46700531` completed in 13 seconds with exit `0:0`, using 2 CPUs and 4 GiB in `wzhdtest`; the reserved DCU was not used for inference or acceleration. See [submission](receipts/SCHEDULER_SUBMISSION.json), [completion](receipts/SCHEDULER_COMPLETION.json), and the passing [analysis receipt](results/ANALYSIS_RECEIPT.json).

Primary outputs:

- [Chinese results memo](RESULTS_DRAFT_ZH.md), [root acceptance](ROOT_ACCEPTANCE.md), and [independent QA](qa/RESEARCH_QA.md)

- [Q1 equal-major standardized estimates](results/Q1_EQUAL_MAJOR_STANDARDIZED.csv) and [pooled/within-major estimates](results/Q1_WITHIN_MAJOR_AND_POOLED.csv)
- [Q2 duties](results/Q2_DUTIES_AMONG_ELIGIBLE.csv), [experience outcomes](results/Q2_EXPERIENCE_AMONG_ELIGIBLE.csv), [experience combinations](results/Q2_EXPERIENCE_COMBINATIONS.csv), [eligibility sensitivity](results/Q2_ELIGIBILITY_SENSITIVITY.csv), and [existing clause co-occurrences](results/Q2_EXISTING_CLAUSE_COOCCURRENCES_AMONG_NEW_GRAD.csv)
- Figures: [Q1](results/FIG1_Q1_EQUAL_MAJOR.pdf), [Q2 duties](results/FIG2_Q2_NEW_GRAD_DUTIES.pdf), and [Q2 experience](results/FIG3_Q2_NEW_GRAD_EXPERIENCE.pdf)

To rerun after staging the frozen private inputs and these exact public code files at the absolute paths recorded by the wrapper:

```bash
sbatch /work/home/lilysharp/private/research_results_20261013/code/wz_run_research_comparisons.sbatch
```

The sanitized release inventory is [RELEASE_MANIFEST.json](receipts/RELEASE_MANIFEST.json). It contains only frozen code, the decision record, returned aggregate results, and scheduler receipts; it excludes private data, credentials, QA work products, drafts, and itself.
