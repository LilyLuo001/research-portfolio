# S05 authoritative SCC execution 7490033

- Commit executed: `f28d883fcb9600bed1ae4cb82f68174ebe237ef5`
- Scheduler job: `7490033`
- Queue/host: `academic-pub` / `scc-gf4.scc.bu.edu`
- Exit state: `failed=0`, `exit_status=0`
- Wall time: 92 seconds
- Maximum virtual memory: 3.009 GB
- Public result: `yaxresult_v1_1004bccbdbd1827c6be03507b9faabd5a5564ec975a2e015ed5d7ca2c16c7bdb`
- Imported result directory: `runs/gate2_broader_support_authoritative_20260908/`

Two earlier attempts are not result evidence. Job `7489942` stopped while
importing SciPy because the node lacked the required GCC runtime. Job `7489971`
then stopped at the A1 numerical interface because the functional-key namespace
was wrong. Both stopped before publishing any result package. The latter also
exposed and led to a regression test for the required
`original_treatment::...` namespace. The successful job used the unchanged
scientific specification, the corrected runner, and the GCC 12 runtime already
used by the certified numerical environment.
