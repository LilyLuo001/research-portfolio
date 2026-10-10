# D63 first-five static engineering review

Reviewed code SHA `2b773e8f13af5c70b6f0b891923cc5112fb41ac70e1da2b61dc7d41d26a94e84` for the three prior blockers.

- Enforces 424,226 total postings as `424,225 processed + 1 invalid_text`; analysis features exclude invalid_text, which cannot enter technology groups or no-observed counts.
- Keeps experience `scope` unknown separate from conditional/alternative scope.
- Restricts `explicit_no_experience` evidence to `objects == ["general_work"]`, reconciling it to the frozen flag; tool/industry waivers are excluded.
- Public output gates remain aggregate-only; no row identifiers or raw evidence text are emitted.

Status: static blockers resolved. Final acceptance still requires the scheduled run receipt and QA arithmetic checks; this review performs no local research computation.
