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

### Federal Realty Investment Trust (CUSIP 31374720) — Category A

Appears in two SPY snapshots.

| event | ETF | snapshot | weight | classification |
|---|---|---|---|---|
| EMR 2023-02-08 | SPY | 2023-01-31 | 0.02% | A |
| ESS 2022-10-26 | SPY | 2022-09-30 | 0.02% | A |

**Why unmapped.** FRT (NYSE: FRT) is an S&P 500 REIT constituent. CUSIP
31374720 does not link to a PERMNO in the MFDB crosswalk for these snapshots.
The security's return is observable. Weight is 0.02% — negligible for basket
return precision but still an identifiable crosswalk gap.

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
| FOMC 2021-09-22 | SPY | 0.43% | 0.10% | 0.53% | yes, manual PERMNO lookup |
| FOMC 2021-09-22 | XLK | 0.00% | 0.09%* | 0.09% | n/a (net −0.14 + 0.23) |
| FOMC 2021-09-22 | XLF | 3.12% | 0.09% | 3.21% | yes, BLK lookup |
| FOMC 2022-01-26 | SPY | 0.40% | 0.00% | 0.40% | yes |
| FOMC 2022-01-26 | XLK | 0.00% | 0.16% | 0.16% | no (derivative) |
| FOMC 2022-01-26 | XLF | 3.03% | 0.00% | 3.03% | yes, BLK lookup |
| NDAQ 2022-04-20 | XLF | 2.56% | 0.00% | 2.56% | yes, BLK lookup |
| EMR 2023-02-08 | SPY | 0.42% | 0.00% | 0.42% | yes |
| ESS 2022-10-26 | SPY | 0.36% | 0.00% | 0.36% | yes |
| GL 2021-07-21 | XLF | 3.02% | 0.06% | 3.08% | yes (BLK); 0.06% B |

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
