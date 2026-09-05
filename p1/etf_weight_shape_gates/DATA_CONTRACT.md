# P1 ETF weight-shape data contract

- Contract version: `P1_CRSP_HOLDINGS_TNA_CONTRACT_2026-09-05_V3`
- Status: `FROZEN_FOR_GOLDEN_SAMPLE_AND_PILOT`
- Prior-result status: `INVALIDATED_PENDING_DATA_CONTRACT`
- Pilot status: `PASS` (18/18 invariants; 25/25 private raw traces)
- Full-run status: `DISABLED_PENDING_CONTRACT_CONFORMANT_IMPLEMENTATION`

This Markdown file is an explanatory rendering, not the executable contract. The sole executable normative specification is the hash-bound combination of `data_contract.json`, `gate01_config.json`, and `golden_sample_spec.json`. Those machine-readable files control if any wording here differs. Licensed CRSP/WRDS row values are intentionally excluded from this public narrative.

## Stop boundary

All prior Gate 0/1 outputs and interpretations remain invalidated. They may be retained only as non-canonical audit artifacts. They are not research results and must not be quoted, summarized, compared, or used to make a Gate decision. The passing pilot validates this contract; it does not rehabilitate any earlier output.

Gate 2 must not be launched. No new full Gate 0/1 run may be submitted. The full-run entry point must exit before enumerating, opening, or scanning the archive unless a current, internally consistent `PILOT_PASS.json` exists and passes the preflight in this contract.

This document explains the V3 contract that passed the targeted pilot. A change to any formula, tolerance, date cutoff, mapping rule, counterfactual, identifier definition, or eligibility rule is a specification amendment and invalidates the pilot artifact.

## 1. Separate entities and indices

The following indices are distinct. No implementation may reuse a generic `fund_id`, `permno`, or `date` variable for more than one of them.

| Entity | Canonical derived name | Source identifier(s) | Meaning and prohibition |
|---|---|---|---|
| Pooled portfolio | `portfolio_id` | CRSP `crsp_portno`; SEC series CIK only as external corroboration | Pool of assets whose holdings are reported. It is not a share class and is not a traded ETF security. |
| Share class | `share_class_id` | CRSP `crsp_fundno`; SEC contract CIK as external corroboration | A claim issued against a portfolio. Monthly TNA is keyed at this level. A class can be conventional or exchange traded. |
| ETF security | `etf_security_id` | The ETF's own CRSP Stock `permno`, plus effective-dated ticker/CUSIP and SEC contract CIK | The exchange-traded security held by investors. It must never be inferred from an underlying holding's `permno`, and ticker alone is not an identifier. |
| Underlying position/security | `underlying_position_id` and nullable `underlying_security_id` | Raw-row provenance and `crsp_company_key`; CRSP Stock `permno` where available; otherwise security type, CUSIP, description, coupon, maturity, or other raw descriptors | The asset appearing in the pooled portfolio's holdings. Derivatives, cash, debt, and other non-equity rows may have no Stock `permno` and must not be dropped or assigned a synthetic equity match. |
| Economic date | Field-specific names below | Holdings `report_dt`; monthly TNA `caldt`; summary TNA `tna_latest_dt`; relationship effective date | Date to which the economic quantity or relationship pertains. |
| Availability date | `available_date` | Holdings `eff_dt` where populated | Date CRSP/vendor records say the holding information was received or became effective in the database. It is not the economic date. |
| Availability timestamp | `available_timestamp` | No verified field in the audited CRSP mutual-fund records | Must be null/unknown unless a separately documented raw source supplies it. A filesystem modification time or extraction time is not an availability timestamp. |

Required physical keys are:

- Holdings raw row: raw file hash, raw row number, `crsp_portno`, `report_dt`, and the source row fields including `security_rank` and `crsp_company_key`. The raw file/row pair is the final tie-breaker because a market position can lack a stable security identifier.
- Portfolio-to-class relationship: `crsp_fundno`, `crsp_portno`, `begdt`, `enddt`.
- Monthly class TNA: `crsp_fundno`, `caldt`.
- Fund-summary observation: `crsp_fundno`, `caldt`, with `tna_latest` tied to its own `tna_latest_dt` rather than assumed to refer to `caldt`.
- ETF-security crosswalk: `crsp_fundno`, ETF Stock `permno`, crosswalk start date, crosswalk end date, source, and verification status.

## 2. Date contract

Field-specific dates must be preserved through every join:

| Quantity | Economic date | Availability date/timestamp |
|---|---|---|
| Holding `market_val`, `percent_tna`, and position descriptors | `report_dt` | Row `eff_dt`; snapshot availability is `max(eff_dt)` and its timestamp is unknown |
| Monthly share-class TNA | `caldt` | Unknown unless independently documented; timestamp unknown |
| Fund-summary `tna_latest` | `tna_latest_dt` | Unknown unless independently documented; timestamp unknown |
| Portfolio-to-class link | Date tested against `begdt`/`enddt` | No separate availability field established |
| ETF-security identifier/ticker/CUSIP link | Its own effective-dated interval | Source-specific; otherwise unknown |

Rules:

1. A holdings/TNA identity uses exact economic-date equality: `TNA_date == report_dt`. Nearest, month-end substitution, last observation carried forward, and future observation carried backward are prohibited.
2. The relationship rule for this contract is `begdt <= economic_date <= enddt`, with a missing `enddt` treated as open ended. **Inclusive endpoints are a frozen project specification, not a fact established by the CRSP documentation.**
3. Relationship dating uses the economic date being analyzed, not the file extraction date or `eff_dt`.
4. Because the complete snapshot is not available before its last received row and `eff_dt` has date-only precision, the holdings snapshot is usable only on the first calendar day strictly after `max(eff_dt)` across all rows in that portfolio/report snapshot. It is not usable on `max(eff_dt)` itself, and the data cannot support an intraday availability claim.
5. TNA cannot be used in an availability-sensitive construction until its availability is separately established; its raw economic date alone is insufficient.
6. Market-value reconciliation uses the latest CRSP absolute price whose trading date is on or before `report_dt`; the price is ineligible if it is more than three calendar days earlier. A later price is never used.
7. Two clocks are retained separately: report age is `as_of_date - report_dt`, while publication delay is `max(eff_dt) - report_dt`. Neither may be silently repaired by joining to a later TNA.

## 3. Raw row units and units of measure

### 3.1 Holdings

One holdings row is a position line reported for pooled portfolio `crsp_portno` on `report_dt`. `market_val` is the value of that position line as of `report_dt`; it is not an ETF-share-class AUM and is not already aggregated across duplicate security lines.

The CRSP guide does not print an explicit currency scale beside `market_val`. For this contract its unit is U.S. dollars because raw-record validation reproduces sampled equity-row values from shares times the latest eligible CRSP price on or before `report_dt`, subject to the three-calendar-day limit in Section 2. This is a documented-plus-raw interpretation, not a claim that the unit label itself appears in the guide. No multiplication by one million is applied to `market_val`.

`percent_tna` is expressed in percentage points and has this denominator:

```text
the total net assets of the pooled portfolio identified by crsp_portno
on the holdings report_dt
```

The weight unit used in calculations is:

```text
w_reported[p,i,t] = percent_tna[p,i,t] / 100
```

It is not an ETF-class weight with ETF-class TNA as its denominator. Raw `percent_tna` is never re-normalized to make retained rows sum to one. Cash, derivatives, debt, missing-`permno` rows, shorts, and other non-equity positions remain in the raw audit universe.

### 3.2 TNA

CRSP monthly TNA is keyed by `crsp_fundno` and `caldt`, and is stored in millions of U.S. dollars. It is therefore share-class-level in the raw table. Convert it as:

```text
class_tna_usd[j,t] = class_tna_millions[j,t] * 1,000,000
```

Portfolio TNA is a derived same-date sum, never a raw share-class observation:

```text
portfolio_tna_usd[p,t]
    = 1,000,000 * sum(class_tna_millions[j,t])
      over the complete, unique set of classes j validly mapped to p on t
```

The sum is eligible only if all of the following hold:

- the portfolio-to-class mapping is valid on `t` under the frozen interval rule;
- duplicate mapping rows have been resolved without double counting;
- every mapped economically active class has an exact-`t` TNA observation or is affirmatively documented as not outstanding on `t`;
- no conflicting active portfolio link exists for a class; and
- TNA is positive and has not been carried across dates.

The mapping interval alone does not establish that a class is economically active: inspected `crsp_portno_map` intervals sometimes continue after a class stops reporting TNA. Activity must be established from exact-date fund records and independently documented termination/status information. Missing TNA is not zero. If completeness cannot be established, `portfolio_tna_usd` is missing for contract testing. The code must label the reason; it must not divide by the available subset of class TNA.

`tna_latest` may be used only with its explicit `tna_latest_dt`. A row's summary `caldt` cannot substitute for that date.

## 4. Historical portfolio-to-ETF-class relationship

CRSP `crsp_portno_map` establishes a dated database relationship between a share class and a portfolio. It does not by itself prove that an ETF class was, on every historical date, a pro-rata claim on that pooled portfolio.

The following fields are supporting evidence but are not sufficient proof individually or in combination:

- `crsp_cl_grp`, which CRSP constructs partly from class-name parsing and overlap;
- a shared `crsp_portno`;
- a shared ticker root, CUSIP root, name, adviser, or management company;
- `et_flag`;
- a current SEC registration applied retrospectively; or
- a filename or table suffix such as `fund_summary2`.

Raw-history review found that `et_flag` does not change in the available `fund_hdr_hist` scan, including histories with known mutual-fund-to-ETF status transitions. It can therefore be carried backward and is **not** accepted as a point-in-time ETF-format indicator.

An ETF class is `PRO_RATA_VERIFIED` for a bounded date interval only when the evidence bundle contains:

1. an effective-dated CRSP class-to-portfolio mapping;
2. an effective-dated ETF-class-to-traded-security crosswalk;
3. an event-time or interval-covering SEC filing identifying the ETF as a class of the same Fund/series whose classes invest in the same portfolio; and
4. filing language or governing-plan evidence showing class allocations/conversions are based on relative net assets or respective class NAVs, without a class-specific asset sleeve that would break proportional ownership.

The verification record must store the covered dates, filing accession/URL, series CIK, contract CIK, CRSP identifiers, reviewer, and any exception. A current filing can corroborate current structure but cannot alone establish pre-effective-date history.

V3 registers two product-date-specific positive controls:

- SPY on 2024-12-31 satisfies `SINGLE_CLASS_UIT_PRO_RATA`: the date-covering SEC prospectus defines Units as proportionate undivided interests in one trust portfolio, and the remaining machine-registered mapping, TNA, security-crosswalk, and identity conditions pass.
- Vanguard 500 Index Fund / VOO on 2024-12-31 satisfies `POOLED_MULTICLASS_PRO_RATA`: contemporaneous 2024 SEC materials identify the ETF and conventional shares as classes of the same Fund, allocate class economics by relative net assets or respective NAVs, and the exact-date N-CSR presents one Fund portfolio with equal class rights to assets and earnings. “No separate sleeve” is an inference from that combined public evidence and exact-date accounting, not a vendor-field assumption.

Neither verification extends to another product or date. In particular, V3 does not treat the VOO evidence as verification for 2024-06-30. Historical launch materials may provide background but are not the executable scope rule; the registered dates in `golden_sample_spec.json` control.

## 5. Holdings/TNA identity invariant

For every eligible raw position row having non-null `percent_tna` and `market_val`, construct:

```text
w_reported = percent_tna / 100
w_value    = market_val / portfolio_tna_usd
residual   = w_reported - w_value
```

### Frozen pilot tolerances

The row-level invariant is:

```text
abs(residual) <= 0.0002
```

The tolerance is in weight units: `0.0002` equals 0.02 percentage points, or 2 basis points of portfolio weight. It was frozen before V3 pilot execution. Across all seven testable cases representing six distinct portfolio-dates, the maximum absolute row error was `0.897134` basis points. This is an aggregate validation result; licensed row values are retained only in the private hash-bound evidence bundle. Tightening or widening the tolerance is a specification amendment.

To prevent a permissive absolute tolerance from hiding a bad denominator among small positions, each eligible portfolio-date must also pass this denominator-level invariant using rows with `abs(w_reported) >= 0.001` and nonzero `w_reported`:

```text
implied_tna_row = market_val / w_reported
abs(median(implied_tna_row) / portfolio_tna_usd - 1) <= 0.005
```

Thus the median implied denominator must be within `0.5%` of the reconstructed same-date pooled TNA. This amended tolerance is encoded in `gate01_config.json`; the V3 pilot was rebuilt and passed with it. The maximum portfolio-date median error was `0.268162%`, below the amended limit. The eligible row set, numerator signs, row counts, maximum absolute residual, median residual, and denominator ratio must be emitted privately for each portfolio-date. If no row meets the denominator-test threshold, that portfolio-date is `NOT_TESTABLE`, not a pass.

All eligible rows in all seven testable cases must pass the row-level invariant; there is no pass-rate waiver. The seven cases collapse to six distinct portfolio-dates because two registered cases test different rules on the same portfolio-date. A failure may diagnose an incomplete class set, wrong date, wrong unit, wrong row unit, duplicated TNA, or a genuinely different denominator. It must not be repaired by re-normalizing weights or choosing a nearby TNA.

## 6. ETF-class dollar exposure invariant

For ETF share class `j` mapped to pooled portfolio `p`, underlying position `i`, and exact economic date `t`, the only permitted class-dollar exposure formula is:

```text
etf_class_exposure_usd[j,i,t]
    = (percent_tna[p,i,t] / 100) * class_tna_usd[j,t]
```

It may be constructed only when:

- the portfolio-date holdings/TNA identity in Section 5 passed;
- class `j` is `PRO_RATA_VERIFIED` for date `t` under Section 4;
- ETF format and the ETF-security crosswalk are verified for date `t`;
- class TNA is present on exactly `t`, in the documented units; and
- the holding is preserved at its raw position unit before any documented security aggregation.

Otherwise the exposure is missing with an explicit failure code. The implementation must not substitute pooled TNA for ETF-class TNA, ETF-class TNA for the `percent_tna` denominator, a stale/nearest AUM, or a sponsor-level proportionality assumption.

For the identity check, pooled TNA is the denominator. For ETF-class dollar exposure, the correctly dated ETF-class TNA is the multiplier. These are different operations and different indices.

## 7. Golden sample

The sample membership, dates, raw-file hashes, and selection logic must be written and hashed before looking at invariant outcomes. At minimum it contains these strata:

1. pure ETF portfolios with one verified active share class;
2. pooled portfolios containing both conventional mutual-fund and ETF share classes, including VOO/Vanguard 500 on 2024-12-31 as the date-scoped pro-rata positive control;
3. funds selected by a pre-outcome rule for rapid same-class or pooled-AUM change;
4. stale holding reports selected by large `eff_dt - report_dt` and at least one exact-date-TNA failure;
5. historical ETF-status transitions. Because the raw `et_flag` scan found no actual flag changes, this stratum must include a known transition on both sides of its SEC event date and explicitly demonstrate the `et_flag` backfill failure; no flag change may be fabricated;
6. corporate-action cases affecting either the ETF security or an underlying position, with effective-dated identifiers retained; and
7. derivative and non-equity positions, including rows with missing Stock `permno`.

Each stratum needs at least one positive case and, where feasible, one deliberately invalid negative control. The golden-sample report must show raw rows, mapping rows, all same-date class TNA rows, SEC verification status, computed values, tolerance, and pass/fail reason. A sample category that cannot be populated is an unresolved contract gap and prevents pilot pass.

## 8. Small end-to-end pilot and raw-row inspection

Only after the golden sample passes may one small pilot run. Its universe and dates must be fixed in the pilot configuration and must be small enough for complete provenance review.

At least 20 distinct final exposure observations must be inspected back to raw records. The 20 cannot all come from one portfolio-date or one easy stratum. The inspection ledger must include:

- final observation key and value;
- `portfolio_id`, `share_class_id`, `etf_security_id`, and underlying position/security identifiers;
- all economic and availability fields;
- source file SHA-256 and raw row number for holdings, mapping, class TNA, and security crosswalk;
- raw `market_val`, `percent_tna`, TNA and their units;
- SEC pro-rata verification record where required;
- both sides of every formula and the invariant result; and
- reviewer disposition and notes.

No result is silently corrected during inspection. Any correction changes the specification or source transformation, invalidates the pilot, and requires a rebuilt golden sample followed by a new pilot.

## 9. `PILOT_PASS.json`

`PILOT_PASS.json` was created only after the golden sample, invariants, pilot, and 20-observation inspection passed. Its strict schema contains:

```json
{
  "schema_version": 1,
  "status": "PASS",
  "created_at_utc": "...",
  "hashes": {
    "code": {"algorithm": "...", "digest": "...", "files": ["..."]},
    "config": {"algorithm": "...", "digest": "..."},
    "data_contract": {"algorithm": "...", "digest": "..."},
    "manifest": {"algorithm": "...", "digest": "..."}
  },
  "required_invariant_ids": ["..."],
  "invariants": [{"id": "...", "passed": true, "result": {"...": "..."}}],
  "golden_sample": {"categories": {"...": 1}, "content_sha256": "..."},
  "raw_trace_inspection": {"observation_count": 25, "all_reconciled": true, "artifact_sha256": "..."},
  "artifacts": {"pilot_raw_trace_inspection.csv": {"sha256": "...", "bytes": 0}}
}
```

Hash rules:

- `code_hash`: SHA-256 of a canonical, sorted manifest of the exact executable source and shell files used by the pilot and full entry point, using file paths and content hashes. It is not merely the current Git commit.
- `config_hash`: SHA-256 of the canonical serialized pilot/full-run configuration.
- `data_contract_hash`: SHA-256 of canonical JSON in `data_contract.json`.
- `manifest_hash`: SHA-256 of the frozen input manifest used by the pilot. The preflight uses the already stored small manifest and must not scan the archive to recreate it.
- `golden_sample_hash` and `inspection_ledger_hash`: SHA-256 of the frozen evidence artifacts.

Unknown, skipped, waived, or not-testable required invariants are not `true` and cannot yield `PASS`.

## 10. Full-run preflight

Before any archive enumeration or read, the full-run entry point must:

1. locate `PILOT_PASS.json`; if absent, exit nonzero;
2. require `status == "PASS"` and every required invariant to be exactly `true`;
3. recompute the current code, config, and data-contract hashes without accessing the archive;
4. compare them byte-for-byte with the artifact;
5. compare the named frozen manifest, golden-sample, and inspection-ledger hashes against their already stored small files; and
6. exit nonzero on any missing file, mismatch, parse error, extra unrecognized amendment, or unresolved verification status.

Only after this preflight passes may the process enumerate or scan archive data. Creating a fresh `PILOT_PASS.json` from inside the full-run path is prohibited.

## 11. Amendment rule

Any new formula, tolerance, date cutoff, mapping rule, counterfactual, identifier interpretation, eligibility rule, exclusion, imputation, aggregation, or source substitution is a specification amendment. The amendment must:

1. receive a new contract version;
2. invalidate the existing `PILOT_PASS.json`;
3. rebuild and re-hash the golden sample, including cases affected by the amendment;
4. rerun the invariants and the small end-to-end pilot;
5. reinspect at least 20 final observations back to raw rows; and
6. create a new passing artifact before any full run.

The registered pilot has passed, but prior outputs remain `INVALIDATED_PENDING_DATA_CONTRACT` and the full implementation remains disabled. No Gate 0, Gate 1, or Gate 2 result may be reported. Rewriting or enabling the full implementation changes the scientific-code/config hash and therefore triggers this amendment process before any full run.
