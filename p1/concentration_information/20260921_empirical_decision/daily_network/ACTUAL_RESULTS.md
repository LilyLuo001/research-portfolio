# Daily and issuer-specific network results

Status: completed 2023-H1 development analysis with a finite issuer-SIC repair. These are descriptive development results, not a causal or confirmatory test.

## Sample actually analyzed

- 15 issuer-date events on 11 unique dates, forming 10 overlapping two-session event blocks.
- 5,025 broad top-500 receiver-date observations with an event response and at least two eligible controls.
- 6,658 observed-positive PURE_D issuer-receiver-event rows, covering all 490 rank-9--500 network receivers.
- No missing issuer-receiver pair was imputed to zero.
- The focal same-SIC2 subset has 514 rows and 142 receivers. All eight top issuers have a date-valid 2022-12-30 SIC after the repair; the adjusted design is full rank.

## Daily nonmechanical facts

The primary unsigned statistic is the mean stock-level absolute response, not the absolute return of an aggregated basket. A bounded after-pilot supplement also constructs exact same-receiver-mask, same-weight aggregated event/control baskets for 48 matched comparisons. Equal-weight absolute basket returns average 0.642% at events versus 1.059% in controls, a -0.418 percentage-point difference. Fixed weights give 0.592% versus 0.952%, a -0.359 percentage-point difference. No interval is estimated because shared-control dependence is unresolved; this supplement does not alter the primary specification.

Across 10 development blocks, equal-weight signed event response averaged -0.096%, versus +0.412% in matched controls, a -0.508 percentage-point difference. The heuristic event-block interval is [-1.059%, -0.021%]. Fixed 2022-12-30 market-cap weights give a -0.364 percentage-point difference with interval [-0.885%, +0.091%]. These signed averages can mix positive and negative earnings news and do not identify propagation direction.

Mean stock-level absolute response was 1.714% at events versus 1.888% in controls under equal weights, a -0.173 percentage-point difference with interval [-0.498%, +0.225%]. Fixed weights give -0.239 percentage points, interval [-0.515%, +0.102%]. Excluding the two blocks overlapping the limited named macro calendar leaves the same qualitative result. Thus this development sample does not show extra broad unsigned repricing around the focal announcements; if anything, point estimates are lower than controls, with intervals spanning zero.

## Issuer-specific reported-weight connection

The primary network outcome is the receiver's absolute event return minus its mean absolute control return. In all observed-positive issuer-receiver pairs, a one-SD increase in log PURE_D pair strength is associated with -0.084 percentage points in the event-FE specification (heuristic interval [-0.180%, +0.010%]) and -0.183 percentage points after pre-size, liquidity and focal-industry controls ([-0.360%, +0.012%]). Both remain negative in every leave-one-block estimate, but neither interval excludes zero.

Within focal same-SIC2 support, the corresponding coefficient is +0.243 percentage points ([+0.115%, +0.372%]) without additional controls and +0.260 percentage points ([-0.007%, +0.477%]) with size and liquidity controls. Both remain positive in all leave-one-block estimates. The adjusted interval nevertheless crosses zero, the subset is only 514 rows, and the dependence correction below is incomplete. This is at most a conditional same-industry association worth testing in untouched data.

Signed-response coefficients are not given a propagation-direction interpretation because signed news was not validated. Raw absolute-return slopes are secondary and can reflect persistent volatility.

The optional same-date bundle exposure (sum of observed pair strengths to all same-date announcers) was not run. All reported network coefficients are focal issuer-receiver specifications.

## Precision and dependence

Forty distinct control windows were used. Of 18,186 receiver-control-window keys, 3,151 were reused across focal dates, accounting for 6,302 rows. Combining event and control calendar support leaves only two connected components; the largest contains 10 of 11 event dates. Therefore the printed event-overlap-block bootstrap intervals are heuristic and do not fully adjust for shared-control dependence. They do not support a formal precision, p-value, MDE or power claim.

The input audit found zero nonadjacent prior-cap lags and zero missing date-valid share-class source-date rows across 39,581 required company-dates. It supports adjacency and source-date presence only; because the audit did not read returns, it is not a certification that every class-day had nonmissing RET or DLRET.

## Known limits and execution deviations

- Announcers whose event windows overlap were excluded, weights were fixed before 2023, and receiver own-EPS dates inside the date-only information span were excluded. Mechanical direct issuer contribution is therefore not the broad result being reported.
- A date-only rule cannot exclude an own-company announcement issued after the preceding trading day's close; the sample is not proven fully own-news-free.
- The macro calendar covers only CPI, Employment Situation and FOMC statements.
- The baseline holding reports can be stale relative to the 2022-12-30 network cutoff, and pair strength is unitless reported-weight coholding.
- During the full run, the full-year delisting file was loaded before the referee caught the missing source predicate. H2 delisting-return values were loaded into memory but could not join the H1-only CRSP rows and were not modeled, exported or inspected. Final code applies an H1 source predicate. Consequently, the claim is “no H2 response entered an estimate,” not “every H2 response-bearing source value stayed unread.”
- Existing work already studies ETF-mediated earnings information transfer. These results neither establish novelty nor show that a long-run rise in concentration changed price discovery.

## Scientific decision for A/B

There is no positive broad daily nonmechanical repricing fact in this development block. The full network sample also does not show larger unsigned excess response at higher financial connection. The only potentially useful signal is the positive same-industry connection slope; it remains positive but loses even heuristic interval separation from zero after controls and lacks valid dependence-adjusted precision. It should be treated as a narrow hypothesis for a prospectively frozen untouched sample, not evidence of an ETF mechanism.
