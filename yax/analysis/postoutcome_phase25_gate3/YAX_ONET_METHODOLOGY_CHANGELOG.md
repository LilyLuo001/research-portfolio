# YAX O*NET Task-Vintage Methodology Changelog

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

This changelog separates observed archive changes from occupational task evolution.
It is not a claim that every affected occupation changed for methodological reasons.

| release/event | documented or observed change | implication for a task panel |
|---|---|---|
| 22.0–31.0 | Official primary task/rating refreshes are concentrated in annual releases; quarterly archives are cumulative snapshots. | Release count is not observation count. Collapse identical fingerprints and use item metadata dates. |
| All releases | Task Statements and Task Ratings contain a `Date` and `Domain Source`; observed task sources include Incumbent, Occupational Expert, Analyst, and transition combinations. | Keep release month distinct from collection/update month and control or stratify by source. |
| 25.1 (Nov. 2020) | O*NET moved to O*NET-SOC 2019, based on the 2018 SOC. The archive audit observes 252 deleted and 201 added codes, with 2,051 identical task-ID/text lineages crossing those code changes. | Do not interpret taxonomy-driven additions/deletions as task reorganization. Use stable exact codes or a validated bridge. |
| 28.2 (Feb. 2024) | Standard-error and confidence-bound metadata precision expanded from two to four decimals. | Rating point values remain comparable; metadata precision is not a task change. |
| 28.3 (May 2024) | Official notes report wording revisions for 39 occupations to update language related to people with disabilities; the audit finds 44 same-ID wording revisions. | Flag this release as editorial/methodological text turnover. |
| 29.0 (Aug. 2024) | The minimum task relevance for retention rose from 10% to 25%, affecting 466 statements in another 228 occupations in addition to refreshed occupations. The audit observes 503 task deletions. | Task deletion at this boundary is mechanically confounded; exclude or explicitly indicator this release. |
| 29.3 (May 2025) | Emerging drone tasks used a new AI/SME source, including a ChatGPT-assisted identification procedure. | Emerging Tasks must not be pooled silently with rated Task Statements; source is part of the construct. |
| 30.1 (Dec. 2025) | Official notes report one task list revised by analyst review. | Analyst-only edits are distinguishable through source/release metadata. |
| 30.3 (May 2026) | The O*NET content model and several file/column names were modernized. The archived Task Statements themselves are unchanged from 30.2 in this audit. | Broader schema migration needs a file crosswalk, but it is not evidence of task-content change in this pair. |
| 31.0 (Aug. 2026) | Official notes report task-rating additions/updates for 205 occupations. The audit observes 134 statement additions, 92 deletions, and widespread rating changes. | This is a genuine new measurement wave, but collection-source and long refresh intervals remain part of interpretation. |

O*NET states that current profiles draw on multiple sources and that subsets can be
updated at different times. The publication schedule reports roughly 78–208 incumbent/
expert occupations in each 2017–2026 primary release, not a balanced annual panel.
The program's official task-writing procedure also includes research, review, revision,
and online-source use, so wording turnover is not a pure behavioral measure.

Sources:

- [Official database release archive](https://www.onetcenter.org/db_releases.html)
- [Official release notes through 30.3](https://www.onetcenter.org/dictionary/30.3/text/appendix_updates.html)
- [Official 31.0 release notes](https://www.onetcenter.org/dictionary/31.0/excel/appendix_updates.html)
- [Official data publication schedule](https://www.onetcenter.org/ombclearance.html)
- [Official data-collection overview](https://www.onetcenter.org/dataCollection.html)
- [Official task updating/new-task procedure](https://www.onetcenter.org/reports/TaskUpdating.html)
