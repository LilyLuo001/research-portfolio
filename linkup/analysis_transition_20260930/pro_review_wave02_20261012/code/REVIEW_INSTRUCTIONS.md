# Wave02 compact semantic review

Review only the row's `question`. Do not recreate the full JOINT review and do not inventory unrelated experience, technologies, or duties. Every output row is a real model judgment after reading the supplied context; never fill labels mechanically from frozen flags.

## Identity and evidence

Copy the canonical four-key, `source_exact_text_sha256`, `context_sha256`, question, frozen-before snapshot, and coverage scope exactly from the packet. Evidence spans use normalized Unicode code-point offsets in the supplied context and must satisfy `context[start:end] == quote`. Include a qualification heading when it determines required/preferred status. Do not use navigation, compensation, employer mission, or equal-opportunity boilerplate as applicant evidence.

`coverage_scope.level` means:

- `full_document`: the complete advertisement was reviewed.
- `exhaustive_target_context`: the packet generator independently certifies that its retrieval covers every context relevant to this question. Reading every supplied excerpt does not create exhaustiveness.
- `partial_context`: the packet cannot establish absence at advertisement level.

Keyword-derived evidence snippets, selected spans, and “all supplied excerpts read” remain `partial_context` unless the packet carries an independent generator certification. For partial context, a rejected candidate or no matching sentence means `ad_level_presence: unknown`, never absence. `absent_after_exhaustive_review` is permitted only after reviewing the full document or every target-relevant item in a generator-certified exhaustive packet. Before assigning absence, review all target evidence, not merely the most consequential clauses. A local contradiction cannot negate an existing advertisement-level positive elsewhere.

## Question: `experience_4dims`

Always return the four `dimension_outcomes` in schema order: general work, occupation/task, industry/domain, and tool-specific. Each gets an advertisement-level `present`, `absent_after_exhaustive_review`, or `unknown`, independent of whether a clause detail is emitted. This prevents omitted dimensions from being mistaken for negatives. `clauses` contains only relevant positive, corrected, or unresolved clause details and may be empty after a full-document/exhaustive review finds no experience requirement.

Classify clause objects as `general_work`, `occupation_task`, `industry_domain`, `tool_specific`, or `unresolved`. General work requires explicit general/professional/work/employment experience language and must not be used merely because a specific object was missed. Named delivery or engineering work is occupation/task experience; do not turn it into unrestricted general work.

Keep `strength` separate from `conditionality`. Strength is only `required`, `preferred`, `unspecified`, or `unresolved`; conditionality is independently `unconditional`, `conditional`, `unspecified`, or `unresolved`. Preserve degree/experience alternatives by group and branch. Attach years only to the clause or branch they govern; never copy a shared number to every named tool. A named tool used to build an application is not the object being developed.

## Question: `entry_responsibility_4dims`

Entry targets distinguish explicit no-experience, explicit new-graduate language, current-student internships, other targets, not stated, and unresolved. Academic class standing is not occupational seniority. “Mentor junior staff” describes other employees unless the advertised worker is itself identified as junior.

Return exactly four responsibility outcomes in schema order: independent judgment, client ownership, people supervision, and training/mentoring. Record both subject and relation: `current_duty`, `required_capability`, and `prior_experience` are distinct; only `current_duty` may enter a strict-duty comparison, while capability and prior experience remain separate. Only `advertised_worker` can support a positive advertised-worker responsibility. Owning customer data, speaking with clients, leading a technical effort, or employer-wide culture language does not by itself establish client-account ownership or people supervision. Programming or technical support is not automatically routine execution; routine execution is outside this compact question.

## Output discipline

Use `confirmed`, `corrected`, or `unresolved` against the frozen candidate. Preserve unknowns. Do not infer negative labels from silence, propagate judgments, alter parser rules, or calculate population metrics. Propagation, if later authorized, requires identical source text and context hashes and must still preserve one observation per canonical advertisement.
