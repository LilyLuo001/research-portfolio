# Independent review

## Verdict

**PASS_WITH_LIMITATIONS.** After one material implementation error was found and corrected, the current aggregate outputs reproduce exactly from an independent raw-DBN decoder and a separate two-pointer range-count implementation. The current `COACTIVITY_ONLY` decision is supported: AAPL has positive near-synchronous coactivity in every RTH and ordinary-control venue/axis cell, but every matched ordinary control exceeds its RTH window; XOM is approximately zero; and the announcement-window results are sparse or timestamp-sensitive. These facts do not identify stock-to-ETF or ETF-to-stock leadership, an earnings-specific mechanism, or an entire-basket effect.

There are no unresolved numerical discrepancies in the corrected main counts or five-second response summaries. A stale XOM response range was also corrected in `RESULTS.md`: the current `0–7` usable trades per instrument/venue cell agrees with the corrected response output. The remaining limitations are scientific and presentational: the sample is two securities on two direct venues and three events; announcement clocks are minute candidates; `PAIR_COUNTS.csv` reports `UNKNOWN_EITHER` near counts but leaves its background/excess cells blank; and unknown-side trades cannot have a signed response identity. This review supplies the missing independent unknown-background counts below.

## Independent method and the corrected material error

I accessed the 18 native files in `/scratch/qluo/native_tick_pilot_20260922` on SCC and decoded them without importing or calling the production analyzer's count or response functions. The independent implementation is `code/independent_scc_review.py`. It:

- maps dated instrument IDs from each DBN's metadata;
- orders messages separately by event time and receive time, with sequence and original file order as tie-breakers;
- treats only `T` as an economic trade, uses native `B/A` aggressor side first, and applies midpoint fallback only to native `N` using the last valid prior message on that same axis;
- uses manifest-derived half-open analysis bounds `[request start + 120 seconds, request end - 65 seconds)` while retaining the full quote arrays for state initialization and response endpoints;
- counts half-open time ranges with independently written monotone two-pointer scans rather than `searchsorted` or the production functions; and
- independently recomputes five-second as-of quote responses and the spread identity.

The first production run counted the full purchased support interval instead of the fixed analysis interval. It therefore included the two-minute state lead and 65-second response tail as trade centers. I reported this immediately. The production code was repaired and all aggregates/figures were rerun. Raw purchased trades were `513,606`; corrected fixed-window trades are `482,020 = 264,831 stock + 217,189 SPY`, with `31,586` support-only trades excluded.

Representative pre-correction to corrected event-axis rates per 1,000 stock trades were:

| Cell | Initial | Corrected |
|---|---:|---:|
| AAPL Feb RTH ARCX / XNAS | 18.30 / 9.06 | 16.759655 / 9.279780 |
| AAPL Feb control ARCX / XNAS | 36.77 / 20.78 | 37.732566 / 20.995842 |
| AAPL Aug RTH ARCX / XNAS | 20.92 / 15.27 | 22.146694 / 16.332718 |
| AAPL Aug control ARCX / XNAS | 67.53 / 54.59 | 64.078762 / 54.647003 |

The repair changes the numbers but not the ranking or decision. Every value below refers to the corrected outputs.

## Raw source semantics, filters, and direction

The raw action totals independently reproduce as `6,107,724 A`, `5,602,968 C`, `513,606 T`, `74,384 M`, and `70 F`, totaling `12,298,752` MBP-1 records. XNAS contains `276,827 T` and no `F`; ARCX contains `236,779 T` and all `70 F`. The official Databento action semantics define `T` as an aggressing order trade and `F` as a resting-order fill, while trade side `B/A` denotes buy/sell aggressor. Counting `T` and excluding `F` is therefore consistent with the prompt's no-double-count rule and the documented source semantics ([MBP-1 schema](https://databento.com/docs/schemas-and-data-formats/mbp-1), [common actions, sides, and flags](https://databento.com/docs/standards-and-conventions/common-fields-enums-types)).

Raw native `T` sides also reproduce exactly:

| Dataset | B | A | N | Total T |
|---|---:|---:|---:|---:|
| XNAS.ITCH | 116,397 | 115,043 | 45,387 | 276,827 |
| ARCX.PILLAR | 97,451 | 109,587 | 29,741 | 236,779 |
| Total | 213,848 | 224,630 | 75,128 | 513,606 |

Across the purchased files, native side classifies `438,478`, strict prior-midpoint fallback classifies `54,347`, and `20,781` remain unknown. Within the corrected analysis windows the corresponding counts are `411,837` (85.44%), `50,457` (10.47%), and `19,726` (4.09%), exactly matching `QUOTE_DIAGNOSTICS.csv`. Event- and receive-axis source totals are identical, though timestamps and pair matches differ. All unknown cases in this sample are at the prior midpoint; none was tick-test filled.

All `12,298,752` messages have a valid positive, non-crossed venue BBO under the implemented rule. Bit tests independently find zero `F_BAD_TS_RECV` records and zero `F_MAYBE_BAD_BOOK` records. Flag value `130` is correctly treated as a combination of bits rather than as a standalone sale condition.

## All 18 event-time count reconstructions

Intervals are half-open: near is `[-20,+20)` microseconds and background is `[-1200,-1000) ∪ [1000,1200)` microseconds. Entries `n / bg` are independent near/background pair counts. `Unknown` means at least one trade has unknown direction. Excess per 1,000 is based on all pairs: `near - 0.1 × background`.

| Window | Venue | Stock / SPY trades | ALL n / bg | BB n / bg | SS n / bg | BS n / bg | SB n / bg | Unknown n / bg | Excess / 1k |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AAPL_AUG | ARCX | 11,891 / 644 | 35 / 136 | 21 / 19 | 13 / 75 | 1 / 18 | 0 / 24 | 0 / 0 | 1.799680 |
| AAPL_AUG | XNAS | 8,100 / 419 | 16 / 63 | 6 / 0 | 9 / 53 | 1 / 7 | 0 / 3 | 0 / 0 | 1.197531 |
| AAPL_AUG_CTRL | ARCX | 7,110 / 17,173 | 536 / 804 | 286 / 185 | 198 / 253 | 24 / 249 | 2 / 56 | 26 / 61 | 64.078762 |
| AAPL_AUG_CTRL | XNAS | 13,697 / 15,380 | 814 / 655 | 239 / 250 | 470 / 187 | 17 / 106 | 48 / 86 | 40 / 26 | 54.647003 |
| AAPL_AUG_RTH | ARCX | 21,037 / 16,952 | 530 / 641 | 231 / 157 | 247 / 341 | 1 / 59 | 15 / 68 | 36 / 16 | 22.146694 |
| AAPL_AUG_RTH | XNAS | 37,930 / 17,679 | 719 / 995 | 325 / 340 | 323 / 310 | 3 / 75 | 38 / 226 | 30 / 44 | 16.332718 |
| AAPL_FEB | ARCX | 13,615 / 1,067 | 103 / 7,830 | 0 / 8 | 8 / 7,786 | 0 / 32 | 95 / 4 | 0 / 0 | -49.944914 |
| AAPL_FEB | XNAS | 8,939 / 532 | 2 / 631 | 1 / 7 | 1 / 488 | 0 / 132 | 0 / 4 | 0 / 0 | -6.835216 |
| AAPL_FEB_CTRL | ARCX | 7,471 / 19,973 | 328 / 461 | 79 / 110 | 237 / 255 | 3 / 43 | 0 / 42 | 9 / 11 | 37.732566 |
| AAPL_FEB_CTRL | XNAS | 18,999 / 14,369 | 466 / 671 | 148 / 234 | 261 / 216 | 9 / 72 | 12 / 118 | 36 / 31 | 20.995842 |
| AAPL_FEB_RTH | ARCX | 32,083 / 35,771 | 707 / 1,693 | 185 / 543 | 453 / 793 | 25 / 175 | 26 / 124 | 18 / 58 | 16.759655 |
| AAPL_FEB_RTH | XNAS | 68,493 / 21,686 | 909 / 2,734 | 250 / 537 | 556 / 1,623 | 23 / 198 | 36 / 271 | 44 / 105 | 9.279780 |
| XOM_JAN | ARCX | 32 / 109 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0.000000 |
| XOM_JAN | XNAS | 90 / 33 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0.000000 |
| XOM_JAN_CTRL | ARCX | 1,436 / 16,301 | 4 / 27 | 3 / 11 | 0 / 6 | 1 / 0 | 0 / 0 | 0 / 10 | 0.905292 |
| XOM_JAN_CTRL | XNAS | 3,716 / 10,914 | 4 / 49 | 3 / 16 | 1 / 20 | 0 / 8 | 0 / 4 | 0 / 1 | -0.242196 |
| XOM_JAN_RTH | ARCX | 3,271 / 16,046 | 2 / 57 | 0 / 28 | 2 / 15 | 0 / 6 | 0 / 4 | 0 / 4 | -1.131153 |
| XOM_JAN_RTH | XNAS | 6,921 / 12,141 | 9 / 69 | 0 / 19 | 7 / 33 | 1 / 7 | 0 / 5 | 1 / 5 | 0.303424 |

For all 18 files, all event/receive/periodic all-pair counts and the `BB`, `SS`, `BS`, and `SB` near/background/excess decompositions match the refreshed `PAIR_COUNTS.csv` exactly. Published `UNKNOWN_EITHER` near counts also match exactly. The table's unknown background counts are independently derived because those cells are blank in the production CSV.

## Event-time, receive-time, and periodic sensitivity

These are independently reconstructed all-pair excess rates per 1,000 stock trades:

| Window | Venue | Event | Receive | Periodic exclusion |
|---|---|---:|---:|---:|
| AAPL_AUG | ARCX | 1.799680 | 1.824910 | 1.369281 |
| AAPL_AUG | XNAS | 1.197531 | 1.197531 | 0.125510 |
| AAPL_AUG_CTRL | ARCX | 64.078762 | 40.773558 | 55.961675 |
| AAPL_AUG_CTRL | XNAS | 54.647003 | 26.480251 | 50.168919 |
| AAPL_AUG_RTH | ARCX | 22.146694 | 16.062176 | 18.334546 |
| AAPL_AUG_RTH | XNAS | 16.332718 | 14.305299 | 14.715900 |
| AAPL_FEB | ARCX | -49.944914 | -2.952626 | 0.841130 |
| AAPL_FEB | XNAS | -6.835216 | 22.284372 | 0.145666 |
| AAPL_FEB_CTRL | ARCX | 37.732566 | 22.165707 | 36.291023 |
| AAPL_FEB_CTRL | XNAS | 20.995842 | 15.263961 | 17.040450 |
| AAPL_FEB_RTH | ARCX | 16.759655 | 8.166319 | 17.665010 |
| AAPL_FEB_RTH | XNAS | 9.279780 | 6.691195 | 8.715932 |
| XOM_JAN | ARCX | 0.000000 | 0.000000 | 0.000000 |
| XOM_JAN | XNAS | 0.000000 | 0.000000 | 0.000000 |
| XOM_JAN_CTRL | ARCX | 0.905292 | -0.557103 | 0.360685 |
| XOM_JAN_CTRL | XNAS | -0.242196 | -0.242196 | -0.137552 |
| XOM_JAN_RTH | ARCX | -1.131153 | -0.733721 | 0.235386 |
| XOM_JAN_RTH | XNAS | 0.303424 | 0.245629 | -0.109190 |

The claims in `RESULTS.md` follow: every AAPL RTH/control cell stays positive on both axes; every AAPL control exceeds its matched RTH cell on the event axis, receive axis, and periodic exclusion; and February's announcement result is unstable across axis/exclusion. The production 100-microsecond and 1-millisecond tables also retain the AAPL control-above-RTH ordering in all four matched venue/event cells. XOM counts are too small and too close to zero for a directional mechanism claim.

## Explicit bounded enumeration and half-open endpoints

For the busiest one-second slice selected mechanically within AAPL February RTH/XNAS, the independent code explicitly enumerated every ordered stock-SPY pair within the ±1.2 millisecond candidate span. The slice contains 78 stock trades, 71 SPY trades, and 804 candidate pairs. All 804 `(stock index, SPY index)` keys are unique: duplicate count is zero. Explicit enumeration gives 75 near pairs and 117 background pairs; the two-pointer method gives exactly 75 and 117.

No actual pair in that slice lands exactly at -20 or +20 microseconds. A separate boundary check with offsets exactly `-20,000 ns` and `+20,000 ns` returns one pair, confirming inclusion of the lower endpoint and exclusion of the upper endpoint for `[-20,+20)`.

## Quote-response reconstruction

I independently recomputed corrected five-second paired/unpaired results using full quote-support arrays but fixed-window trade centers. All 72 five-second rows (18 files × 2 instruments × 2 groups) match the production `TRADE_RESPONSE.csv` counts and means within `1e-10` bp. The decisive AAPL cells are:

| Window/venue | Stock paired n, bp | Stock unpaired bp | SPY paired n, bp | SPY unpaired bp |
|---|---:|---:|---:|---:|
| Feb RTH ARCX | 247, 1.752625 | 1.748672 | 310, 1.130063 | 0.201620 |
| Feb RTH XNAS | 416, 2.626157 | 1.765292 | 373, 0.778763 | 0.204955 |
| Feb control ARCX | 122, 1.327586 | 0.682923 | 156, 0.651175 | 0.195833 |
| Feb control XNAS | 230, 0.907722 | 0.523794 | 145, 0.428407 | 0.168059 |
| Aug RTH ARCX | 133, 0.780343 | 0.357378 | 181, 0.519043 | 0.164448 |
| Aug RTH XNAS | 160, 0.422344 | 0.462545 | 248, 0.561968 | 0.147923 |
| Aug control ARCX | 134, 0.712840 | 0.385774 | 241, 0.389630 | 0.168314 |
| Aug control XNAS | 187, 0.460484 | 0.391693 | 220, 1.025426 | 0.168626 |

Thus paired SPY means exceed unpaired means in all eight cells, while paired stock means do so in seven of eight. The same association on controls prevents an earnings-specific or ETF-transmission interpretation.

I evaluated `effective spread = realized spread + 2 × signed mid change` for all `462,294` finite signed five-second responses; the independent maximum absolute error is `1.14e-13 bp`. Targeted audits include 20 each of native/prior-timestamp, native/same-timestamp, midpoint/prior-timestamp, and midpoint/same-timestamp identities; their sample maximum is `1.78e-15 bp`. I also audited 20 unknown/prior-timestamp and 20 unknown/same-timestamp cases. They remain at-mid unknown and are correctly excluded from signed-response identities rather than imputed. Same-time prior messages are used only when sequence/file order establishes that they precede the trade.

## Security, routing, and final scientific assessment

Raw DBNs remain on SCC. No `.dbn` or `.dbn.zst` file is present in the local result directory, and the code contains only an environment-variable reference—not a credential value. The local exports are aggregate counts, statistics, figures, manifests, and receipts. The `$1.365348368882` API quote is correctly described as a quote; an account debit remains `NOT_OBSERVED`.

Requested reviewer routing was `gpt-5.6-sol / high`; backend routing telemetry was unavailable and is therefore **`NOT_OBSERVED`**. No nested delegation, commit, or push was performed.

Final assessment: the corrected engineering pipeline is usable, and `COACTIVITY_ONLY` is the appropriate interpretation. The results establish observable fast coactivity in AAPL but show that ordinary control hours are more coactive than the matched post-earnings hours. They do not establish price-discovery direction, event causation, ETF arbitrage, a full-basket mechanism, or concentration causality. Any larger panel must be a predeclared interaction/difference-in-differences design rather than an extrapolation from these three cases.
