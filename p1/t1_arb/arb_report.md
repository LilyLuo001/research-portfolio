# P1-T1-arb — assembly report

Source: `../t1_events_final.json` (adjudicated channel). Assembly by `assemble.py`.

## Counts
- event-filings (filing × fund): **1171**
- unique conversion groups: **264**
- → `events_merged.csv` (fund_name + effective_date resolved): **172**
- → held back (needs_fulltext, no stated effective_date or fund_name): **73**
- effective_date conflicts across a group's filings (resolved to latest-filed): **15**
- primary-key (fund_name, effective_date) collisions: **0**

## Owner-gate pool (was silent before 2026-08-27)
The 2026-07-18 spot-check gate parked event records at `recheck`/`defer`/`not_event`, and this script used to drop every one of them without trace. They are now adjudicated in `recheck_resolution.json` against the committed filing excerpts (`p1/t1_channelA_wip/handoff/cb_*.txt`), with every quote re-verified by `resolve_recheck.py`.

- released to the clean set (adjudicated `event`): **85** records
- still excluded: **26** records

Still-excluded records, by why — a rejection on the evidence and an open question are different things and are not pooled:

| fund | family | eff | gate reason | adjudication |
|---|---|---|---|---|
| iM DBi Hedge Strategy ETF | Manager Directed Portfolios | 2021-09-17 | ETF_TO_ETF: target is an ETF | **not_event** |
| iM DBi Hedge Strategy ETF | Manager Directed Portfolios | 2021-09-17 | ETF_TO_ETF: target is an ETF | **not_event** |
| iM DBi Managed Futures Strategy ETF | Manager Directed Portfolios | 2021-09-17 | ETF_TO_ETF: target is an ETF | **not_event** |
| iM DBi Managed Futures Strategy ETF | Manager Directed Portfolios | 2021-09-17 | ETF_TO_ETF: target is an ETF | **not_event** |
| iM Dolan McEniry Corporate Bond Fund | Manager Directed Portfolios | 2021-09-17 | evidence describes the DBi ETFs, not this fund; confirm target was a mutual fund | **not_event** |
| iM Dolan McEniry Corporate Bond Fund | Manager Directed Portfolios | 2021-09-17 | evidence describes the DBi ETFs, not this fund; confirm target was a mutual fund | **not_event** |
| Baron FinTech Fund | Baron Select Funds | 2025-12-12 | target type unproven | **unresolved** |
| Baron Financials Fund | Baron ETF Trust | 2025-12-12 | acquired-fund type not explicit | **unresolved** |
| Baron Technology Fund | Baron Select Funds | 2025-12-12 | target type unproven | **unresolved** |
| Baron Technology Fund | Baron ETF Trust | 2025-12-12 | acquired-fund type not explicit | **unresolved** |
| Fort Pitt Capital Fund | Valued Advisers Trust | 2026-05-15 | acquirer-ETF only | **unresolved** |
| Harding Loevner International Developed Markets Equity Portfolio | Harding, Loevner Funds, Inc. | 2026-07-17 | portfolio type unproven | **unresolved** |
| Harding Loevner International Developed Markets Equity Portfolio | Harding, Loevner Funds, Inc. | 2026-07-17 | portfolio type unproven | **unresolved** |
| Harding Loevner International Developed Markets Equity Portfolio | Harding, Loevner Funds, Inc. | 2026-07-17 | portfolio type unproven | **unresolved** |
| JPMorgan National Municipal Income Fund | JPMorgan Trust I | NA | acquirer-ETF only; target type unproven | **unresolved** |
| JPMorgan National Municipal Income Fund | JPMorgan Trust I | NA | acquirer-ETF only; target type unproven | **unresolved** |
| Lazard Emerging Markets Opportunities Portfolio | Lazard Active ETF Trust | 2025-10-24 | neither side's type confirmed in evidence | **unresolved** |
| Lazard International Dynamic Equity Portfolio | Lazard Funds | 2025-04-30 | acquirer-ETF only; target type unproven | **unresolved** |
| Lazard US High Yield ETF | Lazard Active ETF Trust | 2026-11-06 | acquiring series of an ETF trust; target unclear | **unresolved** |
| Lazard US Systematic Small Cap Equity Portfolio | Lazard Active ETF Trust | 2025-09-12 | acquirer-ETF only; target type unproven | **unresolved** |
| Locorr Investment Trust | LOCORR INVESTMENT TRUST | NA | target type unproven | **unresolved** |
| Morgan Stanley Mortgage Securities Trust | Morgan Stanley Mortgage Securities Trust | 2025-08-01 | shares-on-NYSE only; MF->ETF unproven | **unresolved** |
| Morgan Stanley Mortgage Securities Trust | Morgan Stanley Mortgage Securities Trust | 2025-08-01 | acquirer-ETF only; target type unproven | **unresolved** |
| OTG Latin America Fund | ETF Opportunities Trust | 2025-07-11 | ETF-format mention; MF conversion not explicit | **unresolved** |
| OTG Latin America Fund | World Funds Trust | 2025-07-11 | ETF-format mention; MF conversion not explicit | **unresolved** |
| William Blair Emerging Markets Debt Fund | William Blair Funds | 2026-10-16 | acquirer-ETF only | **unresolved** |

## Adjudication provenance
Channel-level event/no_event calls were adjudicated upstream: deepseek v2-A primary, qwen targeted tiebreaker on 140 contested items, owner gate on the residual 11. 21 verdicts corrected (see ../t1_arb_evaluation.md, ../t1_arb_resolution.json). This step only consolidates filings into conversions; it makes no new event/no_event judgments.

## effective_date conflicts (latest-filed filing wins; all candidates listed)
- **FundX Conservative Upgrader Fund** — candidates ['2023-10-06', '2023-10-09'] across 6 filings (0000894189-23-004375, 0000894189-23-004374, 0000894189-23-005621, 0000894189-23-006958, 0000894189-23-006218, 0000894189-25-001842)
- **FundX Flexible Income Fund** — candidates ['2023-10-06', '2023-10-09'] across 6 filings (0000894189-23-004376, 0000894189-23-004374, 0000894189-23-005621, 0000894189-23-006958, 0000894189-23-006218, 0000894189-25-001842)
- **Matthews Korea Fund** — candidates ['2023-07-13', '2023-07-14'] across 6 filings (0001193125-23-149421, 0001193125-23-158748, 0001193125-23-074820, 0001193125-23-152967, 0001193125-23-149446, 0001193125-23-063051)
- **Guinness Atkinson Asia Pacific Dividend Builder Fund** — candidates ['2020-12-18', '2021-01-22', '2021-02-05', '2021-03-19', '2021-03-26'] across 8 filings (0001398344-20-018901, 0001398344-21-003295, 0001398344-21-003295, 0001398344-20-022229, 0001398344-21-000079, 0001398344-20-024788, 0001398344-21-005169, 0001398344-21-003663)
- **Guinness Atkinson Dividend Builder Fund** — candidates ['2020-12-18', '2021-01-22', '2021-02-05', '2021-03-19', '2021-03-26'] across 6 filings (0001398344-20-018901, 0001398344-20-022229, 0001398344-21-000079, 0001398344-20-024788, 0001398344-21-005169, 0001398344-21-003663)
- **JPMorgan International Research Enhanced Equity Fund** — candidates ['2022-05-20', '2022-06-09'] across 26 filings (0001193125-22-007703, 0001193125-22-010943, 0001193125-22-061688, 0001193125-22-010963, 0001193125-22-061697, 0001193125-22-010952, 0001193125-22-010961, 0001193125-22-061679, 0001193125-22-010937, 0001193125-22-010946, 0001193125-22-061690, 0001193125-22-061693, 0001193125-22-061717, 0001193125-22-010934, 0001193125-22-010964, 0001193125-22-010931, 0001193125-22-010957, 0001193125-22-010945, 0001193125-22-061699, 0001193125-22-061684, 0001193125-22-010947, 0001193125-22-061681, 0001193125-22-061644, 0001193125-22-061645, 0001193125-22-061639, 0001193125-22-050063)
- **Neuberger Berman Commodity Strategy Fund** — candidates ['2022-10-14', '2022-10-21'] across 4 filings (0000898432-22-000589, 0000898432-22-000590, 0000898432-22-000580, 0000898432-22-000519)
- **JPMorgan Equity Focus Fund** — candidates ['2023-07-27', '2023-07-28'] across 28 filings (0001193125-23-034482, 0001193125-23-034472, 0001193125-23-041853, 0001193125-23-034475, 0001193125-23-034487, 0001193125-23-034476, 0001193125-23-034478, 0001193125-23-034483, 0001193125-23-034461, 0001193125-23-034416, 0001193125-23-034417, 0001193125-23-067744, 0001193125-23-180670, 0001193125-23-180665, 0001193125-23-180673, 0001193125-23-180661, 0001193125-23-180667, 0001193125-23-180666, 0001193125-23-180668, 0001193125-23-180659, 0001193125-23-180672, 0001193125-23-185806, 0001193125-23-180664, 0001193125-23-066214, 0001193125-23-066212, 0001193125-23-102040, 0001193125-23-102286, 0001193125-23-067795)
- **JPMorgan High Yield Municipal Fund** — candidates ['2023-07-13', '2023-07-14'] across 29 filings (0001193125-23-034482, 0001193125-23-066224, 0001193125-23-066221, 0001193125-23-034472, 0001193125-23-034475, 0001193125-23-034487, 0001193125-23-034476, 0001193125-23-066217, 0001193125-23-066219, 0001193125-23-034478, 0001193125-23-034483, 0001193125-23-034461, 0001193125-23-034416, 0001193125-23-034417, 0001193125-23-180670, 0001193125-23-180665, 0001193125-23-180673, 0001193125-23-180661, 0001193125-23-180667, 0001193125-23-180666, 0001193125-23-180668, 0001193125-23-180659, 0001193125-23-180672, 0001193125-23-180664, 0001193125-23-066214, 0001193125-23-066212, 0001193125-23-102040, 0001193125-23-102286, 0001193125-23-067795)
- **JPMorgan Sustainable Municipal Income Fund** — candidates ['2023-07-13', '2023-07-14'] across 29 filings (0001193125-23-034482, 0001193125-23-066224, 0001193125-23-066221, 0001193125-23-034472, 0001193125-23-034475, 0001193125-23-034487, 0001193125-23-034476, 0001193125-23-066217, 0001193125-23-066219, 0001193125-23-034478, 0001193125-23-034483, 0001193125-23-034461, 0001193125-23-034416, 0001193125-23-034417, 0001193125-23-180670, 0001193125-23-180665, 0001193125-23-180673, 0001193125-23-180661, 0001193125-23-180667, 0001193125-23-180666, 0001193125-23-180668, 0001193125-23-180659, 0001193125-23-180672, 0001193125-23-180664, 0001193125-23-066214, 0001193125-23-066212, 0001193125-23-102040, 0001193125-23-102286, 0001193125-23-067795)
- **Pabrai Wagons Fund** — candidates ['2026-02-06', '2026-02-09'] across 6 filings (0000894189-25-016171, 0000894189-25-016172, 0000894189-25-015966, 0000894189-25-015990, 0000894189-25-019206, 0000894189-25-014440)
- **Akre Focus Fund** — candidates ['2025-09-26', '2025-10-24'] across 6 filings (0000894189-25-004319, 0000894189-25-004327, 0000894189-25-005135, 0000894189-25-005262, 0000894189-25-005009, 0000894189-25-004658)
- **AB Short Duration Income Portfolio** — candidates ['2024-06-07', '2024-07-12'] across 6 filings (0000919574-24-001857, 0000919574-24-000039, 0000919574-24-001517, 0000919574-24-001705, 0000919574-24-001732, 0001193125-24-019795)
- **AB Short Duration High Yield Portfolio** — candidates ['2024-06-07', '2024-07-12'] across 6 filings (0000919574-24-001857, 0000919574-24-000039, 0000919574-24-001517, 0000919574-24-001705, 0000919574-24-001732, 0001193125-24-019796)
- **Main BuyWrite Fund** — candidates ['2022-08-01', '2022-09-09'] across 4 filings (0001580642-22-004247, 0001580642-22-004227, 0001580642-22-004189, 0001580642-22-003158)

## Held back — needs_fulltext (owner spotcheck / full-filing fetch)
Conversions confirmed as events but with no closing date in the excerpt windows (typical of N-14s saying 'as soon as practicable'); the date lands in a later 497 or completed-conversion filing outside our windows.

Of these, **34** now carry an approximate timing (`effective_date_approx` + `date_precision`) recovered by Pass 1b; `effective_date` stays NA (reserved for verbatim ISO days).

- AXS All Terrain Fund — announce 2022-09-29 — approx 2022-Q4 (quarter) — 1 filing(s): 0001398344-22-019431
- AXS All Terrain Opportunity Fund — announce 2022-12-20 — approx 2023-Q1 (quarter) — 1 filing(s): 0001398344-22-024759
- Adaptive Growth Opportunities Fund — announce 2020-09-24 — 1 filing(s): 0001464413-20-000186
- Aggressive Investors 1 Fund — announce 2026-02-12 — 2 filing(s): 0001592900-26-002075, 0001592900-26-001600
- Angel Oak High Yield Opportunities Fund — announce 2023-12-29 — 2 filing(s): 0000894189-23-009430, 0000894189-24-000712
- Angel Oak Total Return Bond Fund — announce 2023-12-29 — 2 filing(s): 0000894189-23-009430, 0000894189-24-000712
- Arin Large Cap Theta Fund — announce 2022-12-20 — 2 filing(s): 0001829126-23-001258, 0001829126-22-020405
- Arin Large Cap Theta Fund — announce 2022-11-23 — 1 filing(s): 0001829126-22-019488
- Arin Large Cap Theta Fund — announce 2023-02-02 — 1 filing(s): 0001829126-23-001299
- Bahl & Gaynor Income Growth Fund — announce 2025-07-11 — approx 2025-Q4 (quarter) — 3 filing(s): 0000894189-26-000077, 0001398344-25-020089, 0001398344-25-013046
- Bahl & Gaynor Income Growth Fund — announce 2025-08-22 — approx 2025-Q4 (quarter) — 2 filing(s): 0000894189-25-016540, 0000894189-25-005749
- BlackRock Mortgage-Backed Securities Fund — announce 2025-06-05 — 4 filing(s): 0001193125-25-185189, 0001193125-25-183341, 0001193125-25-136795, 0001193125-25-136792
- BlackRock Mortgage-Backed Securities Fund — announce 2025-06-06 — 1 filing(s): 0001193125-25-136953
- Dividend Performers — announce 2022-02-22 — 1 filing(s): 0001387131-22-002287
- Dividend Performers — announce 2021-11-05 — 5 filing(s): 0000894189-22-001072, 0000894189-21-009051, 0000894189-22-001019, 0000894189-22-001081, 0000894189-22-000871
- DoubleLine Income Fund — announce 2025-08-29 — approx 2026-Q1 (quarter) — 2 filing(s): 0001193125-25-192863, 0001193125-25-192891
- DoubleLine Securitized Credit Fund — announce 2025-10-15 — 2 filing(s): 0001193125-25-240418, 0001193125-25-283237
- FPA Queens Road Value Fund — announce 2025-10-14 — approx 2026-Q1 (quarter) — 4 filing(s): 0001104659-25-124171, 0001104659-25-124181, 0001213900-25-125371, 0001104659-26-007886
- Fidelity Municipal Core Plus Bond Fund — announce 2024-11-15 — 1 filing(s): 0001133228-24-010291
- Fidelity U.S. Low Volatility Equity Fund — announce 2024-11-29 — 1 filing(s): 0000945908-25-000554
- Fort Pitt Capital Total Return Fund — announce 2026-01-20 — 2 filing(s): 0001580642-26-001860, 0001580642-26-000320
- Gabelli Media Mogul Fund — announce 2025-12-16 — 1 filing(s): 0001999371-25-020449
- Green Owl Intrinsic Value Fund — announce 2022-08-24 — 3 filing(s): 0001580642-22-004263, 0001580642-22-005431, 0001580642-22-005547
- Impax Global Sustainable Infrastructure Fund — announce 2025-11-14 — approx 2026-Q1 (quarter) — 3 filing(s): 0001398344-25-022435, 0001398344-25-020997, 0001398344-25-022636
- Kinetics Alternative Income Fund — announce 2022-03-10 — 2 filing(s): 0000894189-22-009248, 0000894189-22-008962
- Kinetics Alternative Income Fund — announce 2022-03-10 — 2 filing(s): 0000894189-22-009226, 0000894189-22-007685
- Kinetics Medical Fund — announce 2022-03-10 — 2 filing(s): 0000894189-22-009248, 0000894189-22-008962
- Kinetics Medical Fund — announce 2022-03-10 — 2 filing(s): 0000894189-22-009226, 0000894189-22-007685
- Kinetics Multi-Disciplinary Income Fund — announce 2022-03-10 — 1 filing(s): 0000894189-22-007685
- Kinetics Multi-Disciplinary Income Fund — announce 2022-03-10 — 1 filing(s): 0000894189-22-008962
- Logan Capital Large Cap Growth Fund — announce 2021-09-23 — 2 filing(s): 0000894189-22-002770, 0000894189-22-001943
- Marathon Value Portfolio — announce 2022-08-24 — 3 filing(s): 0001580642-22-004262, 0001580642-22-005429, 0001580642-22-005548
- Mast Managed Futures Strategy Fund — announce 2026-01-20 — approx 2026-Q2 (quarter) — 4 filing(s): 0001213900-26-021666, 0001213900-26-022128, 0001213900-26-022464, 0001213900-26-041534
- Matrix Advisors Value Fund — announce 2025-02-13 — 1 filing(s): 0001592900-25-000335
- Metropolitan West Floating Rate Income Fund — announce 2024-06-12 — approx 2024-Q4 (quarter) — 3 filing(s): 0001829126-24-004764, 0001829126-24-004140, 0001829126-24-004688
- Metropolitan West Investment Grade Credit Fund — announce 2024-06-12 — approx 2024-Q4 (quarter) — 3 filing(s): 0001829126-24-004764, 0001829126-24-004140, 0001829126-24-004688
- (fund_name NA) — announce 2025-01-03 — 1 filing(s): 0001133228-25-000086
- OTG Latin America Fund — announce 2025-03-28 — 1 filing(s): 0001999371-25-004109
- PGIM Jennison Focused Value Fund — announce 2026-06-29 — approx 2026-Q4 (pending) — 1 filing(s): 0001104659-26-078948
- Preferred-Plus — announce 2022-02-22 — 1 filing(s): 0001387131-22-002287
- Preferred-Plus — announce 2021-11-05 — 5 filing(s): 0000894189-22-001072, 0000894189-21-009051, 0000894189-22-001019, 0000894189-22-001081, 0000894189-22-000871
- Putnam California Tax Exempt Income Fund — announce 2025-05-16 — approx 2025-Q4 (quarter) — 22 filing(s): 0001193125-25-164481, 0001193125-25-164479, 0001193125-25-164486, 0001193125-25-164491, 0001193125-25-164487, 0001193125-25-164493, 0001193125-25-164490, 0001193125-25-164480, 0001193125-25-154980, 0001193125-25-154979, 0001193125-25-154975, 0001193125-25-154974, 0001193125-25-154977, 0001193125-25-154981, 0001193125-25-154973, 0001193125-25-154970, 0001193125-25-154982, 0001193125-25-154976, 0001193125-25-154978, 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam Income Fund — announce 2026-05-21 — approx 2027-Q1 (pending) — 3 filing(s): 0001193125-26-239670, 0001193125-26-239660, 0001193125-26-239655
- Putnam Massachusetts Tax Exempt Income Fund — announce 2025-05-16 — approx 2025-Q4 (quarter) — 22 filing(s): 0001193125-25-164481, 0001193125-25-164489, 0001193125-25-164486, 0001193125-25-164491, 0001193125-25-164487, 0001193125-25-164493, 0001193125-25-164490, 0001193125-25-164480, 0001193125-25-154980, 0001193125-25-154979, 0001193125-25-154975, 0001193125-25-154974, 0001193125-25-154977, 0001193125-25-154981, 0001193125-25-154973, 0001193125-25-154970, 0001193125-25-154982, 0001193125-25-154976, 0001193125-25-154978, 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam Minnesota Tax Exempt Income Fund — announce 2025-05-16 — approx 2025-Q4 (quarter) — 21 filing(s): 0001193125-25-164481, 0001193125-25-164486, 0001193125-25-164491, 0001193125-25-164487, 0001193125-25-164493, 0001193125-25-164490, 0001193125-25-164480, 0001193125-25-154980, 0001193125-25-154979, 0001193125-25-154975, 0001193125-25-154974, 0001193125-25-154977, 0001193125-25-154981, 0001193125-25-154973, 0001193125-25-154970, 0001193125-25-154982, 0001193125-25-154976, 0001193125-25-154978, 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam Mortgage Opportunities Fund — announce 2026-05-21 — approx 2027-Q1 (pending) — 2 filing(s): 0001193125-26-239624, 0001193125-26-239616
- Putnam Mortgage Securities Fund — announce 2026-05-21 — approx 2027-Q1 (pending) — 4 filing(s): 0001193125-26-239670, 0001193125-26-239660, 0001193125-26-239666, 0001193125-26-239655
- Putnam New Jersey Tax Exempt Income Fund — announce 2025-05-16 — approx 2025-Q4 (quarter) — 21 filing(s): 0001193125-25-164481, 0001193125-25-164486, 0001193125-25-164491, 0001193125-25-164487, 0001193125-25-164493, 0001193125-25-164490, 0001193125-25-164480, 0001193125-25-154980, 0001193125-25-154979, 0001193125-25-154975, 0001193125-25-154974, 0001193125-25-154977, 0001193125-25-154981, 0001193125-25-154973, 0001193125-25-154970, 0001193125-25-154982, 0001193125-25-154976, 0001193125-25-154978, 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam New York Tax Exempt Income Fund — announce 2025-05-16 — approx 2025-Q4 (quarter) — 21 filing(s): 0001193125-25-164481, 0001193125-25-164486, 0001193125-25-164491, 0001193125-25-164487, 0001193125-25-164493, 0001193125-25-164490, 0001193125-25-164480, 0001193125-25-154980, 0001193125-25-154979, 0001193125-25-154975, 0001193125-25-154974, 0001193125-25-154977, 0001193125-25-154981, 0001193125-25-154973, 0001193125-25-154970, 0001193125-25-154982, 0001193125-25-154976, 0001193125-25-154978, 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam Ohio Tax Exempt Income Fund — announce 2025-05-16 — approx 2025-Q4 (quarter) — 18 filing(s): 0001193125-25-164492, 0001193125-25-164486, 0001193125-25-164491, 0001193125-25-164487, 0001193125-25-154980, 0001193125-25-154979, 0001193125-25-154975, 0001193125-25-154974, 0001193125-25-154977, 0001193125-25-154981, 0001193125-25-154973, 0001193125-25-154970, 0001193125-25-154982, 0001193125-25-154976, 0001193125-25-154978, 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam Pennsylvania Tax Exempt Income Fund — announce 2025-05-16 — approx 2025-Q4 (quarter) — 4 filing(s): 0001193125-25-154970, 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam Short Duration Bond Fund — announce 2026-05-21 — approx 2027-Q1 (pending) — 2 filing(s): 0001193125-26-239660, 0001193125-26-292843
- Putnam Short-Term Municipal Income Fund — announce 2025-05-16 — approx 2025-Q4 (quarter) — 4 filing(s): 0001193125-25-164482, 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam Tax Exempt Income Fund — announce 2025-06-27 — approx 2025-Q4 (quarter) — 3 filing(s): 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- Putnam Tax-Free High Yield Fund — announce 2025-06-27 — approx 2025-Q4 (quarter) — 3 filing(s): 0001193125-25-151504, 0001193125-25-173703, 0001193125-25-174220
- RiverNorth Core Opportunity Fund — announce 2025-06-10 — 3 filing(s): 0001999371-25-009259, 0001999371-25-008948, 0001999371-25-007562
- Small-Cap Value Fund — announce 2026-02-12 — 2 filing(s): 0001592900-26-002075, 0001592900-26-001600
- Sterling Capital Short Duration Bond Fund — announce 2025-11-19 — approx 2026-Q1 (quarter) — 2 filing(s): 0001398344-26-003185, 0001398344-26-000829
- Sterling Capital Ultra Short Bond Fund — announce 2025-11-19 — approx 2026-Q1 (quarter) — 2 filing(s): 0001398344-26-003185, 0001398344-26-000829
- TCW Artificial Intelligence Equity Fund — announce 2024-01-17 — 1 filing(s): 0001829126-24-000240
- TCW High Yield Bond Fund — announce 2024-06-12 — approx 2024-Q4 (quarter) — 3 filing(s): 0001829126-24-004764, 0001829126-24-004140, 0001829126-24-004688
- TCW MetWest Corporate Bond Fund — announce 2024-10-15 — approx 2024-Q4 (quarter) — 1 filing(s): 0001829126-24-006799
- TCW Metropolitan West Corporate Bond Fund — announce 2024-09-12 — approx 2024-Q4 (quarter) — 1 filing(s): 0001829126-24-006253
- TCW New America Premier Equities Fund — announce 2024-01-17 — 1 filing(s): 0001829126-24-000240
- Thrivent Core International Equity Fund — announce 2026-03-10 — 1 filing(s): 0001193125-26-099572
- Thrivent Core International Equity Fund — announce 2026-04-16 — 1 filing(s): 0001193125-26-158201
- Tortoise Energy Infrastructure and Income Fund — announce 2025-02-19 — approx 2025-Q2 (quarter) — 2 filing(s): 0001013762-25-002918, 0001213900-25-015352
- Towle Value Fund — announce 2025-12-04 — 2 filing(s): 0001592900-26-000271, 0001592900-25-004446
- Ultra-Small Company Market Fund — announce 2026-02-12 — 2 filing(s): 0001592900-26-002075, 0001592900-26-001600
- WCM Developing World Equity Fund — announce 2024-06-07 — approx 2024-Q4 (quarter) — 3 filing(s): 0001445546-24-004213, 0001445546-24-005592, 0001445546-24-005385
- WCM International Equity Fund — announce 2024-06-07 — approx 2024-Q4 (quarter) — 3 filing(s): 0001445546-24-005387, 0001445546-24-005594, 0001445546-24-004215
- Water Island Long/Short Fund — announce 2021-05-04 — approx 2021-Q3 (quarter) — 4 filing(s): 0001104659-21-097692, 0001104659-21-076413, 0001104659-21-061833, 0001104659-21-061841
- William Blair Emerging Markets Debt Fund — announce 2026-06-04 — 2 filing(s): 0001193125-26-261098, 0001193125-26-261100
