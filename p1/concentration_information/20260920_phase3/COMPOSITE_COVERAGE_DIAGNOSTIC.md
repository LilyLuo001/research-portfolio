# Post-contract composite coverage diagnostic

`MEASUREMENT_CONTRACT.md` and `measurement_config.json` were frozen for four venue-specific feeds before response access. `EQUS.MINI` was discovered afterward and is **not** silently added to that contract.

The one July `EQUS.MINI` request is a source-coverage diagnostic only. Official Databento documentation describes it as an anonymized, derived multi-venue aggregated BBO, not a full-market SIP NBBO. API range validation rejected the January event because history begins 2023-03-28. The July file's first record is 07:00:01 ET, after the 06:00 technical anchor, so all 20 baseline responses are unavailable. No composite response estimate enters a scientific table or decision.

Any future use of this source for responses requires a prospective contract amendment, source-semantic review, synthetic fixtures, and a new pilot before analysis.

