# Evidence contract

Gate 1 asks whether a later measurement pilot is worth the next research
investment. It does not estimate the paper's headline outcome and it does not
promote a convenient proxy into an assignment variable.

## Shared key

Every tabular CSV output begins with `evidence_key`. Keys are stable within a
table and carry a type prefix:

- `LOCAL:` — physical archive inspection;
- `FUND:` — fund identifier or coverage audit;
- `RULE:` / `SOURCE:` — public institutional source or rule regime;
- `EVENT:` — potential or realized intervention;
- `DOSE:` — assignment record;
- `FOMC:` / `SUPPORT:` — common-news date or event intersection;
- `DESIGN:` — comparison/interference diagnostic;
- `GAP:` / `GAPA:` — integrated or Stage-A unresolved input/design requirement.

Cross-table relationships use explicit fields such as `event_id`, `source_id`,
`fomc_evidence_key`, and pipe-delimited `rule_evidence_keys`; an evidence key is
not overloaded as a generic foreign key.

## Assignment grades

- **A:** exact official historical assignment, or a defensible reconstruction
  from complete contemporaneous inputs with reconciliation.
- **B:** an independently documented intervention or selected official
  assignment evidence, but a full precise dose vector or reference inputs are
  incomplete. Grade B alone does not make the row a candidate treatment;
  `binding_status` determines that role.
- **C:** a screening proxy only, such as an ETF holdings snapshot or approximate
  capitalization.
- **U:** unknown or inaccessible evidence. `U` is never recoded as nonbinding.

Only grade A is eligible for a future exact-dose design. Grade B may support a
narrow event-level design if its estimand is stated accordingly. Grade C is a
search aid, not treatment. Missing numbers remain blank rather than being
renormalized, interpolated, or guessed.

These letters are assignment grades in
`assignment_doses_and_evidence.csv` (`evidence_grade`), the event ledger's
`assignment_evidence_grade`, and the comparison audit's `assignment_grade`.
They are not reused silently for a different evidentiary object:

- `source_and_rule_registry.csv` records `rule_source_grade`, explicitly
  describing completeness of rule/source evidence and never assignment
  observability;
- `rebalance_event_ledger.csv` separately records
  `classification_evidence_grade` (evidence that a scheduled check did or did
  not bind) and `assignment_evidence_grade` (observability of the resulting
  assignment);
- a confirmed nonbinding check can therefore have classification grade B and
  assignment grade U; it is never mislabeled as a grade-B treatment.
- `comparison_and_interference_audit.csv` carries `assignment_grade` only as a
  derived copy of the strongest linked dose grade, falling back to the event's
  assignment grade when no dose row exists; it has no generic evidence-grade
  column.

The separate non-assignment grade scales are:

- `rule_source_grade=A` when primary source evidence supplies the exact rule
  operations and applicable interval encoded by the row; `B` when an official
  source supports a bounded rule/event claim but leaves an operation, interval,
  or historical input incomplete; and `U` when the applicable rule evidence is
  unresolved.
- `classification_evidence_grade=A` is reserved for complete contemporaneous
  event-specific classification evidence; `B` means official evidence is
  sufficient to classify the event as binding, nonbinding, or another
  intervention but does not create an exact dose; and `U` means the calendar or
  rule is known while realized binding status remains unresolved, or the row is
  outside the applicable regime and classification is therefore not
  applicable. `binding_status` distinguishes those cases.

## Portfolio objects

The uncapped reference portfolio, rule-assigned index portfolio, observed ETF
holdings, and creation/redemption basket remain separate objects. All weight
comparisons must share a verified valuation date. A holdings as-of date is
kept distinct from filing, publication, retrieval, and download dates.

## Fact classes

Each conclusion is labeled as one of:

- **Audited fact:** produced by executed code against the read-only archive, or
  directly supported by a primary-source locator.
- **Proxy indication:** useful for screening, but not exact assignment.
- **Maintained assumption:** required for a possible later design and not
  established here.
- **Unexecuted or blocked:** a requested test could not be run; the reason and
  minimum resolving input are recorded.
- **Design failure:** available evidence directly contradicts a required design
  feature, rather than merely being unavailable.

## Non-equivalences enforced throughout

- a scheduled check is not a realized treatment;
- a public reference date is not necessarily a public-information date;
- one policy change affecting many sectors is not many independent shocks;
- repeated issuer appearances are not independent assignments;
- daily MIDAS is not intraday quote or trade data;
- total shares outstanding are not daily ETF creation/redemption flows;
- index returns, industry membership, and constituent membership are different
  data objects;
- a source-availability failure is not evidence that the economic mechanism is
  absent.
