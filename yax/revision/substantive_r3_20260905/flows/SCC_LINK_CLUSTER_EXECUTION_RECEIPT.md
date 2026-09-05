# SCC execution receipt: flow person/household score clustering

* SCC job: `7469212` (`yax_r3_flow_clusters`)
* Queue/host: `bstats-pub` / `scc-mf2.scc.bu.edu`
* Submitted: 2026-09-05 11:38:36 SCC scheduler time
* Started: 2026-09-05 11:40:03
* Ended: 2026-09-05 11:43:30
* Slots: 2
* Wall time: 207 seconds
* CPU time: 215.680 seconds
* Maximum virtual memory: 11.141 GB
* Scheduler status: `failed=0`, `exit_status=0`
* Execution commit: `4953edc4908508c2f88adc403ca8adf893263f1a`
* Amendment commit: `0501a789196c9a91d69e6a4c24484180764567c8`

The job rebuilt all ten official-weight core-flow estimators, reproduced every
stored coefficient to at most `8.33e-17`, and reproduced the saved
finite-corrected occupation influences to at most `1.00e-16`. Maximum event-
weight conservation error was `5.96e-08` on totals measured in survey-weight
units. The SCC and transferred local self-checks both passed all 17 checks.

The scheduler log is `SCC_JOB_7469212.log` (SHA-256
`9b4e21368690b6bcf55a36858ce7509f5d95d7b6b6d8327671f376f26ec8c5d2`).
The transferred `SELF_CHECK.json` has SHA-256
`6b344ecffb29ebdca8ddb4c645f15ce15e83e39e1272f95dcea788a117388741`.
Only aggregate cluster counts, standard errors, intervals, MDEs, and
conservation diagnostics were written. Person, household, and event
identifiers remain outside git.
