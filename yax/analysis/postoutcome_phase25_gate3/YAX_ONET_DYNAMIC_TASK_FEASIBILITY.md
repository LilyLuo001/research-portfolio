# YAX Pilot A — O*NET Dynamic Task-Vintage Feasibility

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## Classification: ONET-B

A longitudinal task panel is feasible only for a restricted occupation subset and
with release/update-method controls. The official archives are much better structured
than a text-scraping exercise, but they do not support an unrestricted 2017–2026
within-occupation interpretation.

## Audit scope

The audit reads all 37 official O*NET text-database releases from 22.0 (August 2017)
through 31.0 (August 2026). It compares task IDs, exact and normalized task text,
task type, importance and relevance ratings, file-level update dates, and domain
sources. Release dates are kept separate from the `Date` metadata in Task Statements
and Task Ratings. Archive hashes are in `YAX_ONET_DYNAMIC_TASK_EXECUTION_RECEIPT.json`.

## Identity and revision behavior

Task IDs are stable within an exact O*NET-SOC code. Across adjacent releases, 1,038
same-code/same-ID statements change wording while retaining their ID. Apparent
renumbering of identical normalized text occurs only 25 times and is concentrated in
the 25.0→25.1 taxonomy transition. Most quarterly releases contain no task-statement
change; substantive task/rating refreshes concentrate in annual `.0` releases.

The 2020 taxonomy transition is not ordinary task evolution. It deletes 252 codes and
adds 201, mechanically producing 4,740 occupation-task additions and 5,244 deletions;
2,051 identical task-ID/text lineages reappear across deleted and added codes. Exact-
code longitudinal work must either remain on the stable taxonomy subset or use a
separately validated taxonomy bridge.

## Repeated observations

Across both taxonomies the archive contains 1,175 exact codes; 923 are in the current
taxonomy and 722 appear in all 37 releases. Among the 923 current codes:

- 839 have at least two distinct task-domain snapshots and 447 have at least three;
- 811 have at least one task-content change and 405 have at least two;
- 464 have at least one pre-2022 and one post-2022 genuine snapshot; and
- only 267 have multiple pre-2022 snapshots plus a post-2022 snapshot.

Positive gaps between metadata-dated genuine updates have a median of 97 months
(interquartile range 85–121). This slow rotation is the binding limitation. A 267-code
restricted sample can supply an occupation-specific historical baseline; the full
occupation universe cannot.

## Measurement timing and methodology

The metadata are sufficient to distinguish the database release month from the task
data update month and source. Observed sources include Incumbent, Occupational Expert,
Analyst, and transition combinations. But a changed archived snapshot is not always
economic task change: examples include the 25.1 taxonomy migration, 28.3 language
revisions, the 29.0 relevance-retention threshold change, and source/method changes.
Those events must be indicators or exclusions in any future design.

The deterministic 12-occupation pilot in `YAX_ONET_TASK_ID_STABILITY.csv` demonstrates
that additions, deletions, wording turnover, importance changes, and relevance changes
can be calculated reproducibly. Importance and relevance are reported separately on
their native scales; no mixed-scale change index is constructed and no change is
labeled AI-driven.

## Decision

`ONET-A` is rejected because the historical baseline and post-2022 refresh are not
broadly observed and the taxonomy/method changes are consequential. `ONET-C` is also
too pessimistic: 267 current occupations satisfy the strict multiple-pre plus post
criterion, task IDs are largely stable, and actual update dates/sources are recorded.
The correct verdict is `ONET-B`.

A future pre-analysis design could freeze the 267-code eligible set, require exact
task IDs within stable occupation codes, model importance and relevance separately,
include update-source and known release-rule indicators, and compare post-2022 changes
with each occupation's pre-2022 revision history. This pilot stops before any CPS merge
or labor-outcome relationship.

Official documentation: [release archive](https://www.onetcenter.org/db_releases.html),
[Task Statements dictionary](https://www.onetcenter.org/dictionary/30.0/text/task_statements.html),
[Task Ratings dictionary](https://www.onetcenter.org/dictionary/28.1/text/task_ratings.html),
[publication schedule](https://www.onetcenter.org/ombclearance.html), and
[task-updating procedures](https://www.onetcenter.org/reports/TaskUpdating.html).
