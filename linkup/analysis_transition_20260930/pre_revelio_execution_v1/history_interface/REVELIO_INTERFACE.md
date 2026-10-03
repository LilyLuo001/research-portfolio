# Revelio pre-event experience interface

Status: **design complete; actual Revelio schema unverified and no Revelio data processed**.

This interface preserves the frozen categories in `research_contract_v1/common_measurement.json`. Every field named in `REVELIO_INTERFACE_CONFIG.json` is a desired semantic field, not a claim about a vendor column name. The first operation after files arrive is a schema-and-cardinality audit that maps actual columns to these meanings and records coverage; missing concepts stay missing.

## Event construction

The event clock is a position start date or month. Construct three event types: external employer entry, internal occupation transition, and same-occupation employer change. Experience evidence must be strictly before the event. When month-level dates cannot order evidence within the same month, mark the ordering unresolved rather than treating the evidence as prior. An ongoing prior position is truncated at the event boundary.

Duplicate and overlapping positions are resolved into time intervals before duration calculation. General work experience is the union of all observable pre-event employment intervals. Occupation/task, industry/domain, and specific-tool durations each take the union of qualifying intervals within that dimension, so concurrent jobs never double-count calendar time. Internships are reported separately.

Left-censored careers retain the observed pre-event duration as a lower bound and carry a censoring flag. They are not assigned zero experience. Current profile skills cannot be projected backward. Education is usable only when its timing shows that the credential was completed or underway by the event.

## Evidence required by experience object

| frozen object | qualifying historical evidence | exclusions |
|---|---|---|
| `general_work` | dated prior position interval | education-only time; unobserved pre-history |
| `occupation_task` | position title/occupation or dated position text mapped to the occupation family or a supported related task family | present-day occupation labels silently backfilled to earlier jobs; undated profile skills |
| `industry_domain` | industry attached to the employer-position interval, valid at that time | current employer industry copied to all past jobs without a dated mapping |
| `specific_tool` | dated position-linked text or another time-stamped source naming the tool | current skill lists without historical timing; generic technology exposure scores |
| `object_unspecified` | evidence exists but cannot be assigned safely | forced assignment to one of the four substantive objects |

The frozen task families are execution/information processing, analysis/judgment, verification/accountability, coordination/communication, and other/unknown. A task-family crosswalk needs source text or an occupation mapping with recorded provenance; the interface does not treat occupational similarity as proof of identical tasks.

## Cross-dataset alignment and denominators

The common aggregation cell is harmonized employer × occupation family × region × calendar quarter. LinkUp contributes eligible deduplicated JOB_HASH/URL records; Revelio contributes eligible person events. This supports distributional alignment and overlap diagnostics, not a claim that a particular advertisement produced a particular hire.

Start from all events meeting an event definition. Report the share mapping to all four common-cell dimensions. Unmapped events remain in coverage tables and are excluded from common-cell contrasts. For each experience object, the denominator is mapped events with adequate pre-event observation. A zero is allowed only when observation is not left-censored and the evidence source can support absence; censored, insufficient, and unresolved histories remain separate. Experience objects are multi-label, so their shares need not sum to 100 percent.

Calendar-quarter matching is a structural interface, not yet permission to align historical demand and hiring. With delivery-snapshot-only LinkUp text, CREATED remains a URL first-observation cohort; it cannot be treated as the requirements faced by same-quarter entrants. Historical demand-flow contrasts require independent text-time evidence. The current frozen LinkUp enrichment does not measure occupation/task experience as a separate category (D10); that side remains unavailable even if Revelio later supports it.

A modern harmonized occupation classification may be applied to genuine historical job titles with documented provenance; the prohibited backfill is use of later job content or a person’s current occupation as evidence about earlier jobs.

Compare LinkUp and Revelio only over cells supported on both sides. No Revelio-specific numeric support threshold is frozen before actual coverage is known. The existing LinkUp comparison thresholds remain governed by the execution plan; this interface does not alter them.

## Arrival gate

Before analysis, record actual file names and hashes, row and key cardinalities, date precision and coverage, duplicate position behavior, employer/title/location/industry mapping rates, and whether descriptions and skill evidence are historically dated. Verify that person and position identifiers are stable and that joins do not expand event counts unexpectedly. Only then bind vendor columns to the semantic config and freeze support rules.

This stage does not estimate hiring probability, experience returns, worker flows, or causal effects. It also cannot repair LinkUp's historical-text limitation.
