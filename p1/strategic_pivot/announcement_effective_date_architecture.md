# Announcement and effective-date architecture

Wrapper events contain several economically distinct dates. Collapsing them into one `event_date` mixes information, shareholder choice, portfolio operations, and exchange trading.

## Required clocks

| Clock | Definition | Economic content | Primary use |
|---|---|---|---|
| `filing_date` | First public SEC filing that identifies the transaction | Earliest formal public signal | information/anticipation |
| `public_announcement_date` | First sponsor release or shareholder notice with transaction identity | Broad investor awareness | announcement response |
| `shareholder_vote_date` | Approval date when applicable | Resolution of transaction uncertainty | discrete information event |
| `last_mutual_trade_or_purchase_date` | Last date predecessor shares can be bought/traded under stated terms | Clientele and flow transition | fund-flow architecture |
| `legal_effective_date` | Merger/conversion becomes legally effective | Legal wrapper changes | fund accounting treatment |
| `first_etf_trading_date` | First verified exchange trading session | Secondary-market/arbitrage channel switches on | main market-mechanism treatment |
| `first_creation_redemption_date` | First verified AP creation/redemption availability | Primary-market ETF mechanism | first-stage mechanism |

## Coding rules

1. Record each date with source URL/accession, quoted factual basis, precision class, and verification status. Never replace an observed date with a proposed date.
2. If first ETF trading differs from legal effectiveness, fund-level accounting uses legal effectiveness and market-mechanism outcomes use first trading.
3. A registered ticker or effective prospectus does not prove operations commenced. Pending events remain untreated until first trading or an explicit sponsor launch is verified.
4. For conversion outcomes, use the last mutual-fund observation as `-1` and the first successor observation as `0`; preserve any operational gap.
5. For share-class additions, existing mutual classes remain controls only within the same portfolio accounting system; their returns are mechanically shared and cannot be treated as independent outcome observations.

## Windows

- Long anticipation: `[-180,-31]` calendar days before public announcement.
- Announcement: `[-1,+1]` trading days for daily outcomes; intraday only if licensed data exist.
- Implementation gap: day after announcement through day before first ETF trading.
- Effective/launch: `[0,+5]` trading days around first ETF trading.
- Medium post: months `[+1,+12]`, excluding the partial launch month in monthly specifications.

If announcement and launch are within five trading days, the event cannot separately identify information and machinery effects; classify it as bundled rather than selecting a convenient clock. All window changes require an outcome-blind amendment.
