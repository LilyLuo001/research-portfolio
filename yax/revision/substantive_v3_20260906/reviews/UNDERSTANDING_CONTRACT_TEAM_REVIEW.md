# Team review of the V3 understanding contract

Review date: 2026-09-06  
Reviewer role: separate execution-team agent, requirements-mapping role  
Independence status: **team self-review; not independent scientific verification**

The reviewer checked `UNDERSTANDING_CONTRACT.md` against all fourteen exact Gate-0 questions in `EXECUTION_PROMPT_V3.md`. All fourteen questions were answered. The reviewer found no material scientific error or omitted question.

Three precision edits were requested:

1. The support discussion should make clear that comparison-graph connectivity is not sufficient by itself under separation; full-rank target information and finite target estimability are also required.
2. Reference-period invariance should be scoped to the same model and estimable contrast space with the full covariance transformed; it does not cover changes in weights, sample, nuisance space, or target.
3. The computer-use discussion should distinguish regressor-level exposure/computer correlation from the sampling covariance of the estimated AI and computer coefficients.

All three edits were incorporated into the contract before any new V3 substantive model was run.
