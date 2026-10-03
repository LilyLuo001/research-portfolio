# LinkUp structured extraction prompt v1.0.0

Return exactly one JSON object conforming to `schema/extraction_v1.schema.json`. Analyze only the supplied advertisement text. Do not infer from employer identity, title alone, marketing copy, or outside knowledge.

For each of the four experience objects (`general_work`, `occupation_task`, `industry_domain`, `specific_tool`), return exactly one finding. Keep the observation states distinct:

- `explicit_positive`: applicant-facing language positively requires, prefers, or expects the condition.
- `explicit_negative`: the text explicitly says the condition is not needed (for example, “no prior experience required”).
- `not_mentioned`: readable text contains no statement about this object.
- `insufficient_text`: the supplied text is empty, broken, truncated, or otherwise cannot support a decision.
- `unresolved`: relevant language exists but its meaning or object cannot be resolved.

Do not turn absence into `explicit_negative`, and do not encode any of the last four states as zero years. Set `state_applicant_context=true` only when the object-level state is supported by applicant-facing language; it must be true for positive or negative requirements and false for `not_mentioned`/`insufficient_text`. For `explicit_positive`, create one mention per applicant qualification. Every mention must include the shortest exact verbatim evidence span and zero-based, end-exclusive character offsets into the original text. Never normalize whitespace inside a span.

Keep `condition_mode` separate from the object. `knowledge`, `proficiency`, and `training_certification` are conditions, not proof of `prior_experience`. In particular, tool proficiency is not prior tool use; domain knowledge is not prior industry work. Use `unclear` when the text does not distinguish them.

Bind every duration to the same mention, object, qualification branch, and evidence span that states the number. A bare “3 years” is `stated_unspecified` unless wording establishes a minimum, maximum, exact value, or range. Education equivalence does not become work tenure. Use `branch_relation=or` or `equivalent` plus the same `alternative_group` for alternatives; use `and` only for jointly required branches. Never add durations across mentions or branches.

Technology findings must be applicant-specific. Company products or general marketing are not applicant roles. Technology classes may overlap, so return separate findings when supported. Distinguish these cases:

- developing or training an AI system: `technology_role=develop_train`, `ai_role_basis=develop_or_train_ai`;
- integrating an AI system: `implement_integrate`;
- using an AI assistant to write ordinary software: `use_operate`, `ai_role_basis=use_ai_to_write_software`;
- developing ordinary software without AI evidence: class `software_information_system`, basis `not_ai`.

Using AI to develop software does not establish developing AI. “No AI detected” means `not_mentioned`, not known non-adoption. Every `explicit_positive` or `explicit_negative` technology finding needs an exact evidence span. Preserve genuine ambiguity as `unresolved`.

The caller supplies `record_id` and computes `source_text_sha256`; copy both exactly. Do not add commentary or Markdown.
