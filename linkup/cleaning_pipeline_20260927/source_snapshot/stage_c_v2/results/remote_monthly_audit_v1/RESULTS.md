# Remote support-table calendar audit

Job `123127202` completed successfully in 39 seconds and conserved all 304,916,642 rows across 64 files. All START_DATE values parsed. The parsed range is 2007-11-08 through 2026-09-05.

- 304,579,947 rows (99.890%) start in 2024 or later; 2024 alone contains 246,068,651 rows. Earlier dates exist but are sparse (336,695 rows before 2024).
- REMOTE_STATUS=true: 24,566,344 (8.057%); false: 280,350,298 (91.943%). False means not tagged remote, not confirmed onsite.
- REMOTE_DETAIL counts: NULL=282,075,861, Remote=7,855,518, Hybrid=7,523,169, blank=7,462,094.
- These are support-row interval starts. They do not turn membership matches for older job CREATED cohorts into historical remote labels.
