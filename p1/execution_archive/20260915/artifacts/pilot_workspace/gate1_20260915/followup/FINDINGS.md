# Bounded follow-up — historical Class B and announcement clock

2026-09-15. **Gate 1 remains HOLD_DATA; no identification or power result claimed.** This follow-up addresses the two named gaps without repeating the project review. No additional agents were launched; deterministic metadata projections and checks were used. No data was purchased, no full DBN hashes computed, and no POST response was decoded.

## 1. CRD failure explained, isolated repair prepared

The original `scc_build_supported_earnings_inputs.py` (approximately lines 180–215) reads historical `ticker/cusip` but not `shrcls/tsymbol`, then renames `ticker` to `date_valid_raw_symbol`. A unique basic ticker is therefore mislabeled as a verified vendor-native symbol.

The new SCC projection checked the historical CRSP name intervals against all 852 announcement dates: 852 matched, no multiple active intervals, and 852 CUSIPs agreed. For the 12 CRD associations, the same PERMNO/CUSIP is consistently **Class B**, not Class A. Historical row-level evidence remains in SCC's `gate1_followup_20260915/licensed_identity_intervals.csv`; the exported receipt contains aggregate checks.

[Databento historical symbology documentation](https://databento.com/docs/standards-and-conventions/symbology) distinguishes Nasdaq and CMS conventions. Applying those conventions to the verified class gives these **proposed, not yet API-validated** symbols:

| Dataset | Proposed native symbol |
|---|---|
| XNAS.ITCH | `CRD.B` |
| BATS.PITCH | `CRD.B` |
| ARCX.PILLAR | `CRD B` |
| XNYS.PILLAR | `CRD B` |

This explains why bare `CRD` failed while accompanying symbols could still download. It does not establish that corrected-symbol records exist on every date. The historical API's venue-specific convention must not be confused with the Reference API's standardized convention.

`CRD_CLASS_B_REPAIR_REQUESTS.csv` contains **192 isolated single-stock windows, 48 per feed**, traced to the original grouped jobs. Of these planned symbol-window instances, 191 had NOT_FOUND and one was in an excluded quote-failed job. They are prepared requests, not downloaded files or new observations. They contain no SPY or other already-acquired symbols, avoiding unnecessary repeat downloads. Originals are unchanged.

`FREE_SYMBOLOGY_QUERIES.json` and `resolve_free_symbology.py` prepare four metadata-only symbol-resolution calls covering the existing date span. Installed Databento SDK compatibility was checked against the callable signature. Execution returned **NOT_RUN_AUTH_ENV_ABSENT**: neither the current local nor noninteractive SCC environment has `DATABENTO_API_KEY`. No credential store or earlier chat credential was read or copied. This is an authentication-state limitation, NOT proof of unavailable historical data. No charged endpoint exists in this runner.

The four previously identified quote-transport failures remain separate. This turn did not silently retry, order or mark them repaired. The three earlier interrupted downloads remain recovered as already verified.

## 2. Actual-source timestamp projection checked

The SCC custodian script projected ONLY `permno,cusip,pends,pdicity,anndats,anntims,actdats,acttims` from the already selected actuals parquet. It did not request the `value` column or any forecast, price or return values. Row-level results remain on SCC.

| Check | Result / denominator |
|---|---:|
| Actual-source metadata rows and matched associations | 852 / 852 |
| `pdicity=QTR` | 852 / 852 |
| Announcement date agrees with current selected manifest | 852 / 852 |
| Announcement time agrees with current selected manifest | 852 / 852 |
| Nonzero seconds in `anntims` | 0 / 852 |
| `00:00:00` sentinel | 0 / 852 |
| Activation date equals announcement date | 796 / 852 |
| Activation date later than announcement date | 56 / 852 |
| Activation date before announcement date | 0 / 852 |

Thus the extraction preserved the selected source clocks; there is no detected date/time transcription mismatch. All timestamps lie on minute boundaries, but this does not establish their rounding rule or true precision. Activation and announcement are different fields and must not be substituted, even where their dates match. Having one quarterly source row is still not a complete certification of economic-event identity or public-release timing.

The original data manual explicitly says the timezone was not verified at harvest (lines 730–734); the saved event-clock dictionary likewise marks it unverified. The [LSEG actuals overview](https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/actuals) distinguishes announcement, effective and activation dates but does not specify the WRDS `actu_epsus.anntims` timezone/rounding contract. An [LSEG community response](https://community.developers.lseg.com/discussion/78942/i-b-e-s-timestamps-in-which-time-zone) discusses a per-field timezone attribute for **Eikon forecast timestamps**, not this WRDS actuals field; it is not sufficient authority to assume ET, fixed EST or UTC here. No session, RTH-60 or five-minute eligibility was inferred from those other products.

## 3. Exact next input / execution handoff

The binding scientific input is a source-specific answer for **WRDS `ibes.actu_epsus`, unadjusted quarterly US EPS actuals, 2019–2024: `anndats/anntims`**. Obtain the provider dictionary/helpdesk confirmation specified in `CLOCK_SOURCE_QUESTION.md`, or independently sourced publication-time evidence for the fixed events. That request is prepared locally, not sent externally. Do not ask the PI to resupply a stock roster or sign an entire new research contract.

Once that clock evidence exists, version the timestamp uncertainty policy and execute a small golden PRE measurement test before the broader six-horizon stock/SPY mask census. Do not decode POST responses or select a clock by price movement. Session classification and endpoint precision must remain separate acceptance checks.

Independently, after the already configured runtime exposes `DATABENTO_API_KEY`, the single command below executes only four free symbology calls:

```sh
/Users/lilyluo/databento_preflight_20260914T043849Z/.venv_runtime/bin/python /Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot/gate1_20260915/followup/resolve_free_symbology.py
```

A successful symbol response is not authority to download. Exact isolated repair quotes and current budget authority must be checked before a charged repair. No new full acquisition round is needed.
