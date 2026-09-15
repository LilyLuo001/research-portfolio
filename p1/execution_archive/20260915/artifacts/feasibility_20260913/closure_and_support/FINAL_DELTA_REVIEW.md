# Independent final-delta review

Review date: 2026-09-13. Scope: the finite final reconciliation delta and the outcome-blind closure/support bundle only. This is proposal verification, not a whole-P1 audit or approval. The reviewed source bytes are identified below; later changes require a bounded delta check.

## Item findings

| Item | Status | Independent finding |
|---|---|---|
| Scope lint cannot self-authorize | VERIFIED_PROPOSAL_DELTA | `contract_gate_status` has no authorizing return. Even a `PI_APPROVED` mapping with both exact boolean metadata approvals returns `AUTHORITY_VERIFICATION_REQUIRED`. Owner authority, the signed hash, and an authorized protected view remain external prerequisites. This is a scope lint, not an implemented access-control gate. |
| Actual YAML and adverse mappings | VERIFIED_PROPOSAL_DELTA | The actual hashed YAML returns `FAIL_DRAFT_CANNOT_SELF_APPROVE`. Independently evaluated 400 purpose/mapping combinations, varying status, absent/false/true/numeric/string approval values and outcome approval while setting SCC/purchase booleans true. Results: 300 draft failures, 48 missing-scope failures, 50 sealed-outcome failures, and 2 external-authority-required results. None authorizes access. |
| Explicit standardization and no extrapolation | VERIFIED_PROPOSAL_DELTA | The functional specifies frozen PRE stocks, equal stock weights, separate PRE/POST common-calendar sets, equal calendar weights, and the stock baseline, period/group, and industry-calendar SUE derivative terms. Every positive-weight stock-calendar cell requires observed eligible rows; missing support yields `NOT_ESTIMABLE`. Required rank failures cannot be repaired by dropping load-bearing controls. This verifies the stated functional, not realized support or an implemented estimator. |
| Direction and margins | VERIFIED_PROPOSAL_DELTA | Positive relative kappa alone cannot establish high-tier acceleration. The high-tier own causal shape condition requires all early components nonnegative and their equal-horizon mean above the proposed 0.05 threshold. Mixed, negative, and slower patterns remain reportable. The relative-kappa and own-high-tier five-point thresholds are explicitly distinct, PI-pending estimands. Pure timing still requires the stronger unverified counterfactual and terminal conditions. |
| Covariance wording and finite inputs | VERIFIED_PROPOSAL_DELTA | Both timing discussion passages now say covariance omission can misstate uncertainty in either direction. Independent ratio calculations with numerator 0.4, terminal 1, and marginal variances 0.04 give variances 0.0464, 0.0344, and 0.0584 for covariance 0, +0.015, and -0.015; treating the reference as fixed gives 0.04. Nonfinite reference/covariance inputs, nonpositive reference SE, asymmetric covariance, and indefinite covariance are rejected in the checked cases. These are finite fixtures, not confidence-set or production inference validation. |
| Estimated B* | VERIFIED_PROPOSAL_DELTA | The terminal margin explicitly treats B* as estimated and requires joint propagation of B* and coefficient covariance. No empirical B*, calibrated margin, or equivalence result is supplied. PI approval cannot be replaced by selecting a margin using treatment results or power. |
| Graph algebra and inference boundary | VERIFIED_PROPOSAL_DELTA | Independently formed the primitive-shock loading matrix for `U_A=a1+d1`, `U_B=a2+d1`, `U_C=a2+d2`. With independent unit-variance primitives, `L L'=[[2,1,0],[1,2,1],[0,1,2]]`; graph traversal reaches all three nodes, while `Cov(A,C)=0`. Eigenvalues are approximately 0.5858, 2, 3.4142. Connectedness does not imply transitive pairwise covariance. Neither this fixture nor component topology validates multipliers, a multiway alternative, or a sample-size claim. |
| Fail-closed census representation | VERIFIED_PROPOSAL_DELTA | Parsed both CSVs independently. All 11 support-template rows and all 8 dependence-template rows have blank `value` fields, nonempty reasons, and source locators. Support statuses are `NOT_AVAILABLE`; dependence has `NOT_AVAILABLE` plus one `NOT_IMPLEMENTED` interpretation row. Those numbers count template rows only, not economic observations. No actual support, component count, or effective sample size is fabricated. |
| Exact minimum metadata request | VERIFIED_PROPOSAL_DELTA | The final request distinguishes the two unavailable/not-implemented statuses; requires protected-view construction of new-clock exposure/tier metadata from as-of, publication, split, holdings, denominator and missingness inputs; specifies all response-leg dates including +1d; and requests observed positive-weight stock-calendar support with industry/quarter identifiers. It requires calendar/timestamp uncertainty, eligibility/mask reasons, overlap/reuse, signed sponsor provenance, and a filtered-view/hash/authorization receipt. It excludes response values and remains contingent on PI contract signature and protected-view authority. The source-provenance table is the metadata engineer's receipt; underlying source contents and their claimed provenance were not independently re-audited in this finite review. |
| PI next-decision framing | VERIFIED_PROPOSAL_DELTA | The note labels actual support unknown and proposes a conditional metadata-only census. It preserves unresolved timing, H3, rank, power, and inference validity. Its general reference to `NOT_AVAILABLE` blanks should be read with the precise CSV/request distinction: the interpretation row is `NOT_IMPLEMENTED`. No new authority is conveyed. |
| Actual support and statistical validity | CONCRETE_BLOCKER | No authorized new-clock event/session/coverage/control/dependence view or signed sponsor crosswalk is present in this bundle. Realized support, estimator rank, selection stability, reference precision, B* calibration, and a valid inference procedure therefore remain unverified. The required next input is the specified PI-signed, authorized, outcome-blind protected census view and receipt. This review does not fill those blanks. |

## Deterministic execution

Independently ran:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  p1/feasibility_adjudication/20260913/reconciliation/tests/test_contract_counterexamples.py \
  p1/feasibility_adjudication/20260913/closure_and_support/tests/test_closure_checks.py
7 passed in 0.28s
```

The additional adverse-mapping, analytical covariance, finite-input rejection, primitive-shock covariance, graph-traversal, and CSV blank/reason checks above were executed independently in memory. They wrote no additional review artifacts. The existing tests also verify the amplitude-only timing counterexample, pooled 0.9 versus equal-wave 0.5, and duplicated-event variance 1 versus the erroneous independent-row 0.5.

## Exact reviewed SHA-256 hashes

Paths below are relative to `p1/feasibility_adjudication/20260913/`. This review's own file is excluded to avoid a self-referential hash.

| File | SHA-256 |
|---|---|
| `reconciliation/estimation_contract.reconciled.PROPOSED.yaml` | `00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f` |
| `reconciliation/TIMING_COUNTEREXAMPLES.md` | `3c81b6df1b785871acae65ecedeb2693a3dbdba395f55852efc4812814d61c35` |
| `reconciliation/code/contract_counterexamples.py` | `e90d080293a12743430e9faaadd131368752b3509ad4ad2aa91c390d1661b85b` |
| `reconciliation/tests/test_contract_counterexamples.py` | `26b3b623e96109219841690f07699e8efa9e65b8c8e321d72fc441ff7388e5d6` |
| `closure_and_support/SUPPORT_CENSUS.csv` | `a8f7f14c2a82903f0a5a09866409105b1a9add110626d367ddaaaa99901866a4` |
| `closure_and_support/DEPENDENCE_CENSUS.csv` | `3656f22b90fba59baa5e0f222aa5a2af0c04fdef0da7d50aa749388e8ba1d1b1` |
| `closure_and_support/MINIMUM_METADATA_REQUEST.md` | `32741af09c8e2cccc427c1cc3b486965f270a99f82820a3fd30202323d641abd` |
| `closure_and_support/PI_NEXT_DECISION.md` | `e6fc7a693a376175f717f0eaa67429e414cce49b5d9d82f555f79b44d11b399a` |
| `closure_and_support/code/closure_checks.py` | `484ebcf5866e7276420b7200576cd6cf1238f1718f10df52ee267d3247aef96b` |
| `closure_and_support/tests/test_closure_checks.py` | `e27642a0493ae784aee9d9a76e48e118cc61a83c2c7867ea41602993319cdb70` |

## Constrained repairs and research boundary

The finite repairs identified during review—stock baseline slope in the functional, distinct directional/relative margins, two-sided covariance wording, exact census-status description, and the missing exposure/response-date/observed-support metadata requirements—are present in the hashes above. No further load-bearing proposal repair is identified within this narrow scope.

No sealed outcome, earnings-response, quote, forecast, actual-EPS or treatment-result files were opened. No remote/SCC operation, purchase, commit, or push was performed. Passing algebra and lint fixtures does not establish identification, pure timing, terminal equivalence, H3, causal effects, power, or inference validity. `HOLD_DESIGN + HOLD_DATA` and the separate protected-view/owner authority boundary remain intact.
