# Independent contract review — provisional

Date: 2026-09-21. Disposition: **`NUMERICAL_VALIDATION_PASS; CONTRACT_NOT_FROZEN; EMPIRICAL_RELEASE_BLOCKED`**.

This is a bounded review of `EXECUTION_SCOPE.md`, `ANALYSIS_CONTRACT.yaml`,
`method/VALIDATION_AMENDMENT.md`, and the new wrapper, informed by the prior
ratio-continuation review and its retained adversarial tests. It does not read
financial response values or audit old research results. Requested Sol/high
routing was accepted; actual backend model/effort telemetry is `NOT_OBSERVED`.

## Narrow repair finding

For a real symmetric matrix, nonnegativity of every principal minor is
necessary and sufficient for positive semidefiniteness. The wrapper converts
each represented binary float exactly to a rational number, checks exact
symmetry, and evaluates all 15 principal minors of the fixed 4x4 interface.
It returns a copy of the input and performs no clipping, averaging,
symmetrization, or nearest-PSD projection. This closes the prior accepted-
indefinite and accepted-asymmetric cases as specified.

The repair is deliberately strict. A floating-point Gram or intended singular
covariance can be rejected if its represented entries are not exactly PSD.
That is a caller-visible fail-closed policy, not evidence against the
scientific covariance model. It also does not make covariance construction or
critical-value calibration valid.

Independent execution under warnings-as-errors produced:

```text
new method/test_validation.py                         7 passed
prior reviewer/test_ratio_adversarial.py via wrapper 15 passed
new reviewer/test_exact_psd_wrapper.py                12 passed
```

The prior suite was loaded unchanged while the module name `estimator` was
bound to the new wrapper; no prior file or test was modified. The 15 passes
include the formerly decisive near-indefinite regression, randomized and
singular containment, unit-scaling, extreme finite arithmetic, malformed
covariance, weak-denominator, and score-helper cases. Final hashes are not yet
recorded because the contract and support artifacts are still changing.

## Contract release findings

The YAML accurately labels itself
`SPECIFIED_BUT_NOT_EMPIRICALLY_RELEASED`. It is a draft measurement framework,
not a frozen analysis contract. The following are release conditions, not
optional refinements:

1. Freeze the supported event population and grouping before response access.
   The six announcements are probes and the 32-group inventory is explicitly
   not an analysis sample. Any expansion needs a deterministic, outcome-blind
   rule; “scientific need” alone leaves discretion after support is known.
   Freeze issuer mapping, ETF-specific top-five membership date, duplicate or
   shared-message treatment, and event/date exclusions.
2. Freeze an operational release-anchor rule and the primary session from
   provenance metadata. “Earliest evidenced public release interval” must not
   be silently upgraded to proof of worldwide first publication. The rule must
   say how source postings, distributor notices, wire reposts, conflicting
   timestamps, and unresolved earlier plausible releases affect eligibility.
   Five-minute use requires an operationally justified interval and all
   predeclared plausible-anchor/endpoint sensitivities; failed cases must fall
   to a predeclared coarser/not-run path rather than be selected with prices.
3. Verify historically available consensus and actuals matched on period,
   currency, split basis, and units. Freeze the news-quality exclusions and
   transformation/standardization `F_star`; do not define either from price
   responses.
4. Verify pre-event basket holdings, cash, and corporate actions separately
   for SPY and QQQ. Freeze valuation conventions, missing-component behavior,
   issuer/security mapping, and whether a supported event enters one or both
   ETFs. A later public snapshot or a renormalized proxy is not the primary
   basket.
5. Freeze quote scope and endpoint semantics: actual venues/feed, bid/ask
   validity, crossed/locked quotes, halt/cancel/gap state, staleness, endpoint
   selection, multi-security synchronization, and missingness. A single venue
   must not be relabeled NBBO. Freeze how incomplete basket components make an
   event-horizon cell unavailable.
6. Specify the estimator from supported rows through the four coefficients.
   The current text names the contrast but not weighting, intercept/covariate
   handling, source-composition implementation, or the exact relationship
   between event observations and `N`, `k`, and `F_star`.
7. Specify and calibrate the one simultaneous joint region. This includes
   influence-score construction and bread, clustering/blocking for shared
   messages, cross-ETF reuse, repeated issuers, overlapping windows and dates,
   small-cluster handling, covariance rank policy, critical-value algorithm,
   resampling unit/count/seed, and outcome-blind null-size acceptance criteria.
   A nonempty `calibration_status` string is not calibration.
8. Freeze the weak-denominator and diagnostic decision rules. Unbounded or
   disconnected sets must be retained. Pre-news, pseudo-event, timing,
   staleness, reversal, and leave-block-out diagnostics need predeclared
   consequences; they cannot become post-response exclusion choices.
9. Do not make equivalence, exclusion, “no meaningful effect,” or MDE claims
   until an economically justified margin and valid variance/dependence model
   are frozen. Observed post-hoc power remains prohibited.
10. Implement an auditable response-read guard. It needs explicit required
    fields/states, a machine-checkable pass/fail receipt, hashes or immutable
    identifiers for frozen inputs/code, and a definition of response-bearing
    data. Known past access must be recorded; the inventory cannot be called an
    untouched confirmation sample.

## Public clock evidence

An independent recount of the two saved receipts confirms 18 HTTP attempts and
13 successful metadata projections. Every one of the six probes has at least
two successful source records. The generated support table's source-time split
of three premarket and three after-hours observations is reproducible; zero
events are certified first-public and zero primary responses are released.
The receipt hashes recorded in `clock/CLOCK_COUNTS.json` match the files.

The evidence is fit for source-specific operational candidate adjudication,
not historical proof of the first publication anywhere. All retrievals were in
2026, page bodies were not retained, and issuer pages can carry later
modifications. The source URLs, extracted metadata, retrieval facts and hashes
are preserved, but a body hash without the body does not permit later
independent re-extraction if a page changes.

The event-level adjudications are appropriately nonuniform:

- Exxon 2023-01-31 has an issuer/wire agreement at 06:30 ET and is a credible
  candidate minute, not a global-first certificate.
- Exxon 2023-07-28 has distinct issuer 06:00 and wire 06:30 anchors. Both must
  remain predeclared variants; returns cannot choose between them.
- UnitedHealth has a 05:55 wire observation followed by 05:57:23.332 issuer
  metadata. This is a plausible source sequence, not a contradiction that may
  be resolved with prices.
- The two Apple wire observations at 16:30 are candidate distribution minutes;
  issuer pages add only dates.
- Microsoft's 03:00 page metadata is not an actual-release clock. The 16:07
  notice says results were already available, so it is an upper observation
  and notice-session diagnostic, not an original-release anchor.

This review does not require logically proving the absence of every earlier
publication worldwide. It requires a defensible, source-labeled operational
interval, transparent residual uncertainty and precommitted timing sensitivity.

## Stage-A support projection

A separately frozen, diagnostic-only quote-support projection is consistent
with the approval and does not release a research outcome. It may output quote
timestamps, instrument identifiers, documented feed state and
present/positive/noncrossed support booleans and counts, but no bid/ask levels,
mids, returns, directions, magnitudes or response estimates. Its manifest must
name exact inputs, schema/publisher/feed/venue, symbols and mappings, all six
events and source-specific interval variants, and code hashes. Exxon July 28
must preserve both clock variants; Microsoft remains original-time unknown and
its 16:07 notice can support only a notice diagnostic.

The quote-state routine must be justified by actual source schema semantics,
including bid/ask meaning, locked/crossed policy, feed-status/halt/cancel/gap
interpretation, freshness/lookback, ordering/deduplication, session timezone,
and missingness. If those meanings are unavailable, the result is
`SUPPORT_UNAVAILABLE`, not inferred validity. Stage-A support may determine
whether a full contract can be frozen; it may not select clocks or rules from
responses or authorize primary estimation. This separates an outcome-blind
feasibility gate from the still-blocked empirical analysis and avoids a
circular requirement to freeze unsupported quote semantics.

## Scope of the pass

The numerical implementation now passes the narrow validation contract. That
does **not** pass empirical covariance, critical-value calibration, source or
clock provenance, signal/holdings/quote support, data completeness, estimand
identification, economic-margin justification, or novelty. Primary p-values,
effect intervals, power, equivalence, exclusion, and causal or information-
production claims remain blocked until the enumerated release conditions are
frozen, independently checked, and enforced by the read guard.

This disposition is provisional. Actual support counts and calibration/null-
size evidence will be independently reproduced after their artifacts are
available; a final `INDEPENDENT_REVIEW.md` will then replace this provisional
release assessment.
