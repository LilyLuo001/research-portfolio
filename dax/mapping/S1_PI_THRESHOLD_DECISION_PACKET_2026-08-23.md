# DAX v3 S1 prospective threshold decision packet

**Status:** `NEED_PROSPECTIVE_PI_THRESHOLD_SIGNATURE`

No binding S1 numerical construct-validity threshold existed before the
120-task audit. This packet does not choose a cutoff after seeing the pilot and
does not authorize S3, model inference, or production measurement.

## Rules that already exist—and do not answer this decision

| Existing rule | Scope | S1 implication |
|---|---|---|
| CPS/O*NET mapped component mass ≥90% | W2 crosswalk completeness | Not a benchmark construct-validity threshold. |
| V2 task-mass coverage ≥80% and family coverage ≥70% | Frozen Mapping A v2 validation | Historical v2 only; not inherited into the redesigned v3 benchmark. |
| V2 PPV/FPR/recall/adjudication/transport rules | GDPval direct-relation classifier | Different unit and validation target; not an S1 item-validity rule. |
| S1 `PASS/REVISE/NON_EVALUABLE` item rule | Individual constructed item | Applied exactly, but supplies no aggregate pilot pass cutoff. |

## Complete pilot distribution available to the PI

- Item status: 13 `PASS`, 11 `REVISE`, 96 `NON_EVALUABLE`.
- Pilot task-mass shares: 12.7861% `PASS`, 12.9327% `REVISE`, 74.2812%
  `NON_EVALUABLE`.
- Equal-family shares: 10.7576% `PASS`, 8.7879% `REVISE`, 80.4545%
  `NON_EVALUABLE`; 12 of 22 families contain at least one pass.
- Seven items are fully mechanically scoreable and pass. They represent 4.7720%
  of pilot task mass. Six additional passing items need limited human rubric
  review.

These values describe the audit. They are not used below to reverse-engineer a
passing rule.

## Aggregate threshold dimensions requiring signature

| Dimension | PI must specify prospectively | Consequence of stricter choice | Consequence of looser choice |
|---|---|---|---|
| Construct-pass share | Metric denominator and minimum unweighted `PASS` share. | Higher construct confidence; likely confines inference to a narrow digital/document subset. | More items can advance, but `REVISE` defects may contaminate task-boundary validity. |
| Task-mass pass share | Whether and at what minimum descriptive or future design-weighted mass must pass. | Preserves economic relevance; may reject a scientifically valid partial-identification design. | Permits sparse measurement; wider missing-mass bounds and weaker occupation interpretation. |
| Occupation-family coverage | Minimum families with a pass and/or minimum equal-family pass share. | Reduces family concentration and improves transport; increases expert/environment burden. | Faster capture but risks results driven by a small set of document-heavy families. |
| Revision allowance | Whether `REVISE` may be repaired and re-audited; maximum revision rate; one-time repair rule. | Limits researcher degrees of freedom and post-audit tailoring. | Recovers valid tasks but increases redesign discretion; must prohibit model-result-informed revision. |
| Non-evaluable mass | Maximum acceptable unidentified mass, or explicit approval of partial identification and lower/upper bounds. | Supports a broader central interpretation only if feasible; may make v3 impossible for embodied/interpersonal work. | Honest partial identification, but cannot be described as full-economy occupational displacement. |
| Objective scoring | Minimum task-mass share with fully mechanical scoring and allowed human-rubric share. | Improves reproducibility and historical capture speed. | Broadens work products but adds rater reliability, governance, and cost dependencies. |
| Expert construct validation | Reviewer number, qualifications, blinding, agreement statistic/floor, and adjudication rule. | Stronger validity and independence; higher delay/cost before retirement deadlines. | Quicker capture but the current single-Codex audit is not sufficient external validation. |
| Historical executability | Minimum share executable across required model vintages versus vintage-specific missingness/bounds. | Improves longitudinal comparability. | Preserves more modern/file/tool items but risks changing sample composition across vintages. |

## PI decision form

No field is approved until signed and dated.

| Decision | PI entry |
|---|---|
| Primary aggregate S1 metric(s) and denominator(s) | `NEED_HUMAN` |
| Minimum construct-pass value(s) | `NEED_HUMAN` |
| Task-mass and family coverage values | `NEED_HUMAN` |
| Revision/re-audit rule and maximum permitted revision cycle | `NEED_HUMAN` |
| Non-evaluable-mass treatment: central design, partial identification, or stop | `NEED_HUMAN` |
| Mechanical versus human-rubric scoring requirement | `NEED_HUMAN` |
| Independent expert validation and agreement rule | `NEED_HUMAN` |
| Historical-vintage executability requirement | `NEED_HUMAN` |
| Formal S1 disposition | `NEED_HUMAN` |

**PI name/signature:** `NEED_HUMAN`

**Date:** `NEED_HUMAN`

**Decision commit/version:** `NEED_HUMAN`
