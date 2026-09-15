# P1 strict necessary-support analysis

Date: 2026-09-15  
Decision: **HOLD_DATA**  
Scope: fixed MF-to-ETF pilot design; outcome-blind metadata only.

## Result

The analysis has reached the plan's Step-4 early-stop branch. It is not valid to
run quote measurement, the realized design matrix, or power simulations yet.
This is not because the repaired W021 sample is empty. W021 has a valid
pre-announcement exposure roster and strong analyst coverage, but none of its
candidate release records is currently certified as RTH or RTH-60 under the
frozen session contract. The updated data manual expressly says that the
timezone interpretation of `anntims` was not verified during harvest.

W002 supplies a separate negative result: the only currently proposed-clean
high-tier candidate has three PRE and one POST release keys, and neither the
DIRECT nor the independently retained RESCUE_ADJUSTED complete SCC source
family contains a key with at least two analysts. Each family finds one zero
key and three one-analyst keys. Removing `usfirm=1` does not change the result.
This candidate therefore cannot support the present W002 high-versus-low
comparison. Other W002 candidates whose competing-conversion status is still
unknown are not silently classified as failures.

## Necessary-support matrix

| Gate | Evidence | Status |
|---|---|---|
| W021 pre-announcement dose | 39 date-valid US common stocks with active same-date share denominators; frozen H/M/L counts 13/13/13 | PASS |
| W021 H PRE analyst support | 182/198 release keys have at least two analysts; all 13 high-tier stocks represented | PASS |
| W021 H POST analyst support | 109/124 release keys have at least two analysts; 12 high-tier stocks represented | PASS |
| W021 L PRE analyst support | 205/208 release keys have at least two analysts; all 13 low-tier stocks represented | PASS |
| W021 L POST analyst support | 113/122 release keys have at least two analysts; all 13 low-tier stocks represented; one additional implementation-date-boundary key remains UNKNOWN | PASS for analyst coverage only |
| W002 proposed-clean H PRE/POST analyst support | 0/3 PRE and 0/1 POST keys reach two analysts in either complete SCC family | VERIFIED FAIL for that candidate |
| W021 RTH/RTH-60 classification | Source display time exists, but WRDS `actu_epsus.anntims` timezone/session bridge remains uncertified | UNKNOWN / blocking |
| W021 competing-conversion screen | Repaired 39-stock roster has not been fully joined to a complete conversion calendar | UNKNOWN / blocking |
| Common six-horizon quote mask | Not evaluated because the required session gate failed | NOT RUN |
| Rank, size, MDE and power | Would condition on an uncertified event clock and population | EARLY STOP / NOT RUN |

The W021 analyst figures are reproduced identically by DIRECT and
RESCUE_ADJUSTED families and by the EPS-base and `usfirm=1` diagnostic rules.
Across all 1,082 W021 release keys, 1,033 reach at least two analysts, 23 have
one, and 26 have zero. These are accounting-period/public-release keys, not
claims of statistically independent shocks.

## Identification and power interpretation

No supported identification or adequate-power claim follows yet. The intended
RTH price-discovery estimand requires a verified release instant relative to the
historical exchange session. Treating nominal `anntims` as Eastern time would
be an undocumented specification amendment. Running power on that assumption
would quantify a different, unapproved design and could materially overstate
usable event support. The failure of one W002 candidate also shows that quote
purchases cannot repair every missing comparison cell.

This evidence does not establish NO_GO for all MF-to-ETF conversions. It shows
that the current fixed pilot is not ready for rank or power analysis, while
W021 remains worth rescuing because its pre-announcement roster and analyst
support are strong.

## Single next action

Produce one versioned, outcome-blind W021 clock projection for the 1,082 fixed
release keys that records the authoritative timezone/semantics of
`anndats/anntims`, a bounded timestamp uncertainty interval, the historical
XNYS open/close, and resulting RTH/RTH-60/UNKNOWN flags. Use provider
documentation or event-specific issuer/wire timestamps where the provider
bridge cannot be established. Do not read prices, returns, forecasts, EPS, or
POST responses. If this projection yields nonempty H/L PRE/POST common-session
support, return to the remaining Step-4 competing-conversion,
common-calendar-cell and control-availability checks. Quote coverage may begin
only after those checks pass; the realized numerical design matrix follows
permitted PRE calibration rather than the clock repair itself.

## Reproducibility

- Corrected metadata aggregate SHA-256: `8c1e20a9618a8b44efc059ab7bc6d9530aaa522223563105591e84308b429129`
- Corrected exact-detail aggregate SHA-256: `5bcef73a1391345012e061dc2d5f50527c6866906160c2f4fdf3deaba598bf4c`
- Tier/side analyst aggregate SHA-256: `b90f2bfcfff0af08b5ca6c22ba5c9cb70d3875a5f918fca4a4d0a3c7ab54e07c`
- Raw row-level licensed metadata remained on SCC. No financial values,
  quotations, prices, returns, treatment outcomes, coefficients, or p-values
  were read or exported.
