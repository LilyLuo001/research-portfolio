# Existing recovered relation metadata: inventory boundary

No new execution result is claimed. Only the newest `linkup/AGENTS.md`, existing
recovery code/public report and year-binding contract/code were inspected. The
inventory script has passed a local AST syntax check only; private data and SSH
were not accessed. Root owns scheduler execution and the production decision.

All paths below are existing JSON paths, relative to the recovered directory
already supplied to `prepare_year_object.py --recovered`. They are not proposed
new reference files. Recovery filenames are emitted at
`relation_feasibility_20261024/code/materialize_supervision.py:262–265`.

| Relation | Existing original path | Existing recovered fields | Limit |
|---|---|---|---|
| Required/preferred experience requirement scope | `/experience_clauses/{i}/object`, `/strength`, `/conditionality`, `/alternative_group`, `/alternative_branch` | `RECOVERED_ORIGINAL_ITEMS_PRIVATE.jsonl`, family `experience_strength`: `labels.object`, `labels.strength`; family `qualification_conditions_and_alternatives`: `labels.object`, `labels.conditionality`, `labels.alternative_group`, `labels.alternative_branch`. Four-family accepted tuples, when available, are also in `accepted_same_item_experience_tuple`. | Real same-item object/strength/condition binding, not a separate scope-cue→arbitrary-requirement endpoint annotation. Does not establish required/preferred scope for every non-experience qualification. |
| Alternative branches | `/qualification_alternatives/{g}/group`, `/relation`, `/branches/{b}/branch`, `/branches/{b}/quotes`; `/experience_clauses/{i}/alternative_group`, `/alternative_branch` | `QUALIFICATION_GROUPS_PRIVATE.jsonl`: `original_group`, `original_group_path`, `accepted_family_status`, `evidence[].branch`, `referenced_by_experience`. Qualification item rows additionally have `explicit_qualification_group`, `qualification_group_evidence`. | Explicit original local group/branch IDs bind items; OR/AND is the group relation. IDs are local identities, not transferable class labels. Null branch can mean shared condition; null group is not a negative. |
| Responsibility subject | `/responsibility_items/{i}/dimension`, `/subject`, `/relation`, `/conditionality` | `RECOVERED_ORIGINAL_ITEMS_PRIVATE.jsonl`, family `current_responsibility_subject_and_relation`: same four `labels` fields; exact item retained in `original_item_audit_only`. | Subject is an original categorical label, not a named subject endpoint span. Dimension/subject/relation/condition remain bound within the original item. |

Recovery schema definitions: `materialize_supervision.py:21–28`; accepted original
mask/provenance and reviewed-full checks: `:155–189`; group recovery: `:192–210`;
item identity/labels and absent endpoint spans: `:213–227`; explicit group linkage:
`:228–238`; four-family tuple: `:250–254`. Safe same-item identity is
`(context_sha256, source_sha256, source_record_id, original_item_path)`. Family-array
position alone is not a cross-family join. The new inventory also requires the
original object label to agree when joining strength/object/qualification rows.

The frozen ledger in the recovery manifest supplies family status, isolation and
original source acceptance; final1331 and the unchanged legacy adapter supply
original split membership. Inventory preserves `train`,
`final_previously_exposed`, `previous_holdout_reserved_not_final` and validates
each recovered split. Source files, frame parquet, packets and
`CONTEXTS_PRIVATE.jsonl` are never opened. The already recovered JSONL files contain
quote fields; inventory parses their metadata but never accesses quote values or
document bodies. Inputs are read-only and SHA checked; output is create-only.

Existing `RECOVERABILITY_PUBLIC.json` already gives these unique-context supports:

| Original class | Train | Previously exposed final |
|---|---:|---:|
| Strength required | 5568 | 1242 |
| Strength preferred | 4325 | 952 |
| Strength explicitly_waived | 49 | 4 |
| Strength unspecified | 50 | 6 |
| Group OR | 2153 | 506 |
| Group AND | 40 | 13 |
| Responsibility subject advertised_worker | 5316 | 1185 |
| Responsibility subject other_employee | 10 | 2 |
| Responsibility subject employer_general | 5 | 2 |
| Responsibility conditional | 128 | 41 |

These are marginal clause/group supports, not unique candidate-bound training
pairs or accuracy. The original 50-train/50-final floor fails for several retained
classes. Joint tuple supports are not in the existing report; the new inventory
counts them without dropping classes. Actual branch memberships and same-item
scope metadata exist, but the current references do **not** establish a trainable,
fully supported end-to-end system for all three full relations.

Explicit pair-specific negative/no_relation annotation is absent from the existing
schema. Recovery reports `entity_pair_ready_rows=0`, `generated_no_relation_rows=0`
and explicitly states the absence at `materialize_supervision.py:283,290–293`.
Year binding independently preserves this boundary in
`year_object_relation_20261024/code/INPUT_BINDING_CONTRACT.md` and
`prepare_year_object.py:233–237,278–286,420–427`. `known` is an acceptance state;
`not_applicable` is document nonmention; null, absent mentions, unresolved and
unmatched candidates are not pair negatives. An advertised-worker label does not
automatically label every other potential subject pair negative. The script does
not manufacture negatives by crossing original items, branches or subjects.

`inventory_relation_metadata.py` requires `--recovered`, receipt-bound
`--items-sha256`, `--groups-sha256`, unchanged `--input-manifest`, and a new
`--output`. It refuses execution without `SLURM_JOB_ID`. Its sole output is
`RELATION_METADATA_PUBLIC.json`: safe enum aggregates, original schema-key counts,
family masks, branch binding states and unique-context split/joint supports. Local
IDs, record identities, quotes, free text, and noncore enum values are not emitted.
No labels, parser, candidate generator, model or training are added. No scheduler
submission is performed by this code-preparation subtask.
