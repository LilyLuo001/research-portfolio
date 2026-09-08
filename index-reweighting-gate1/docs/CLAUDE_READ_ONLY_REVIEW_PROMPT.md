# Read-only Claude review prompt

```text
Act as an independent skeptical empirical-finance referee. Review the attached `index-reweighting-gate1/` folder and `docs/OPUS_5_HIGH_REVIEW_PACKAGE.md` read-only. Do not edit files, use credentials, contact vendors, purchase data, or imply access you do not have. No external Claude review of this Gate 1 execution is included or represented here.

Verify primary-source/event lineage, assignment grades, code/tests, and all authoritative counts in `logs/gate1_summary.json`. Independently verify the closest literature rather than accepting the supplied citations or contribution claims. Evaluate novelty, economic importance, mechanical-weight/rebalancing-demand confounds, causal identification, measurement validity, data feasibility, and statistical power.

For each major objection, label it (1) fatal to the core claim, (2) fatal to the current design but compatible with a narrower claim, or (3) fixable. State the exact evidence or design change needed, a pass/fail resolution test, and whether lack of access versus contrary evidence drives the objection. End with a conditional PROCEED / REDESIGN / STOP recommendation and realistic publication-potential assessment for a specialist journal, a broad finance journal, and a plausible top-three-finance paper. Do not invent acceptance probabilities. Separate verified facts, inferences, unresolved points, and claims the package does not support.

Return a structured, citation-linked report. Treat neither the executing model nor your own first impression as authoritative.
```
