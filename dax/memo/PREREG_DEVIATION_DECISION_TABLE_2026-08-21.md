# DAX upstream-gate deviation and decision table — 2026-08-21

The outcome seal remains closed. This table classifies proposed or completed
changes; it does not authorize any item marked `NEED_HUMAN`.

| Item | Classification | PI decision required | Fresh red team required | Current status / rationale |
|---|---|---:|---:|---|
| Mapping A v1 to proposed v2 | Methodological deviation | Yes | Yes | v1 executed and failed coverage; v2 changes candidate generation, labels, and transport. Validation prep only. |
| Dense + lexical candidate generation | Methodological deviation | Yes | Yes | Exact model revision and BM25 rules are frozen for blind validation, but production use is not approved. |
| Independent relation labeling | Implementation safeguard plus methodological clarification | Yes, for binding taxonomy | Yes | Blind fields and vendor separation are mechanical safeguards; relation taxonomy changes the substantive map. |
| Many-to-many transport | Methodological deviation | Yes | Yes | Proposed rule replaces v1 one-best behavior and can change occupation exposure. |
| Inherited Mapping A validation thresholds | Already preregistered | No new decision | Review with v2 | PI Decision 7 supplies 10% stratified human audit, weighted kappa >=0.70, and crossing agreement >=90%. |
| New Mapping A candidate-recall/coverage/family thresholds | Methodological deviation | Yes | Yes | `NEED_HUMAN`; code has no unapproved defaults. |
| GDPval task-duration source hierarchy | Implementation clarification preserving the adoption-cost estimand | Yes, before binding fallback | Yes | Primary exact task/version data preferred; public release has 0/220 task-level values. |
| Qualified-human duration fallback | Methodological deviation | Yes | Yes | Three independent qualified annotators are proposed; numeric agreement floor remains `NEED_HUMAN`. |
| Benchmark choice (0.13/0.16/0.19) | Methodological deviation from prior temporary 0.19 choice | Yes | Yes before freeze | Executable value remains null; 0.13 and 0.16 sourced, 0.19 provenance unknown. |
| Entrant companion demotion | Evidence-triggered deviation preserving honest scope | Restoration only | Yes before restoration | Accepted red-team action after real pre-event support audit; exploratory and outside Gate 1. |
| Event/model eligibility | Existing fail-closed evidence rule | Only to change the rule | Yes if changed | Rows lacking required dated evidence remain excluded; no eligibility rule changed in this batch. |
| W4 capture rules | No change in this batch | Not applicable | Not applicable | Infrastructure may be checked; no model measurement, stand-in, retry, scoring, or price rule was altered. |
| W5/power execution | No methodological change; missing-input block | Benchmark and upstream gates | Yes after populated inputs | Schemas/engines exist, but real W5 and real power remain blocked and were not run. |

Any approved production change must be dated and signed before outcomes are
opened. First-run artifacts remain retained; failure does not authorize
threshold or specification search.
