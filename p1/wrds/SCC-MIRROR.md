# P1 SCC WRDS mirror

**Verified:** 2026-09-03

**Owner manual:** `/Users/lilyluo/Documents/P1_Refraction_WRDS_Data_Usage_Manual.md`

Read-only archive root:

```text
/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902
```

Execution scratch/output used for the current exposure build:

```text
/projectnb/econdept/qluo/P1_Refraction_WRDS/p1_execution_20260903
```

Mirror verification facts from `FINAL_VERIFY_REPORT.txt`: 12,100 source files,
12,100 destination files, 9.913 GiB, zero missing/wrong-size/extra paths, and
`PATH_SIZE_CHECK = PASS`. `FINAL_CHECKSUM_DIFF.txt` has zero lines; the report
does not separately print a literal signed `CHECKSUM_CHECK=PASS`.

Current relevant content:

- date-valid CRSP CIZ stock names;
- legacy CRSP daily security data through 2024;
- CRSP CIZ daily security data for 2025;
- CRSP–IBES link data and I/B/E/S files;
- Compustat security/fundamental files.

There is no full intraday event-window dataset in the mirror, and no CRSP DSF
for 2026. CRSP mutual-fund holdings are validation only; N-PORT remains the
frozen treatment source. I/B/E/S `ANNTIMS` timezone semantics remain to be
verified before outcome construction.
