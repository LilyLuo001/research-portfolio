# Evidence contract

Gate 1 asks whether a later measurement pilot is worth the next research
investment. It does not estimate the paper's headline outcome and it does not
promote a convenient proxy into an assignment variable.

## Shared key

Every machine-readable output begins with `evidence_key`. Keys are stable
within a table and carry a type prefix:

- `LOCAL:` — physical archive inspection;
- `FUND:` — fund identifier or coverage audit;
- `RULE:` / `SOURCE:` — public institutional source or rule regime;
- `EVENT:` — potential or realized intervention;
- `DOSE:` — assignment record;
- `FOMC:` / `SUPPORT:` — common-news date or event intersection;
- `DESIGN:` — comparison/interference diagnostic;
- `GAP:` — unresolved input or design requirement.

Cross-table relationships use explicit fields such as `event_id`, `source_id`,
and `dataset_id`; an evidence key is not overloaded as a foreign key.

## Assignment grades

- **A:** exact official historical assignment, or a defensible reconstruction
  from complete contemporaneous inputs with reconciliation.
- **B:** an independently documented binding event, but a full precise dose
  vector or reference inputs are incomplete.
- **C:** a screening proxy only, such as an ETF holdings snapshot or approximate
  capitalization.
- **U:** unknown or inaccessible evidence. `U` is never recoded as nonbinding.

Only grade A is eligible for a future exact-dose design. Grade B may support a
narrow event-level design if its estimand is stated accordingly. Grade C is a
search aid, not treatment. Missing numbers remain blank rather than being
renormalized, interpolated, or guessed.

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
