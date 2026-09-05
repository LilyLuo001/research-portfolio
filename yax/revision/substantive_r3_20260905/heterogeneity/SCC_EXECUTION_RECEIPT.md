# SCC execution receipt

All compute ran under `/project/econdept/qluo/yax-substantive-revision-20260905`; existing private inputs under `/projectnb/econdept` were read-only. No existing job or shell session was terminated.

| Job | Purpose | Exit | Wall time | Max memory | Result |
|---|---|---:|---:|---:|---|
| 7469239 | first environment attempt | 1 | 2 s | 451.371 MB | failed at `scipy.stats` import before any data access; preserved |
| 7469259 | dependency-corrected full estimation | 0 | 57 s | 2.023 GB | 12 models, 10 paired contrasts, 65/65 checks |
| 7469280 | traceability/multiplicity reporting rerun, no estimator change | 0 | 66 s | 2.034 GB | same estimates plus explicit memberships, coverage, simultaneous paired intervals; 81/81 checks |

Final execution host: `scc-gr4.scc.bu.edu`. Final start/end: 2026-09-05 12:09:45--12:10:51 EDT. The public receipt records only restricted-input basenames and SHA-256 hashes; no private path or credential is embedded. Logs are in `logs/`, and the permanent chronology is in `EXECUTION_HISTORY.md`.

The archived 7469259 checkpoint log retains the preceding import-failure traceback at its head before the successful 65/65 block. The separate failed-job log and scheduler accounting disambiguate the attempts; 7469280 is the clean final 81/81 execution log.

Input SHA-256:

- wide microdata: `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9`
- March repair microdata: `a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911`
- occupation bridge: `0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc`
- rebuilt treatment membership: `c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1`
- pre-results specification: `f903bf947d4df8308fe1751457a81d7b16b281f294151511f1efc18a066d8516`
- final analysis script: `8985b044ae8d02f9ee496da41f74e62a870b00fd34c6112a32e0746e9939831a`

The final `results/EXECUTION_RECEIPT.json` authenticates every result file. Local re-verification passed all 81 checks after transfer, and the five construction unit tests pass.
