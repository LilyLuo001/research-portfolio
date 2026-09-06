# Unmapped holding-line categorization — six governing snapshots

Produced by inspecting the unmapped lines (is_cash=False, permno=NaN) in each
governing snapshot using `out/holdings_three_etfs.parquet` on SCC. The
`s8_coverage.parquet` aggregate reports the total unmapped mass per event-ETF;
this document resolves what those lines actually are.

Three categories are distinguished below. The critical distinction: a security
whose PERMNO crosswalk is absent in the CRSP holdings-to-DSF link is **not**
the same as a security with no observable return. Conflating them overstates the
measurement gap.

---

## Categories

**A — Known equity, PERMNO crosswalk absent.**
The security is identifiable from its CUSIP and name. A PERMNO exists in CRSP
(the security traded on a US exchange in the relevant period), but the holding
record does not carry one, because the CRSP mutual-fund database's internal
crosswalk did not link this CUSIP to a DSF entry for this snapshot. The return
is **not** unobservable — it is computable from exchange data once the CUSIP is
manually resolved to a PERMNO. These lines cannot be treated as a return bound
without an explicit claim that the quote for that security is also missing.

**B — Non-equity / non-quotable instrument.**
The line has no CUSIP, no security-level return, and no quote to request. These
are either balance-sheet netting entries or derivative positions. The return on
these lines is not computable from equity quote data; they are a genuine gap.

**C — Genuinely unidentifiable.**
No CUSIP and no recognizable name. None found in these six snapshots.

---

## Line-by-line inventory

### BlackRock Inc (CUSIP 09290D10) — Category A

Appears in every XLF snapshot and in every SPY snapshot. Dominant item.

| event | ETF | snapshot | weight | classification |
|---|---|---|---|---|
| FOMC 2021-09-22 | XLF | 2021-08-31 | 3.12% | A |
| FOMC 2021-09-22 | SPY | 2021-08-31 | 0.35% | A |
| FOMC 2022-01-26 | XLF | 2021-12-31 | 3.03% | A |
| FOMC 2022-01-26 | SPY | 2021-12-31 | 0.32% | A |
| NDAQ 2022-04-20 | XLF | 2022-03-31 | 2.56% | A |
| EMR 2023-02-08 | SPY | 2023-01-31 | 0.33% | A |
| ESS 2022-10-26 | SPY | 2022-09-30 | 0.28% | A |
| GL 2021-07-21 | XLF | 2021-06-30 | 3.02% | A |

**Why unmapped.** CUSIP 09290D10 is BlackRock Inc common stock (NYSE: BLK).
BLK is in CRSP DSF with SHRCD 10 or 11. The crosswalk failure is in the
mutual-fund holdings table: the MFDB entry for this CUSIP carries no PERMNO
link. The security and its daily and intraday return are fully observable.
Manual resolution: look up PERMNO for CUSIP 09290D10 in CRSP DSF directly.

**Consequence for the measurement.** The BlackRock position is the source of
virtually all of the XLF "missing mass." For XLF events it is roughly 3% of
TNA. This weight is **not** a return bound: BLK traded on NYSE during all six
event windows and its quote path is requestable. If BLK is added to the quote
manifest (and its weight confirmed from an alternative source), the XLF basket
becomes essentially complete. If it is not added, the 3% weight must be carried
as an explicit exclusion with its return unobserved, which differs from saying
the basket has a measurement error of that magnitude.

---

### LabCorp Holdings Inc (CUSIP 50492210) — Category A

Appears in three SPY snapshots.

| event | ETF | snapshot | weight | classification |
|---|---|---|---|---|
| FOMC 2021-09-22 | SPY | 2021-08-31 | 0.08% | A |
| FOMC 2022-01-26 | SPY | 2021-12-31 | 0.08% | A |
| EMR 2023-02-08 | SPY | 2023-01-31 | 0.07% | A |
| ESS 2022-10-26 | SPY | 2022-09-30 | 0.06% | A |

**Why unmapped.** LabCorp (NYSE: LH) trades under the name "Laboratory
Corporation of America Holdings." The holding record uses the name "LABCORP
HOLDINGS INC ORD" with CUSIP 50492210. The PERMNO crosswalk is absent, likely
because the CUSIP in the MFDB filing does not match the DSF entry for LH. The
security is an S&P 500 constituent with an observable return.

---

### Federal Realty Investment Trust (CUSIP 31374720 → 31374510) — Category A

Appears in two SPY snapshots.

| event | ETF | snapshot | weight | classification |
|---|---|---|---|---|
| EMR 2023-02-08 | SPY | 2023-01-31 | 0.02% | A |
| ESS 2022-10-26 | SPY | 2022-09-30 | 0.02% | A |

**Why unmapped.** Federal Realty Investment Trust converted from a Maryland real
estate investment trust to a Maryland corporation on January 1, 2022, with a
documented CUSIP change from 31374720 (trust) to 31374510 (corporation). The
MFDB snapshots dated 2022-09-30 and 2023-01-31 still record the pre-conversion
CUSIP 31374720, but CRSP DSF for 2022 and 2023 carries CUSIP 31374510. The
automatic PERMNO crosswalk fails because no 31374720 entry exists in the
post-conversion DSF; CUSIP 31374510 in DSF resolves to **PERMNO 58413**
(confirmed in crsp_dsf_2022.parquet and crsp_dsf_2023.parquet). Weight is
0.02% per snapshot — negligible for basket return precision but resoluble.

---

### "OTHER ASSETS LESS LIABILITIES" / "OTHER ASSETS" (CUSIP=NA) — Category B

Appears in multiple snapshots as a net balance-sheet line.

| event | ETF | snapshot | weight | sign | classification |
|---|---|---|---|---|---|
| FOMC 2021-09-22 | SPY | 2021-08-31 | 0.10% | positive | B |
| FOMC 2021-09-22 | XLF | 2021-08-31 | 0.09% | positive | B |
| FOMC 2021-09-22 | XLK | 2021-08-31 | −0.14% | **negative** | B |
| GL 2021-07-21 | XLF | 2021-06-30 | 0.06% | positive | B |

These are fund-level accounting entries — net of receivables, payables,
accruals, and other non-security balance-sheet items. They carry no CUSIP and
no security return. The XLK 2021-08-31 entry is negative (−0.14%), meaning
total reported TNA minus holdings exceeds 100% — a normal rounding artifact in
MFDB filings.

**Consequence.** These lines have no quote to request and no equity return to
compute. They are the only lines in these snapshots for which "return unknown"
is literally correct. Total Category B weight across all events:

| event | ETF | total Category B weight |
|---|---|---|
| FOMC 2021-09-22 | SPY | 0.10% |
| FOMC 2021-09-22 | XLK | −0.14% (net) |
| FOMC 2021-09-22 | XLF | 0.09% |
| FOMC 2022-01-26 | (no B lines found) | — |
| NDAQ 2022-04-20 | (no B lines found) | — |
| EMR 2023-02-08 | (no B lines found) | — |
| ESS 2022-10-26 | (no B lines found) | — |
| GL 2021-07-21 | XLF | 0.06% |

---

### "ES&P TE SIF SP21" / "ES&P TE SIF MR22" (CUSIP=NA) — Category B

Appears in XLK snapshots only.

| event | ETF | snapshot | weight | classification |
|---|---|---|---|---|
| FOMC 2021-09-22 | XLK | 2021-08-31 | 0.23% | B |
| FOMC 2022-01-26 | XLK | 2021-12-31 | 0.16% | B |

The name pattern "ES&P TE SIF SP21" / "ES&P TE SIF MR22" is consistent with
an equity index futures or cash-equitization instrument used by the fund manager
(SIF = Single Index Futures or similar; SP21 = September 2021 expiry; MR22 =
March 2022). No CUSIP is present. These are not equity securities; computing
a basket return from equity quotes and including them would require futures
pricing data. Their weight (0.16–0.23%) is small but non-zero.

**Consequence.** These lines have no equity quote to request. The XLK basket
for the two FOMC events excludes 0.16–0.23% of TNA carried in derivative or
futures-equivalent positions. This is a genuine exclusion and the only one in
XLK that cannot be closed by PERMNO crosswalk resolution.

---

## Summary by event-ETF

| event | ETF | Cat A weight | Cat B weight | total unmapped | Cat A resoluble? |
|---|---|---|---|---|---|
| FOMC 2021-09-22 | SPY | 0.43% | 0.10% | 0.53% | yes — BLK (87267), LH (12062) |
| FOMC 2021-09-22 | XLK | 0.00% | 0.09%* | 0.09% | n/a (net −0.14 + 0.23) |
| FOMC 2021-09-22 | XLF | 3.12% | 0.09% | 3.21% | yes — BLK (87267) |
| FOMC 2022-01-26 | SPY | 0.40% | 0.00% | 0.40% | yes — BLK (87267), LH (12062) |
| FOMC 2022-01-26 | XLK | 0.00% | 0.16% | 0.16% | no (derivative) |
| FOMC 2022-01-26 | XLF | 3.03% | 0.00% | 3.03% | yes — BLK (87267) |
| NDAQ 2022-04-20 | XLF | 2.56% | 0.00% | 2.56% | yes — BLK (87267) |
| EMR 2023-02-08 | SPY | 0.42% | 0.00% | 0.42% | yes — BLK (87267), LH (12062), FRT (58413) |
| ESS 2022-10-26 | SPY | 0.36% | 0.00% | 0.36% | yes — BLK (87267), LH (12062), FRT (58413) |
| GL 2021-07-21 | XLF | 3.02% | 0.06% | 3.08% | yes — BLK (87267); 0.06% B |

\* XLK 2021-09-22 net: 0.23% futures − 0.14% other assets = 0.09% net; reported sum 99.99%.

**Key corrective.** The figures previously described in `MANIFEST.md` as the
"missing mass" that is "not reconstructable from this source" are mostly
Category A — identifiable securities whose PERMNO crosswalk is missing from
the MFDB holdings table. BlackRock Inc alone accounts for 2.56–3.21% in every
XLF snapshot. That weight is not a bound on the basket return; it is a bound
on what the automated PERMNO pipeline produces. The bound collapses to near
zero if BLK, LH, and FRT are added to the quote request using their CUSIP or
exchange ticker. Category B (balance-sheet entries, derivatives) is the only
portion for which no equity return can be computed regardless of quote data;
it ranges from 0 to 0.23% depending on event and ETF.

---

## PERMNO crosswalk resolution — post-primary analysis

The three Category A securities were searched against CRSP DSF and CRSP MSF
(`crsp_msf_full.parquet`, SCC archive) by CUSIP. Results:

| security | CUSIP (MFDB) | CUSIP (DSF post-2022) | exchange ticker | resolved PERMNO | source |
|---|---|---|---|---|---|
| BlackRock Inc | 09290D10 | 09290D10 | BLK (NYSE) | **87267** | crsp_msf_full.parquet |
| LabCorp Holdings | 50492210 | 50492210 | LH (NYSE) | **12062** | crsp_msf_full.parquet |
| Federal Realty Investment Trust | 31374720 | **31374510** | FRT (NYSE) | **58413** | crsp_dsf_2022.parquet, crsp_dsf_2023.parquet |

**FRT resolution.** The CUSIP changed from 31374720 (Maryland trust) to 31374510
(Maryland corporation) on January 1, 2022. The MFDB snapshots dated 2022-09-30
and 2023-01-31 record the pre-conversion CUSIP; CRSP DSF for those years carries
the post-conversion CUSIP 31374510 → PERMNO 58413. All three Category A
securities are now resolved. No Category A exclusion remains.

---

## Equity coverage before and after PERMNO repair

Applying BLK (PERMNO 87267) and LH (PERMNO 12062) to the governing snapshots.
"Before" = automated pipeline result; "After" = with these two PERMNOs added.
FRT remains unresolved; its weight appears in the remaining-unmapped column.

Percentages are PERMNO-matched equity weight as a share of reported percent_tna
(the MFDB-reported sum, which itself deviates from 100% by filing rounding —
see raw totals below). "Before" = automated pipeline result; "After" = with all
three Category A PERMNOs added (BLK 87267, LH 12062, FRT 58413).

| ETF | snapshot | before | after | gain | remaining unmapped | remaining unmapped detail |
|---|---|---|---|---|---|---|
| SPY | 2021-08-31 | 99.42% | 99.85% | +0.43% | 0.10% | OTHER ASSETS LESS LIABILITIES (0.10%) |
| XLK | 2021-08-31 | 99.72% | 99.72% | +0.00% | 0.09% | ES&P TE SIF SP21 (0.23%); OTHER ASSETS (−0.14%) |
| XLF | 2021-08-31 | 96.68% | 99.80% | +3.12% | 0.09% | OTHER ASSETS (0.09%) |
| SPY | 2021-12-31 | 99.72% | 100.12% | +0.40% | 0.00% | none |
| XLK | 2021-12-31 | 99.82% | 99.82% | +0.00% | 0.16% | ES&P TE SIF MR22 (0.16%) |
| XLF | 2021-12-31 | 96.76% | 99.79% | +3.03% | 0.00% | none |
| XLF | 2022-03-31 | 97.22% | 99.78% | +2.56% | 0.00% | none |
| SPY | 2022-09-30 | 99.56% | 99.92% | +0.36% | 0.00% | none |
| SPY | 2023-01-31 | 99.46% | 99.88% | +0.42% | 0.00% | none |
| XLF | 2021-06-30 | 96.78% | 99.80% | +3.02% | 0.06% | OTHER ASSETS (0.06%) |

Snapshot-to-event mapping: FOMC 2021-09-22 uses SPY/XLK/XLF 2021-08-31; FOMC
2022-01-26 uses SPY/XLK/XLF 2021-12-31; NDAQ 2022-04-20 uses XLF 2022-03-31;
EMR 2023-02-08 uses SPY 2023-01-31; ESS 2022-10-26 uses SPY 2022-09-30; GL
2021-07-21 uses XLF 2021-06-30.

After full Category A repair, XLF equity coverage reaches 99.78–99.80% in all
snapshots. SPY reaches 99.85–99.92% (ESS/EMR snapshots now 0.00% remaining
after FRT resolution). XLK is unchanged because all its unmapped lines are
Category B. The only residual unmapped weight in any snapshot is Category B
(balance-sheet entries and expired futures; see §below).

The "after" figure exceeds 100% in SPY 2021-12-31 (100.12%). The source of that
excess is unverified; the raw MFDB sum for that snapshot is 100.39% (see raw
weight totals below), indicating the MFDB filing itself sums above 100%.

**Raw MFDB weight totals (sum of percent_tna, all rows, from holdings parquet).**
The PERMNO repair is a join operation that assigns PERMNOs to existing rows
without modifying any weight field. Row counts and signed weight totals are
preserved by construction.

| event | ETF | snapshot | rows | raw sum percent_tna | cat_b rows (SIF + OTHER ASSETS) |
|---|---|---|---|---|---|
| FOMC 2021-09-22 | SPY | 2021-08-31 | 508 | 100.07% | 0.10% |
| FOMC 2021-09-22 | XLK | 2021-08-31 | 77 | 99.99% | 0.09% |
| FOMC 2021-09-22 | XLF | 2021-08-31 | 67 | 99.98% | 0.09% |
| FOMC 2022-01-26 | SPY | 2021-12-31 | 507 | 100.39% | 0.00% |
| FOMC 2022-01-26 | XLK | 2021-12-31 | 79 | 100.11% | 0.16% |
| FOMC 2022-01-26 | XLF | 2021-12-31 | 68 | 99.93% | 0.00% |
| NDAQ 2022-04-20 | XLF | 2022-03-31 | 69 | 99.94% | 0.00% |
| EMR 2023-02-08 | SPY | 2023-01-31 | 505 | 99.93% | 0.00% |
| ESS 2022-10-26 | SPY | 2022-09-30 | 507 | 100.33% | 0.00% |
| GL 2021-07-21 | XLF | 2021-06-30 | 67 | 100.02% | 0.06% |

---

## XLK futures contract identification and reconciliation

The XLK snapshot lines labelled "ES&P TE SIF SP21" (snapshot 2021-08-31) and
"ES&P TE SIF MR22" (snapshot 2021-12-31) are identified as CME E-mini
Technology Select Sector futures, CME root symbol **XAK**. Fields are from
`holdings_three_etfs.parquet` directly; arithmetic is verified against reported
market_val.

| CRSP label | CME ticker | expiry | direction | nbr_shares (CRSP) | est. contracts | multiplier | implied index level | market_val | percent_tna |
|---|---|---|---|---|---|---|---|---|---|
| ES&P TE SIF SP21 | XAKU1 | September 2021 | LONG | 67,100 | 671 | $100/pt | 1,597.50 | $107,192,250 | 0.23% |
| ES&P TE SIF MR22 | XAKH2 | March 2022 | LONG | 47,400 | 474 | $100/pt | 1,750.80 | $82,987,920 | 0.16% |

**CRSP convention.** The `nbr_shares` field for futures is recorded as
`contracts × multiplier` (i.e., 100 × number of contracts). The implied index
level equals `market_val / nbr_shares`. Verification: 671 × $100 × 1,597.50 =
$107,192,250 (exact); 474 × $100 × 1,750.80 = $82,987,920 (exact).

**XAKU1 expiry — critical.** CME September 2021 quarterly futures (XAKU1)
expired on the third Friday of September 2021, which is **September 17, 2021**
— five days before the FOMC 2021-09-22 event. The governing snapshot (2021-08-31)
records XAKU1 with 671 contracts at $107M. By the event date, this contract had
expired and the fund had rolled: the 2021-09-30 snapshot shows XAKZ1 (December
2021) with 50,900 nbr_shares / 509 contracts at $76.6M. The exact roll date,
quantity held on September 22, and whether the fund maintained an equivalent
notional exposure are not known from the available monthly snapshots.

**Consequence for the FOMC 2021-09-22 event.** The August 31 snapshot cannot be
used to assert the fund held a specific XAK futures quantity on September 22. The
XLK basket return for this event carries an unresolved futures exposure. The
direction and approximate magnitude (cash-equitization, LONG) are inferred from
the surrounding month-end records, but no specific contract, quantity, or
notional can be assigned without intraday position data. Retain this as an
unresolved exposure; do not substitute the August 31 position as the September 22
position.

**XAKH2 (March 2022) is not affected.** The FOMC 2022-01-26 event date is January
26, 2022. XAKH2 expires on the third Friday of March 2022 (March 18, 2022) —
well after the event. The 2021-12-31 snapshot showing 474 XAKH2 contracts at
$82.99M governs this event without an expiry concern.

**Exclusion rule.** These positions must **not** be excluded from the economic
exposure of the fund merely because they lack a stock PERMNO or because the
carrying value is small. They carry genuine beta exposure to the XLK basket.
There is no equity quote to request for futures; the 0.16–0.23% weight is
Category B and must be reported as an explicit exclusion in any basket return
calculation, not silently dropped.

The "OTHER ASSETS LESS LIABILITIES" (negative) lines in the XLK 2021-08-31
snapshot (−0.14%) are balance-sheet netting entries unrelated to the futures
position; they are a separate Category B item.
