# GDPval task-duration author-outreach packet — 2026-08-21

**Status:** draft only; not sent. No author response or private duration value
is implied. The public 220-row GDPval release contains no task-level duration
field, while the paper documents validated self-reported professional
completion time in Appendix A.2.4 and aggregate statistics in Appendix A.4.

## 1. Draft message

**Subject:** Research request for GDPval gold-subset task-level human completion-time metadata

Dear GDPval authors/data-access team,

I am conducting academic research on occupation-task exposure to changes in AI
capability and cost. The analysis uses the 220-task GDPval gold subset. Your
paper describes validated self-reported real-world professional completion
times, but I could not locate task-level timing fields in the public parquet.

Would you be willing to provide, under any confidentiality or data-use terms
you require, the task-level human completion-time metadata for the 220 gold
tasks? The minimum useful file would join exactly to the released task IDs and
identify the dataset version, original units, timing definition, and validation
status. We would use the values only to estimate human active-completion cost
for each task and associated sensitivity bounds. We would not use them to train
models, identify workers, publish restricted row-level data, or evaluate any
individual expert.

We can receive the file through a BU-approved secure transfer route, store it
only on Boston University SCC private storage with restricted permissions, and
commit only hashes, aggregate coverage counts, and non-sensitive provenance to
Git. We are happy to execute a data-use agreement and follow a requested
retention or destruction schedule.

Could you also clarify whether the 404-minute gold-subset average reported in
Appendix A.2.4 and the 9.49-hour mean in Appendix A.4 Table 3 use different
universes, weighting, or timing constructions? We will not substitute either
aggregate for missing task-level values.

Thank you for considering the request. I can provide a short methods note,
IRB/data-management information if applicable, and the exact proposed output
disclosure table.

Sincerely,

Lily Luo

Boston University

## 2. Requested data dictionary

### Required variables

| Variable | Required content |
|---|---|
| `task_id` | Exact public GDPval gold-subset task identifier |
| `dataset_revision` | Release/tag/commit or dated benchmark version to which the task belongs |
| `duration_original_value` | Unrounded task-level value as collected or frozen |
| `duration_original_unit` | Minutes, hours, or other explicitly defined unit |
| `duration_active_minutes` | If already derived by the authors; otherwise the project will convert hours once as `hours*60` |
| `duration_statistic` | Individual report, validated value, mean, median, consensus, or another named construction |
| `timing_definition` | Exact inclusion/exclusion instructions shown to experts, including reading, preparation, tool use, QA, waiting, and coordination |
| `measurement_basis` | Self-report, observed elapsed time, time log, or another collection method |
| `n_reporting_experts` | Number of professional time reports contributing to the task value |
| `n_independent_validators` | Number of occupational reviewers who independently validated/corrected the report |
| `validation_status` | Passed, corrected, unresolved, excluded, or another defined status |
| `collection_or_freeze_date` | Date or version timestamp sufficient for provenance |

### Strongly preferred variables

- lower/upper or dispersion information for the human time report;
- de-identified report/validator IDs sufficient to distinguish repeated people,
  without names, email addresses, employers, or free-text personal information;
- reason code for corrections or exclusions;
- occupation/sector fields used in the released benchmark;
- provenance locator linking the values to the paper/release;
- license, redistribution, citation, retention, and deletion requirements.

Individual names and contact details are not requested. If only a validated
task-level frozen value can be shared, the project can work with that smaller
schema provided its construction and units are documented.

## 3. Exact acceptance and use rules

1. Join only by exact `task_id` and `dataset_revision`; semantic/occupation
   matching is prohibited.
2. Preserve original value and unit. Convert hours to minutes exactly once.
3. Require the paper's validated-self-report basis and at least two independent
   occupational validators for an author-supplied frozen value, or retain the
   task as unresolved.
4. Do not replace missing values with the 404-minute or 9.49-hour aggregate,
   an occupation mean, or another task.
5. Construct lower/median/upper human-cost sensitivity inputs. If uncertainty
   is not provided, the project will disclose that limitation rather than
   invent task-level dispersion.
6. Do not expose model performance, W5 exposure, power, treatment effects, or
   outcomes to the duration source or use them to accept/reject a duration.

## 4. Confidentiality and storage plan

- Receive through an author-approved secure route, not a public issue or chat.
- Store under
  `/usr3/graduate/qluo/dax-private/task_duration/author_source_<YYYYMMDD>/`
  on BU SCC; directories mode `700`, files mode `600`.
- Never add the file, task-level timing rows, personal metadata, or transfer
  credentials to Git.
- Create a private manifest with file hash, receipt time, source, permissions,
  row count, schema, and authorized use. Git receives only a sanitized receipt
  with hashes, coverage counts, and source/license status.
- Limit access to named project personnel; do not transmit task-level values to
  external model APIs.
- Follow the authors' DUA, attribution, disclosure, retention, and secure
  destruction requirements. If terms prohibit derived row-level release, only
  aggregate diagnostics and code will be released.
- No outcome data is joined during the duration audit.

## 5. Outreach authorization form

- PI authorizes sending the draft request: YES / NO / REVISE
- Approved sender and institutional contact information: ____
- Approved secure transfer channel: ____
- PI accepts exact-ID-only matching and no aggregate substitution: YES / NO
- If authors decline or do not respond by ____ date, proceed to the separately
  signed qualified-human fallback: YES / NO
- Additional DUA/privacy conditions: ____
- PI name/signature/date: ____

Until signed, this packet remains `DRAFT_NOT_SENT`.
