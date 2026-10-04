# Measurement semantic revision v1.1

This directory is the single D26 semantic revision. It leaves `measurement/` v1 prompts, schema, code, labels, and the original 20-row diagnostic unchanged. No semantic revision remains after v1.1.

The revision is limited to four observed failures: experience-object/duration binding, local required/preferred scope, education/work qualification branches, and AI train/develop versus deploy/maintain or training-data preparation. The schema adds only `qualification_scope` and nullable exact `condition_quote` to an experience mention.

The actual next blind pack is outside the repository's public measurement tree at:

`linkup_sample/private/run-123584403/measurement_dev_revision_v1_1/blind_unused20_A10_B10.jsonl`

It has exactly two fields (`record_id`, full `original_text`), 20 unique fixed80 records, 10 from each original A/B arm, no text equal to the previously read 20, and no within-pack full-text duplicate. `BLIND20_SELECTION_AGGREGATE.json` records the fixed hash rule, aggregate exclusions, counts, and artifact SHA without record IDs or text.

Use `BLIND_READER_INSTRUCTIONS.md` for the two independent Sol/medium readings. Mechanical offset expansion and structural/evidence validation are local. They do not infer omitted durations or repair semantics.

The schema and validator can enforce shape, exact spans, branch fields, and condition evidence. They cannot prove that a reader found every digit or spelled-out duration, chose the right object, or interpreted a section correctly; those remain semantic checks for the independent readings and bounded adjudication.

Candidate year aggregation in `aggregate_candidate_v1_1.py` accepts only structurally valid v1.1 rows. Its candidate unconditional-prior-experience duration bucket includes only `prior_experience` mentions with `qualification_scope=unconditional`. This structural/scope filter is not acceptance as a formal production metric. Education substitutions and other conditional mentions are reported separately. Missing, unresolved, non-year, proficiency, knowledge, and training/certification conditions never become zero years.

`validate_cached_shard_v1_1.py` is the deferred L3 offline-import interface. It validates cached prediction shards and explicit failure evidence against a source shard and writes a resumable receipt; it performs no model/API call. The existing unavailable batch gate remains authoritative. The 40,300 production extraction has not started. The evaluation200 keys are provisional and unrevealed, not locked, and this revision does not read or prepare them.
