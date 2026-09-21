# P1 empirical decision execution

Started 2026-09-21 under the user's approved execution prompt. Baseline commit: `4ee495f618494d847f2361e96d6fe103c04ebc37`. This directory is a new stage; prior diagnostic receipts remain historical records.

## Actual dispatch

- `sol_empirical_lead`: requested `gpt-5.6-sol`, `medium`; spawn interface accepted. Owns scientific specification, daily analysis and issuer-specific network analysis. No nested delegation.
- `terra_intraday_clock`: requested `gpt-5.6-terra`, `medium`; spawn interface accepted. Owns the bounded public-clock and intraday diagnostic. No nested delegation.
- Parent coordinates integration and publication. The parent model was not switched by a prompt; its exact backend model/effort telemetry is `NOT_OBSERVED`.
- `empirical_referee`: separately dispatched with `gpt-6-astra`, `high` after the completed intraday aggregate and executed daily pilot were available and Terra completed. Interface accepted. Reviews this stage only, including final daily outputs when ready. A launch request is not evidence of backend telemetry or completion.

At most two workers run concurrently. No separate agent is needed for a single shell command or a short status check.

Observed installed CLI: `codex-cli 0.143.0`. The active desktop tool interface accepted the explicit worker model/effort parameters above; independent backend telemetry is `NOT_OBSERVED`. No configuration or authentication was changed. [Official model-selection guidance](https://learn.chatgpt.com/docs/models#choose-a-model-2) was checked using OpenAI Docs; it does not certify this session's backend routing.

## Execution boundary

SCC SSH and the existing P1 mirror were verified available. Licensed row-level data stay on SCC. New development-response permissions apply only after the lead records the scientific specification and resolves development/validation assignment. The old conversion seal is unchanged. This stage does not authorize raw-data exports, authentication changes, subscriptions, or a branch merge.

Only files in this new stage directory will be staged for this turn. Existing unrelated untracked files are preserved.

## Completed branch

Terra completed the bounded intraday diagnostic: nine existing SCC DBN files, aggregate-only reproducer, no new response acquisition, no API request or spending. Two conditional publisher clocks remain inadequate for a scientific first-public claim; the July archive/metadata conflict is preserved. The independent referee is checking the resulting artifacts, not another generic missing-input memo.

## Final closure

Sol completed the daily/network execution, targeted industry repair, source-read correction, control reuse census and secondary same-mask basket diagnostic. The separate referee independently reproduced decisive counts and coefficients and closed `INDEPENDENT_REVIEW.md` with **CONDITIONAL PUBLICATION PASS** for the qualified exploratory package, not scientific GO or a pristine-source-seal certificate. The optional date-bundle network secondary remains explicitly `NOT_RUN`. No further review work is outstanding. Parent verified the two local test scripts, JSON validity and execution-receipt output hashes before publication.
