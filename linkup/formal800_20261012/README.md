# Formal800 finite review and analysis

Current state: the finite review of 800 ads is complete and released as a
bounded sample analysis. It is not a global-corpus certification. Freeze
job46364888 selected800 ads (719 complete contexts) from9,282 eligible fixed10k
ads; all719 primary contexts and153 independent blind-audit contexts passed
consolidation. Final jobs46394029,46394097, and46394098 completed successfully.

This directory contains the frozen methods, review schema, validators, bounded
audit merge helper, and scheduled SCNet sampler/analyzer for the approved finite
review (A/B/C 320/320/160). Root40 comprises36 selected differences and4
agreements. The composite144/153 discordance is a bounded comparison result, not
a population error rate.

See [RESULTS_ZH.md](RESULTS_ZH.md) for the result report, T1–T6 tables, the two
figures, and the primary-baseline comparison. The final public receipts include
the scheduler and provenance records; no raw IDs, text, labels, credentials, or
secrets are included.

Use `EXECUTION_LEDGER.md` for actual job receipts and the retrospective
`PROJECT_STATE.json` for resumption. Earlier preparation entries are retained as
history, not current blockers. Git main publication was explicitly authorized
by the user after the first default-branch approval rejection.

The sampler fails closed when required cloud assets are absent. Private packets,
canonical keys, raw text, row-level linkage, credentials, and review outputs
must never enter Git.
