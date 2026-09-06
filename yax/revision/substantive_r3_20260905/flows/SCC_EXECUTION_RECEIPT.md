# SCC execution receipt: corrected flows and worker outcomes

## Model execution

* SCC job: `7469141` (`yax_r3_flows`)
* Scheduler queue/host: `bstats-pub` / `scc-mf1.scc.bu.edu`
* Submitted: 2026-09-05 11:03:32 SCC scheduler time
* Started: 2026-09-05 11:04:14
* Ended: 2026-09-05 11:07:01
* Slots: 2
* Wall time: 167 seconds
* CPU time: 238.416 seconds
* Maximum virtual memory: 13.685 GB
* Execution commit recorded by the result generator:
  `3f760f6e537f124636c8b881c952d4cb507db120`

The runner completed all 35 fixed models and wrote zero model failures. The
machine-readable receipt records the restricted-input hashes, public-input
hashes, output hashes, link counts, route diagnostics, seed, and draw hashes.
The restricted files remain outside git.

## Wrapper exit and corrected self-check

The scheduler records `failed=0` and `exit_status=1`. This nonzero wrapper exit
occurred after all models and result hashes were written. The original
self-check required the literal phrase `employer hire`, while the limitations
memo correctly used `employer hiring` and separately stated that the CPS has no
employer identifier. The resulting assertion is visible in
`SCC_JOB_7469141.log` (SHA-256
`70d0a50efd922f55d31e51de07d03370878463211285e620dc44acc33f71ab11`).

Commit `5274ff0` narrowed the text check to require both the concepts
`employer` and `hiring`; it did not alter data, models, estimates, intervals, or
result hashes. The corrected verifier was rerun directly against the existing
SCC output and again after transfer. Both runs passed all 135 checks. The
transferred `SELF_CHECK.json` has SHA-256
`32b304554b6464d5ffd16dced6e5ed483c3fee498aa237bc5d74199518447cbe`.

## IPUMS weight patch

Authenticated IPUMS extract 12 supplied only the identifiers and official
longitudinal weights needed to repair the corrected 114-sample calendar. The
sanitized request receipt is `CORRECTED_WEIGHT_PATCH_REQUEST.json` (SHA-256
`c052b5a536b110d8baf3cfa1b36dc0ab647de2fe3f213153dc8532618fa11ae1`).
Its data hash is
`bc97f807eace1bf3f0ca04b09e6a9d099bf1c86433c56bb1edd08b4156ac9fd6`;
the data itself is not in the repository.
