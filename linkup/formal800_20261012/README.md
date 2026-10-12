# Formal800 finite review and analysis

This directory contains the frozen methods, review schema, validators, bounded
audit merge helper, and scheduled SCNet sampler/analyzer for the approved
finite review of at most 800 ads from the fixed10k frame (A/B/C 320/320/160).
Sampling, validation, weighting, aggregation, and uncertainty calculations run
only as scheduled cloud jobs. Freeze job46364888 selected800 ads (719 complete
contexts) from9,282 eligible fixed10k ads. All153 independent blind-audit contexts
are mechanically validated. Primary reading, bounded repairs and final review
are still in progress; final analysis is not yet complete.

Use `EXECUTION_LEDGER.md` for actual job receipts and the retrospective
`PROJECT_STATE.json` for resumption. Earlier preparation entries are retained as
history, not current blockers. Git main publication was explicitly authorized
by the user after the first default-branch approval rejection.

The sampler fails closed when required cloud assets are absent. Private packets,
canonical keys, raw text, row-level linkage, credentials, and review outputs
must never enter Git.
