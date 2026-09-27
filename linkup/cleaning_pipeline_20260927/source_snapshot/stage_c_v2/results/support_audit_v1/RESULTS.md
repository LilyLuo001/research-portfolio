# Support-table audit results

Job `123126482` completed successfully in 20m11s. It audited 62 O*NET files (356,299,258 rows), 64 remote files (304,916,642 rows), and the validated Records index without persisting a full-width join.

- USA Records denominator: 253,210,047.
- O*NET: 356,299,258 distinct keys, 0 duplicate-key jobs, 0 multi-code conflicts, and 4,651 jobs without a nonempty code. USA key coverage is 253,127,252/253,210,047 (99.9673%); nonempty-code coverage is 99.9659%. Code-format conformity does not validate an O*NET release or historical classification.
- Remote: 304,916,642 rows for 295,654,306 distinct keys; 9,183,333 keys have multiple rows and 8,888,797 have multiple observed label combinations. USA membership is 202,888,939/253,210,047 (80.1267%). This is table membership by job CREATED cohort, not historical remote-label coverage.
- Dates: 295,654,306 open/missing ends, 0 invalid starts, 0 invalid ends, 0 negative intervals, 0 strict overlaps, and 79,003 boundary-touching intervals. Open intervals were kept separate.
- `REMOTE_STATUS=false` means the row is not tagged remote; it does not prove onsite work. Multiple labels on a job can be sequential changes rather than conflicts.
