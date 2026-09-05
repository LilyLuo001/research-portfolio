# Documentation evidence and redacted validation summary for the P1 data contract

- Evidence snapshot: 2026-09-05
- Contract supported: `P1_CRSP_HOLDINGS_TNA_CONTRACT_2026-09-05_V3`
- Prior-result status: `INVALIDATED_PENDING_DATA_CONTRACT`
- Data-contract pilot status: `PASS`

This file explains what the cited public documentation and the redacted validation aggregates establish. It contains no licensed CRSP/WRDS row values and is neither an executable specification nor a Gate report. The sole executable normative contract is the hash-bound combination of `data_contract.json`, `gate01_config.json`, and `golden_sample_spec.json`; if this narrative conflicts with those files, the machine-readable files control.

Prior Gate 0/1 outputs remain invalid, Gate 2 has not been authorized, and no Gate conclusion appears here. The V3 golden sample and pilot passed 18/18 registered invariants, including the identity tests for all seven testable cases representing six distinct portfolio-dates. The full implementation remains disabled.

## Evidence labels

- `DOCUMENTED`: stated by an authoritative CRSP, WRDS, or SEC source.
- `RAW_VALIDATED`: reproduced from the SCC source records or an identified market record.
- `PROJECT_RULE`: a frozen research-design choice needed to make an implementation unambiguous; it is not attributed to a vendor.
- `NOT_ESTABLISHED`: unavailable or insufficiently supported and therefore not safe to infer.

## 1. CRSP and WRDS definitions

Primary source: [CRSP Survivor-Bias-Free US Mutual Fund Database Guide, SAS/ASCII release](https://www.crsp.org/wp-content/uploads/2023/10/CRSP_US_Mutual_Funds_Guide_SAS_ASCII_R.pdf). A [WRDS-hosted copy](https://wrds-www.wharton.upenn.edu/documents/410/CRSP_MFDB_Guide.pdf) is also available.

| Claim | Evidence and location | Label | Contract implication |
|---|---|---|---|
| `crsp_fundno` identifies a fund/share-class record. | CRSP Guide, fund-header sections around pp. 13–15. | `DOCUMENTED` | It is the share-class index, not the pooled-portfolio or traded-security index. |
| `crsp_portno` identifies a portfolio and one or more funds/classes can map to it. | CRSP Guide, portfolio and class-group discussion around pp. 13–15. | `DOCUMENTED` | Holdings and class TNA require an explicit effective-dated bridge. |
| `series_cik` groups share classes issued against the same portfolio; `contract_cik` denotes one class/contract. | CRSP Guide, SEC identifier definitions around p. 9. | `DOCUMENTED` | Series and contract identifiers corroborate, but do not replace, CRSP identifiers. |
| Holdings are keyed to `crsp_portno` and `report_dt`; `eff_dt` is the date the information was received/effective in the feed and is no earlier than `report_dt`. | CRSP Guide, Holdings table around p. 18. | `DOCUMENTED` | Economic date and availability date are distinct. The source exposes a date, not a timestamp. |
| `percent_tna` is a security/position percentage of total net assets in the portfolio. | CRSP Guide, Holdings field definitions around p. 18. | `DOCUMENTED` | Divide by 100 to obtain a weight; its denominator is pooled portfolio TNA, not ETF-class TNA. |
| `market_val` is the position's market value as of `report_dt`; `nbr_shares` is the shares held in the portfolio. | CRSP Guide, Holdings field definitions around p. 18. | `DOCUMENTED` | `market_val` is a holdings-row quantity, not class AUM. The guide does not state a printed scale beside the field. |
| A holding `permno` exists only when the issue is covered by CRSP; other descriptors include company key, CUSIP, ticker, coupon, and maturity. | CRSP Guide, Holdings field definitions around p. 18. | `DOCUMENTED` | Missing Stock `permno` is expected for some derivatives and non-equity positions and is not grounds to drop them. |
| `crsp_portno_map` contains `crsp_fundno`, `crsp_portno`, `begdt`, and `enddt`. | CRSP Guide, mapping table around p. 19. | `DOCUMENTED` | The raw relationship is effective dated. The guide does not establish whether a project should treat both interval endpoints as inclusive. |
| Monthly TNA is keyed by `crsp_fundno` and `caldt` and is reported in millions of dollars. | CRSP Guide, Monthly Total Returns/TNA fields around p. 19. | `DOCUMENTED` | Raw TNA is at class level; pooled TNA is the same-date sum across the complete mapped class set, multiplied by one million. |
| Fund-summary `tna_latest` is the latest month-end TNA in millions and has its own `tna_latest_dt`. | CRSP Guide, Fund Summary fields around p. 17. | `DOCUMENTED` | Historical code must join on `tna_latest_dt`, not assume the row's summary `caldt` is the TNA date. |
| `crsp_cl_grp` is constructed using class-name parsing/cleanup and overlapping histories. | CRSP Guide, class-group discussion around pp. 14–15. | `DOCUMENTED` | It is a useful grouping aid, not legal/economic proof of a pro-rata pooled claim. |
| `et_flag` codes an ETF as `F` and an ETN as `N`. | CRSP Guide, fund-history field definitions. | `DOCUMENTED` | The meaning of a populated value is documented; its suitability as point-in-time history is not. |

The [WRDS Return Gap macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/wrds-macros-return-gap/) provides independent implementation evidence. In steps 2.3–2.6 it treats observations keyed by `crsp_fundno` as share-class quantities and aggregates across classes to obtain a portfolio-level quantity. This supports the class-versus-portfolio distinction; it does not establish the P1 date cutoff or pro-rata rule.

An official CRSP Mutual Fund Knowledge Base has additionally warned that a `crsp_portno` can associate records from more than one management company in client/feeder arrangements. The formerly published URL is [recorded here](https://www.crsp.org/wp-content/uploads/CRSP_US_Mutual_Funds_Knowledge_Base.pdf), although the file may have moved during CRSP's site migration. The implication is conservative: a common `crsp_portno` is not, by itself, proof of identical pro-rata claims.

### Public CRSP sample arithmetic

The public holdings example around pp. 49–50 of the CRSP Guide shows that dividing different position-level `market_val` observations by their reported percentage weights yields the same portfolio-level denominator, up to displayed precision. The row values are intentionally not reproduced here. This supports the pooled-portfolio denominator and does not identify an ETF-class denominator.

## 2. Redacted raw-record validation

The licensed row-level evidence remains in the hash-bound private pilot bundle. This public narrative records only non-proprietary methods and aggregate outcomes.

### `market_val` unit and price-date rule

Sampled equity positions reconciled `market_val` to shares times the absolute CRSP security price. V3 selects the latest trading observation on or before `report_dt` and rejects a reconciliation if that price is more than three calendar days old. This validates U.S. dollars as the working `market_val` unit and rules out a millions multiplier. The three-day cutoff is a `PROJECT_RULE`, not a vendor definition.

### Share-class versus pooled TNA

The V3 identity was evaluated for all seven testable golden cases, representing six distinct portfolio-dates. Every eligible holdings row passed:

- maximum absolute row-weight error: `0.897134` basis points, below the frozen `2` basis-point limit; and
- maximum portfolio-date median implied-denominator error: `0.268162%`, below the V3 `0.5%` limit.

These are aggregates across the validation set, not disclosed source rows. They support the documented interpretation that `percent_tna / 100` uses same-date pooled portfolio TNA. The pooled weight and the multiplication by verified ETF-class TNA remain separate operations.

### Availability rule

`eff_dt` has date precision, not intraday precision. V3 therefore treats a complete holdings snapshot as usable only from the first calendar day strictly after the maximum `eff_dt` across all rows in that portfolio/report snapshot. Publication delay remains `max(eff_dt) - report_dt`; it is not report age and is not silently repaired with a later TNA.

### ETF flag history

The audited history did not provide a reliable within-fund ETF-format transition signal for the registered conversion negative control. The raw `et_flag` can be carried backward and therefore cannot date ETF status by itself. This aggregate finding is `RAW_VALIDATED` only for the audited archive and does not justify a claim about every CRSP release.

### Historical portfolio map and table naming

The audited relationship object contains the documented `crsp_fundno`, `crsp_portno`, `begdt`, and `enddt` schema. Validation also showed that interval coverage alone is insufficient to establish that a class is economically active; complete pooled TNA requires exact-date TNA plus effective historical status evidence, and missing TNA is never treated as zero.

The published CRSP Guide documents a Fund Summary table but does not assign a distinct economic meaning to a local filename suffix such as `fund_summary2`. Local names are therefore `NOT_ESTABLISHED` evidence for row units or denominators.

## 3. SEC evidence for pro-rata ETF claims

SEC evidence is accepted only for the explicitly registered product-date. A common sponsor, benchmark, ticker family, or current structure is not extrapolated to another fund or historical date.

### SPY: single-class UIT evidence for 2024-12-31

The [2024 SPDR S&P 500 ETF Trust prospectus](https://www.sec.gov/Archives/edgar/data/884394/000119312524016958/d109104d497.htm) describes each SPY Unit as a proportionate undivided interest in one unit-investment-trust portfolio and derives per-Unit NAV from total Trust net assets. Combined with the dated class mapping, exact-date class-versus-pooled TNA equality, ETF-security crosswalk, and passing holdings/TNA identity, this supports `SINGLE_CLASS_UIT_PRO_RATA` for SPY on 2024-12-31 only.

### VOO: pooled multi-class evidence for 2024-12-31

The [April 2024 Vanguard Index Funds statutory filing](https://www.sec.gov/Archives/edgar/data/36405/000168386324002986/f38455d0.htm) identifies ETF Shares as an exchange-traded class of Vanguard 500 Index Fund alongside its conventional classes and states that the classes have the same investment objective, strategies, and policies.

The [Vanguard Multiple Class Plan filing index](https://www.sec.gov/Archives/edgar/data/106830/000168386324009332/0001683863-24-009332-index.htm) shows that the attached [Multiple Class Plan](https://www.sec.gov/Archives/edgar/data/106830/000168386324009332/f40270d4.htm) was filed and effective on 2024-12-20, with Schedule A last updated on 2024-11-19. The plan:

- lists Investor, Admiral, Institutional Select, and ETF as the authorized classes of Vanguard 500 Index Fund;
- permits conversion into ETF Shares of the same Fund at the respective class NAVs;
- allocates fund-wide expenses and income, gains, and losses by relative class net assets; and
- gives the classes the same remaining rights, obligations, and privileges except for identified class-specific matters.

The [Vanguard 500 Index Fund N-CSR filing index](https://www.sec.gov/Archives/edgar/data/36405/000110465925020270/0001104659-25-020270-index.htm) records a report period ending 2024-12-31. Its [certified shareholder report](https://www.sec.gov/Archives/edgar/data/36405/000110465925020270/tm253223d8_ncsr.htm) presents one Fund-level portfolio and states in the accounting notes that each class has equal rights to Fund assets and earnings, subject to class-specific expenses, while income, other non-class expenses, and investment gains and losses are allocated by relative net assets. The publicly reported class net assets sum exactly to publicly reported Fund net assets; dollar amounts are omitted here because they are unnecessary to the contract conclusion.

Together these sources support `POOLED_MULTICLASS_PRO_RATA` for VOO on 2024-12-31 only. “No separate sleeve” is an inference from one Fund-level portfolio, equal rights to assets and earnings, relative-net-assets allocation, and exact class-to-Fund accounting. V3 does not treat this evidence as establishing VOO on 2024-06-30 or any other unregistered date.

## 4. Evidence-to-contract conclusions

| Question | Conclusion | Basis |
|---|---|---|
| What is a holdings row? | A position line in a pooled `crsp_portno` portfolio on `report_dt`. | CRSP holdings definitions. |
| What are the `market_val` units? | U.S. dollars for the audited holdings construction. | Guide meaning plus redacted shares-times-price validation. |
| What are `percent_tna` units and denominator? | Percentage points; pooled portfolio TNA on `report_dt`; use `/ 100`. | CRSP definition, public sample arithmetic, and aggregate V3 validation. |
| Is raw TNA pooled or class level? | Class level by `crsp_fundno`, in USD millions; pooled TNA is a derived same-date complete-class sum. | CRSP table key/unit and WRDS macro. |
| Does `crsp_portno` prove pro-rata ownership? | No. | CRSP mapping scope, client/feeder caution, absence of legal/economic terms. |
| Does historical `et_flag` establish ETF status date? | No for the audited archive. | Raw no-change/backfill finding. |
| Can ETF-class exposure equal portfolio weight times ETF-class TNA? | Yes only for a date-scoped `PRO_RATA_VERIFIED` class with exact-date class TNA and a passing denominator audit. | CRSP quantities plus event-time SEC structure evidence. |
| Which pro-rata controls passed? | SPY under `SINGLE_CLASS_UIT_PRO_RATA` and VOO under `POOLED_MULTICLASS_PRO_RATA`, each only on 2024-12-31. | Product- and date-specific SEC evidence plus the V3 accounting tests. |
| Is an interval endpoint inclusive? | Frozen as inclusive for the pilot, but not documented by CRSP. | `PROJECT_RULE`. |
| When are holdings usable? | First calendar day strictly after the snapshot's maximum `eff_dt`. | Date-only source precision plus the frozen no-lookahead rule. |
| Which price can reconcile `market_val`? | Latest CRSP price on or before `report_dt`, no more than three calendar days earlier. | V3 `PROJECT_RULE`. |
| What is TNA's availability timestamp? | Unknown. | No verified source field. |

## 5. Explicit non-claims and unresolved availability

The evidence does **not** establish any of the following:

- that every ETF sharing `crsp_portno` with conventional classes is a pro-rata share class;
- that a current SEC filing proves the same structure before its effective period;
- that `crsp_cl_grp`, `et_flag`, name, ticker, or CUSIP alone is a historical class relationship;
- that CRSP's relationship interval endpoints are vendor-defined as inclusive;
- that TNA was publicly or operationally available on `caldt` or `tna_latest_dt`;
- an intraday availability timestamp for holdings or TNA;
- that nearest-date, stale, or carried TNA is an acceptable substitute;
- that derivative/non-equity rows without `permno` can be discarded;
- that VOO's 2024-12-31 verification establishes its economics on 2024-06-30 or any other date;
- any Gate 0, Gate 1, or Gate 2 result.

The V3 golden sample, small end-to-end pilot, 25 private raw-trace inspections, all seven testable cases across six distinct portfolio-dates, and 18 registered invariants passed. The public, non-proprietary status and hashes are recorded in `pilot/PILOT_PUBLIC_RECEIPT.json`; licensed row-level evidence and the canonical authorization receipt remain in the controlled execution environment. This validation does not make any old or future Gate output valid. The old full implementation remains disabled pending a contract-conformant rewrite and a new hash-bound pilot.
