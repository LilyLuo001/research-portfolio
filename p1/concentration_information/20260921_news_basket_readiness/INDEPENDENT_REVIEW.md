# Independent finite review

Date: 2026-09-21. Final disposition: **`HOLD_DATA + HOLD_METHOD`**. The
implemented bounded pieces receive only `PASS_SOURCE_ADAPTER_LOGIC` and
`PASS_SYNTHETIC_IMPLEMENTED_MODULES`. This is not a PASS for the full method,
data readiness, empirical research, contribution, causal interpretation, or
production inference.

The review was limited to the approved
[`NEXT_EXECUTION_PROMPT.md`](../20260921_price_discovery_method/NEXT_EXECUTION_PROMPT.md),
this stage's source/method artifacts, and explicitly named permitted local
metadata. It did not reconnect to SCC or WRDS, acquire a new source, read
financial/quote/return/outcome values, reopen old H2/PIT work, or repeat the
literature audit. Requested Sol/high dispatch was accepted; actual backend
telemetry remains `NOT_OBSERVED` and is not inferred from the request.

## Independent evidence recount

`reviewer/independent_counts.py` does not import the source engineer's
accounting program. From the permitted `CLOCK_EVIDENCE.csv` rows it recounts 32
rows, 32 unique old event IDs, zero scientifically frozen rows, and two
conditional technical anchors. The same local public source manifest contains
two QQQ Form N-PORT entries. The old 32 denominator is a retained inventory,
not a newly approved research population and not an effective sample size.

The clock inventory has 8 issuers with 4 events each and 25 distinct dates; 6
shared-date blocks contain 13 events, with at most 3 events on one date. These
are inventory-dependence diagnostics only. They do not validate an issuer/date
covariance estimator, determine cross-ETF event reuse, or certify any research
sample.

SPY 32/32 and QQQ 0/32 were independently re-read from the retained safe
aggregate overlap summary, but were **not** reconstructed from the unavailable
old manifest rows. They remain propagated request/name accounting, not valid
quote support. Availability-matched actual baskets, cross-ETF reuse, and valid
news--ETF--actual-basket joint quotes are `UNKNOWN`, including at every proposed
1/5/15/30/60-minute horizon and by session. Unknown is not zero.

## Source binding and restricted-view review

The initial adapter reproducibly accepted six rows containing one repeated fake
URL hash and `APPLE` for every event, accepted duplicate allowlisted headers and
ragged extra cells, allowed contradictory false-certification states, and did
not emit the two promised handoff hashes. These were S1--S4 in repair round 1.

The final adapter closes that finite list:

- the request now states the exact six `event_id -> SHA256(URL) -> issuer`
  bindings and a stable binding-list hash;
- the adapter cross-checks its reviewed binding against that request and rejects
  event/hash/issuer swaps;
- duplicate headers, prohibited headers, missing or ragged cells, duplicate or
  missing events, uncontrolled enum values, and contradictory certification are
  rejected before aggregation; and
- aggregate output includes the private input hash, source-list hash, adapter
  hash, and counts only. Rows remain custodian-private.

The reviewer independently hashed the six retained issuer-page URLs and matched
all six event/issuer bindings. Fifteen reviewer adversarial/algebra tests and
nine final source tests pass. This pass applies only to the whitelist and
aggregate-consumer logic. The adapter neither obtains the required historical
CMS/distribution view nor independently proves that a custodian's certified
status is true. Upstream provenance and authorized operation remain necessary.

## Method algebra and estimand review

The initial V2 weight builder normalized jointly across TOP and REST while the
fit required weights summing to one and had no group block. A group slice was
therefore rejected and the combined input pooled the two target groups. The
paired-response function also accepted ETF and basket evaluation windows that
were arbitrarily displaced. These were M1--M2 in the same repair round.

The final code requires exactly one selected group per fixed-support weight
construction and rejects a combined TOP/REST call. Within that group, reviewer
fixtures reproduce the intended order: ETF mass sums within event, event mass
sums within issuer, and issuer/cell targets are then applied. ETF and basket
must share the same anchor, h, and H evaluation-time uncertainty intervals.

Independent synthetic checks also establish the following for the implemented
scope:

- with varying issuer weight, using `x = w*z` recovers the specified slopes,
  while substituting `z` does not;
- cell-specific slopes are linearly standardized by fixed F* cell weights,
  rather than pooled with implicit within-cell `x^2` weights;
- an independent bread/cluster-score/meat reconstruction matches both the
  event-cluster joint cell covariance and its standardized covariance;
- randomized direct quadratic inversion matches all returned Fieller-set
  geometries tested, including weak-denominator unbounded cases; and
- randomized inputs satisfy the symmetric composition identity, while missing
  support and invalid weights are rejected.

The function accepts caller-supplied, prevalidated `x`; it does not establish
the provenance of empirical `w` or `z`. Event clustering is synthetic-only and
does not validate issuer-by-date, overlapping-window, cross-ETF/date, few-cluster,
or empirical critical-value behavior. The single-group Fieller implementation
does not solve the cross-group target: `D_TOP - D_REST` joint confidence-set
inversion remains explicitly `NOT_IMPLEMENTED`, with no marginal-interval
subtraction. Terminal equivalence, platform stability, quote/feed validity,
source validity, corporate actions, and parameter freezing also remain outside
the certified code. These limitations require `HOLD_METHOD`.

## Reproduction and repair closure

One named repair round was used; no second round was requested. Final commands
run independently from the stage root:

```text
python3 -m pytest -q sources                         -> 9 passed
python3 method/synthetic_tests.py                    -> 15 / 15 passed
python3 -m pytest -p no:cacheprovider -q reviewer    -> 15 passed
python3 reviewer/independent_counts.py               -> completed
python3 -m py_compile method/*.py sources/*.py reviewer/*.py -> completed
```

The final source count and method count differ from the original engineering
reports because repair-round tests were added. Passing synthetic and parser
tests does not create empirical support, power, identification, or novelty.

Final reviewed SHA-256 values are recorded in
[`reviewer/FINAL_HASHES.json`](reviewer/FINAL_HASHES.json). That manifest omits
its own hash and this report's hash to avoid a self-reference loop; the
coordinator may record the report hash after the review is frozen.

## Final decision and only next action

`HOLD_DATA` remains necessary because there is no certified first-public clock,
availability-matched pre-event actual basket, historical identifier join, or
valid bilateral quote common mask. `HOLD_METHOD` remains necessary because the
cross-group ratio contrast and actual dependence calibration are not
implemented. Parameters remain `PROPOSED_NOT_FROZEN`, and the overall research
status remains `HOLD_CONTRIBUTION_AND_EMPIRICAL_VALIDATION`.

The single prioritized next action is exactly the bounded custodian request
already prepared: obtain an authorized historical CMS/version or release-
distribution provenance view for the fixed six events and six URLs, then run
the aggregate adapter. Re-fetching current pages is not a substitute. This
action does not authorize response values, holdings/quote joins, purchases,
population expansion, or empirical analysis.
