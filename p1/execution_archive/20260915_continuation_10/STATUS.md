# P1 continuation 10 — source-authority inquiry packet

Date: 2026-09-15

Decision: **HOLD_DATA — PROVIDER CONFIRMATION REQUIRED**

Checkpoint 09 established that the frozen W021 RTH/RTH-60 necessary-support
verdict flips with the interpretation of `ibes.actu_epsus.anntims`: Eastern and
fixed EST fail, while UTC passes the necessary Stage-A count. This continuation
performed the one remaining source-authority search rather than starting quote,
rank, power or outcome analysis.

## Completed checks

- Rechecked the updated SCC data manual. It explicitly says the timezone of
  `anntims` was not verified during harvest and prohibits intraday conversion
  without official I/B/E/S/WRDS documentation or external validation.
- Rechecked the archived manufacturer-guide findings. They support seasonal
  Eastern/DST for a 2013 direct-delivery context and distinguish announcement
  from activation fields, but do not bridge that convention to the harvested
  WRDS `actu_epsus` delivery over the full frozen manifest.
- Searched public official WRDS/LSEG material for the exact field bridge.
  Available LSEG guidance shows that timezone can depend on the delivery/API
  field and directs content-definition questions to the provider helpdesk. It
  does not certify the SCC fields.
- No authoritative statement was found for first-public versus receipt/
  activation meaning, minute precision/rounding/imputation, or revision rules.

## Result

`NO_DECISIVE_WRDS_LSEG_BRIDGE_FOUND`. This is not evidence for either Eastern or
UTC. The formal status remains `HOLD_DATA`, and checkpoint 09's conditional
decision tree remains unchanged.

## Single next action

Submit the prepared four-question inquiry in
`artifacts/w021_clock_authority_20260915/PROVIDER_INQUIRY.md` to the WRDS/LSEG
content helpdesk and save the authenticated answer with ticket/date/version.
No further quote purchase or power analysis should begin before that answer is
applied to the frozen 1,082-key classifier.
