# Manual-transfer review package for Opus 5 High

Prepared for independent review; execution date: 2026-09-08.

This document is a handoff package, not an independent referee report. No Opus or Claude review is represented as having occurred. The reviewer should treat every novelty claim, citation, interpretation, and design judgment as contestable. The package preserves the original scientific prompt and the narrower Gate 1 execution prompt verbatim, describes the full completed **Gate 1 execution plan** and its realized status, maps the evidence, and states the unresolved assumptions and gaps. It is not a completed full-paper research plan: the governing Gate 1 prompt deliberately narrowed the task to assignment observability and support and prohibited writing another broad research plan before that gate was resolved.

## 1. What the reviewer is being asked to decide

The upstream paper asks whether greater index-weight concentration changes how common public information is incorporated across constituent stocks and index instruments, beyond the arithmetic effect of weights, heterogeneous news exposures, signal precision, and temporary rebalancing pressure.

Gate 1 asks a narrower investment decision: whether the available archive plus public institutional records support a defensible sample of repeated rule-based index reweightings with observable assignments, credible comparisons, and sufficient intersection with common-news dates to justify a later measurement pilot.

The execution intentionally did **not** run headline return regressions, estimate intraday price-discovery outcomes, construct monetary-policy shocks, calculate an MDE, or claim causal identification. It therefore cannot establish the paper's final novelty, economic importance, measurement validity, or power. Those are explicit review questions, not presumed achievements.

## 2. Transfer and integrity notes

Repository: `https://github.com/LilyLuo001/research-portfolio`

Audit folder: `index-reweighting-gate1/`

The governing inputs can be integrity-checked as follows:

| Input | SHA-256 | Lines | Role |
|---|---|---:|---|
| `index_concentration_research_agent_prompt.md` | `cd0ff03e5a0d828c6e39a048762889fbfdd875dadb2dbe76026a4236938223e0` | 315 | Upstream scientific research-agent prompt |
| `index_reweighting_gate1_execution_prompt.txt` | `a2d81c35f614c21bf38ee8a41dd40c470755b90a0f96b7306679b3564b9f56e0` | 223 | Narrower executed Gate 1 prompt |
| `P1_Refraction_WRDS_Data_Usage_Manual_UPDATED_20260903.md` | `bc13934789517677f87371e3d8673e462a8d535cfae4913aa06ed7d7c1feb5d8` | 2,258 | Archive navigation guide; not itself evidence that a dataset exists |

The archive manual is not reproduced because it describes licensed internal holdings. The exact input version is identified by hash, and the public package reports only aggregate audit outputs. No credentials or proprietary row-level data belong in this package.

The key-results snapshot in Section 3A records the final same-commit machine summary, so this document can be transferred by itself. If the folder is also supplied, `logs/gate1_summary.json` is the machine-readable verification source rather than a competing set of counts. Its main paths are:

- `institutional.*` for rule, event, intervention-group, and binding-status counts;
- `assignment.*` for dose grades and complete grade-A events;
- `common_news.*` for calendar and overlap counts at distinct counting units;
- `design.*` for comparison and matrix-rank status;
- `local.*` for archive coverage summaries;
- `gaps.*` for current blockers; and
- `headline_outcome_regressions_run` for the scope guardrail.

## 3. Full completed execution plan

This is the complete operational Gate 1 plan actually followed, including its decision rules and the status of each step—not a summary of that plan. “Completed” means the specified audit action ran or the access state was explicitly recorded; it does not mean that the underlying scientific requirement passed. A full-paper plan remains conditional on the Gate 1 decision and the independent review requested here.

### Phase 0 — Governance, scope, and isolation

1. **Freeze the decision and prohibited actions.** Limit the work to assignment observability and support. Do not revive the historical-HHI design, run headline outcomes, infer results from daily proxies, purchase data, bypass access controls, or alter frozen P1/Refraction work.
   - Acceptance rule: the package must state that Gate 1 is a feasibility audit and that no headline outcome regression ran.
   - Evidence: `RUN_README.md`, `docs/EVIDENCE_CONTRACT.md`, and `logs/gate1_summary.json`.
   - Realized status: completed.

2. **Create a clean, isolated repository area.** Work only in a new `index-reweighting-gate1/` folder on a task branch; preserve every older folder and all raw archives.
   - Acceptance rule: all new project artifacts are below the new folder, and raw licensed files are absent from Git.
   - Evidence: repository history, `.gitignore`, and artifact tree.
   - Realized status: completed; final branch/main synchronization is a repository-delivery step, not scientific evidence.

3. **Hash and read the governing inputs completely.** Read both prompts and the data manual; record hashes, byte/line counts, and roles without treating the manual as proof of access.
   - Acceptance rule: hashes resolve the exact input versions and no credential is copied into artifacts.
   - Evidence: `docs/INPUT_LINEAGE.md` and this package.
   - Realized status: completed.

### Phase A — Narrow, read-only archive audit

4. **Verify physical SCC access before making data claims.** Test the archive root, project directory, baseline manifest, and post-snapshot directory; load the documented Python environment. Write only to a new SCC run directory outside the archive.
   - Acceptance rule: missing paths would be reported `BLOCKED_ACCESS`; no invented row count is permitted.
   - Evidence: `logs/stage_a_commands.log`.
   - Realized status: completed; the documented paths were readable.

5. **Resolve candidate logical datasets without stacking overlapping copies.** Inspect the baseline manifest and the post-snapshot tree, identify candidate holdings, fund metadata, daily security data, corporate actions, identifier links, index metadata/membership candidates, and daily MIDAS summaries; compare duplicate candidates by hashes/metadata.
   - Acceptance rule: distinguish current/overlapping copies, canonical monthly MIDAS files, and superseded quarterly files; retain file-level provenance.
   - Evidence: `src/audit_archive.py`, `local_data_catalog.csv`, and `logs/stage_a_evidence.json`.
   - Realized status: completed for the bounded search; absence means “not identified in this archive audit,” not nonexistence.

6. **Audit the candidate ETF/fund panel.** For the Select Sector SPDR candidates and QQQ, resolve identifiers and eligible periods, audit holdings-report dates and gaps, reconcile saved batch metadata to Parquet parts, check fallback-key duplicates, and measure mapped-constituent/price coverage.
   - Acceptance rule: preserve report/as-of timing separately from filing/publication/download timing; no interpolation across gaps; holdings remain screening evidence.
   - Evidence: `fund_identifier_and_coverage_audit.csv`, `remaining_input_gaps_stage_a.csv`, and Stage A logs.
   - Realized status: completed as an aggregate audit.

7. **Audit outcome-input availability without pretending daily data are intraday.** Check daily returns, open and bid/ask fields for candidate ETFs, candidate daily stock data, schema transitions, and daily MIDAS coverage. Do not extrapolate a legacy TAQ link or join long histories on ticker alone.
   - Acceptance rule: daily summaries must be labeled daily; no claim of modern event-time quotes/trades.
   - Evidence: `local_data_catalog.csv` and Stage A validation logs.
   - Realized status: completed; intraday measurement remains unresolved.

8. **Search specifically for exact target membership and assignment inputs.** Inspect index header, constituent-history, and generic membership candidates; verify whether target Select Sector/Nasdaq-100 series and constituent rows actually resolve.
   - Acceptance rule: index returns, industry membership, fund holdings, and provider constituent membership remain distinct.
   - Evidence: `local_data_catalog.csv` and `remaining_input_gaps.csv`.
   - Realized status: completed search; the required point-in-time target membership and exact provider assignment inputs were not established.

9. **Prove archive safety and public-output hygiene.** Confirm no archive files were newly written, no Parquet/raw row output entered the run directory, and the committed evidence log contains aggregate metadata only. Licensed identifier values, file locators, per-batch details, and schema/file fingerprints are withheld from the public export and retained in permission-restricted SCC lineage files.
   - Acceptance rule: no licensed raw row and no credential is committed.
   - Evidence: `logs/stage_a_commands.log`, `logs/stage_a_validation.log`, repository secret scan, and final Git diff.
   - Realized status: completed subject to final repository validation.

### Phase B — Historical rules and event universe

10. **Retrieve primary institutional records and record transport limitations.** Inspect the S&P Select Sector methodology/change notices and capping analysis, Nasdaq-100 methodology/change log and July 2023 notice, official Federal Reserve calendars, NYSE calendar materials, and SF Fed USMPD page/workbook metadata.
    - Acceptance rule: a browser-readable source with command-line HTTP 403 is a transport limitation, not an evidence failure; a public shell does not prove historical file contents are available.
    - Evidence: `source_and_rule_registry.csv`, `logs/stage_b_source_retrieval_20260908.tsv`, `logs/root_transport_probe_20260908.tsv`, and Stage E source logs.
    - Realized status: completed for the registered sources.

11. **Build a regime-specific rule registry.** Record the document date, effective interval, rule level (company/issuer/security line), thresholds versus targets, input weighting, exact order of operations, reference-date rule, implementation/effective timing, secondary checks, precision, limitations, and evidence grade.
    - Acceptance rule: do not backcast current rules; `rule_source_grade=A` means exact rule/source evidence, not exact event assignment.
    - Evidence: `source_and_rule_registry.csv` and `src/build_rule_registry.py`.
    - Realized status: completed for the bounded regimes, with unresolved historical-source rows retained as `U`.

12. **Generate a complete potential-event ledger for the screening window.** Enumerate regular Select Sector rebalances, secondary checks, relevant sector-reorganization boundaries, the September 2024 common rule transition, Nasdaq-100 routine/special events, the separately announced July 17, 2023 constituent replacement as interference context, and separately labeled 2026 partial rows.
    - Acceptance rule: one common date or policy transition is not multiplied into independent shocks; scheduled checks are not automatically binding.
    - Evidence: `rebalance_event_ledger.csv`.
    - Realized status: completed for the encoded calendar.

13. **Classify binding status conservatively.** Assign each occurrence `confirmed_binding`, `confirmed_nonbinding`, `uncertain`, or `outside_applicable_regime` using registered source evidence. Preserve a separately documented non-capping index replacement as `confirmed_other_intervention` interference context. Retain near-boundary and unresolved rows.
    - Acceptance rule: unknown evidence remains `U`, never silently becomes nonbinding.
    - Evidence: `rebalance_event_ledger.csv` and rule-builder tests.
    - Realized status: completed; most unresolved events remain explicit rather than imputed.

### Phase C — Assignment observability and pilot reconstruction

14. **Keep four portfolio objects separate.** Define the uncapped reference portfolio, provider rule-assigned index portfolio, observed ETF holdings, and creation/redemption basket as different objects in every dose row.
    - Acceptance rule: blank unavailable fields are not filled from another object.
    - Evidence: `assignment_doses_and_evidence.csv`, `docs/EVIDENCE_CONTRACT.md`, and tests.
    - Realized status: completed.

15. **Apply the A/B/C/U evidence hierarchy.** Grade A requires an exact official vector or complete contemporaneous inputs with reconciliation; B establishes a documented event with incomplete dose; C is screening only; U is unknown/inaccessible.
    - Acceptance rule: only complete grade A can support exact-dose calculations and design-information statistics.
    - Evidence: `assignment_doses_and_evidence.csv` and `logs/gate1_summary.json`.
    - Realized status: completed; consult the summary for the authoritative grade distribution.

16. **Run bounded pilots.** Examine Technology Select Sector March and June 2024, the September 2024 rule transition, and July 2023 Nasdaq special rebalance. Transcribe only same-table, selected, rounded official values where available; preserve their precision and incompleteness. Keep cap distortion separate from rebalance change.
    - Acceptance rule: do not renormalize a top-15 subset, infer old/new portfolios from differently dated snapshots, or describe a retrospective table as trader-time public information.
    - Evidence: `assignment_doses_and_evidence.csv` and source registry.
    - Realized status: completed as a source-availability test; exact vectors remain an input gap.

17. **Withhold rule replay when inputs are insufficient.** Require contemporaneous membership, provider-consistent company/share-class mapping, float/IWF inputs, corporate actions, prices, and full rule order before replay and reconciliation.
    - Acceptance rule: report the missing package rather than fabricate a vector or narrow uncertainty bound.
    - Evidence: `remaining_input_gaps.csv`.
    - Realized status: completed as a defensible stop condition; replay was not falsely executed.

### Phase D — Comparison, interference, and statistical-support audit

18. **Write the prospective design objects before outcomes.** For every ledger row, state the candidate treatment, counterfactual status, assignment and inference units, event grouping, shared dates/issuers, and the mechanical/exposure/precision/liquidity/interference threats.
    - Acceptance rule: event existence and same-stock overlap do not establish an exclusion restriction or clean comparison.
    - Evidence: `comparison_and_interference_audit.csv` and `src/build_design_audit.py`.
    - Realized status: completed as a row-level design audit. Event status can be grouped from the ledger, but a separate signed-dose distribution by index family, regime, quarter, and issuer was not reported because no event has a complete exact vector and most selected numerical rows cover only one Technology pilot; that requested distribution remains unexecuted rather than being inferred from incomplete subsets.

19. **Gate matrix diagnostics on exact assignments.** Compute rank, collinearity, dose range, residualized information concentration, and leave-one-event/issuer/sector/transition support only after a complete signed vector and frozen design matrix exist.
    - Acceptance rule: a zero/unknown denominator yields `NOT_COMPUTED`, not an arbitrary support statistic.
    - Evidence: matrix-status fields in `comparison_and_interference_audit.csv`.
    - Realized status: completed as a blocked diagnostic; no unsupported information-effective sample size was reported.

20. **Define the first adversary as mechanical weight and demand effects.** Require future replay of actual and alternative weights on identical price paths, with common support and corporate-action-consistent units; distinguish accounting effects from equilibrium responses.
    - Acceptance rule: any non-accounting remainder is not automatically causal behavior.
    - Evidence: comparison audit and the unresolved causal-comparison gap.
    - Realized status: specified but not empirically executed because exact vectors/outcomes are absent.

### Phase E — Common-news calendar and overlap support

21. **Build an official FOMC meeting/statement calendar.** Use Federal Reserve annual/current calendar pages, retain scheduled meetings plus separately labeled unscheduled, notation-vote, cancelled, boundary-year, and realized partial-extension entries; identify statement/package differences without treating phases as independent shocks.
    - Acceptance rule: eligibility is rule-based; omitted or ineligible records must still be explicit where relevant.
    - Evidence: `fomc_calendar.csv`, `src/build_fomc_calendar.py`, and Stage E tests/logs.
    - Realized status: completed and correction-tested; use the summary JSON for current counts.

22. **Construct the NYSE trading-session calendar.** Encode regular holidays plus documented special closures, with Juneteenth only from the applicable year.
    - Acceptance rule: calendar source IDs must resolve to registered source URLs and signed distances must pass tests.
    - Evidence: Stage E source registry, code, and tests.
    - Realized status: completed for the bounded period.

23. **Screen USMPD availability without importing factors.** Download the public workbook temporarily, inspect workbook metadata/sheets and coverage, register its version/hash, and discard the file; do not use surprises, factors, or returns in Gate 1.
    - Acceptance rule: schema/coverage screening is not factor construction or event classification.
    - Evidence: `logs/stage_e_usmpd_registry.csv` and `logs/stage_e_retrieval.log`.
    - Realized status: completed.

24. **Intersect every ledger event with eligible FOMC meetings.** Preserve reference date, earliest documented announcement, pro forma date, implementation close, effective open, secondary adjustment, and next intervention as distinct anchors. Compute signed trading-session distances, nearest pre/post meetings, and 20/40/60-session support bands.
    - Acceptance rule: unknown dates remain unknown; a band-overlap flag means interval intersection with anticipation/subsequent interventions; source IDs/URLs must resolve.
    - Evidence: `assignment_and_fomc_support.csv` and FOMC tests.
    - Realized status: completed for encoded event anchors.

25. **Report dependence-aware counting units.** Keep FOMC meetings, intervention groups, ledger event rows, and resolved anchor joins separate; identify reused meetings and shared rebalance dates.
    - Acceptance rule: none of these counts is called an independent-observation count or a power calculation.
    - Evidence: support table and `logs/gate1_summary.json`.
    - Realized status: completed. The final support build contains 69 eligible all-scope FOMC meetings (63 in the 2018–2025 primary scope), 49 resolved unique intervention dates, 785 distinct ledger `basket_assignment_id` values (one per event row, not 785 exact vectors), and zero reusable comparison IDs. Exact shared-stock overlap remains unresolved because authoritative point-in-time constituent inputs were not recovered.

### Phase F — Close Questions 2 and 3 at the feasible level

26. **Do not validate intraday statistics with daily pseudo-data.** Record that daily returns/MIDAS can help later with covariances or exposures but cannot calibrate latency, quote noise, clocks, or event-time transmission.
    - Acceptance rule: no pseudo-ticks, intraday MDE, or speed claim from daily data.
    - Evidence: `remaining_input_gaps.csv` and `headline_outcome_regressions_run` in the summary.
    - Realized status: completed as a scope conclusion.

27. **Classify future measurement inputs claim by claim.** Separate stock/ETF quotes and trades, futures data if retained, exact assignments, point-in-time membership, corporate actions, timestamps/conditions, and event metadata.
    - Acceptance rule: a stock–ETF-only pilot may narrow the claim but cannot answer a futures-inclusive question.
    - Evidence: `remaining_input_gaps.csv`.
    - Realized status: completed as a feasibility map; the data have not been acquired.

### Phase G — Decision, reproducibility, and handoff

28. **Integrate a single evidence-based Gate 1 recommendation.** Separate conclusions for treatment observability, comparison credibility, independent support, and outcome measurability; identify the minimum resolving input and avoid implying that novelty, power, or publication potential passed.
    - Acceptance rule: exactly one allowed recommendation appears in `FINAL_DECISION.md`.
    - Evidence: `FINAL_DECISION.md` and validator.
    - Realized status: completed. The final recommendation is **REVISE / RESOLVE A SPECIFIC INPUT GAP**; the rationale and pass/fail next gate are restated below.

29. **Run deterministic validation.** Execute all unit tests, regenerate derived tables, verify required schemas and typed keys, check line endings/diff hygiene, scan for secrets, and ensure sources resolve internally.
    - Acceptance rule: the final test and validation logs in the reviewed commit must pass; stale intermediate logs are not controlling evidence.
    - Evidence: `tests/`, `src/validate_gate1.py`, final validation log, and Git diff.
    - Realized status: completed; 64 tests passed and the package-contract validator passed after the final deterministic rebuild. The reviewer should reproduce both from the reviewed commit.

30. **Prepare manual independent-review materials.** Include both prompts, the full plan, evidence and literature matrices, open assumptions/gaps, artifact map, and a read-only referee instruction. Do not simulate a review.
    - Acceptance rule: the reviewer is explicitly told to verify literature and contribution claims rather than accept them.
    - Evidence: this document and `docs/CLAUDE_READ_ONLY_REVIEW_PROMPT.md`.
    - Realized status: completed by this package.

## 3A. Same-commit result and decision snapshot

**Formal Gate 1 recommendation: REVISE / RESOLVE A SPECIFIC INPUT GAP.** The institutional variation warrants one more bounded assignment-retrieval and design-adjudication exercise, but the current evidence does not justify an outcome-measurement pilot, intraday-data purchase, headline regression, causal claim, power claim, novelty claim, or publication claim.

| Dimension | Final executed result | Interpretation |
|---|---:|---|
| Local catalog | 19 logical audit rows | Physical availability is table-specific, not proof of target coverage |
| Candidate fund-years | 96: 12 funds × 2018–2025 | 94 have at least one recorded screening gap; all 96 are unfit as exact assignment substitutes |
| Candidate holdings screen | 59,605 rows; 1,133 fund-report dates; 41 parts in 24 reconciled batches | Aggregate screening only; licensed IDs/file lineage are suppressed from the public export and retained in permission-restricted SCC lineage files |
| Rule/source registry | 21 rows: 10 source-grade A, 7 B, 4 U | Source grade is not assignment grade |
| Event ledger | 785 rows in 104 event groups | Rows are not independent shocks |
| Event classification | 30 confirmed binding in 17 groups; 175 confirmed nonbinding; 575 uncertain; 4 outside regime; 1 other confirmed intervention | Unknown is not nonbinding; the other intervention is interference context, not a capping treatment |
| Assignment evidence | 34 grade-B dose rows; zero complete grade-A event vectors | Exact signed doses, full rule replay, design rank, leverage, and information-effective support remain unavailable |
| FOMC calendar | 78 records; 63 eligible scheduled primary-scope meetings | Exceptions and partial 2026 records remain explicit |
| Event/FOMC support | 11,745 rows, of which 8,646 have resolved anchors and 3,099 are unresolved anchors | Join rows are not sample size or power |
| Confirmed-binding primary overlap | 37/70/86 event-group–meeting pairs within 20/40/60 trading days, spanning 24/36/39 distinct meetings | Temporal support is nonempty but dependent and not yet causal support |
| Comparison audit | 785 rows; 0 reusable `comparison_id` values | No estimable preferred causal contrast is established |
| Headline outcomes | none run | This is an assignment/support audit only |

The smallest decision-changing next step is an authorized, source-vintaged, full-precision Select Sector assignment package for the March, June, and September 2024 pilots: every constituent, point-in-time membership, security/share-class/company lineage, provider shares and IWF/float factors, prices and valuation timestamps, corporate actions, unrounded old/new index shares or weights, complete rule order, and trader-time pro-forma publication metadata. Reconcile at least one complete vector under the contemporaneous rule and repeat the pathway on a second routine episode. Before looking at outcomes, freeze one treatment/counterfactual design, replay the mechanical identical-price-path benchmark, and require a full-rank matrix with support surviving event-group, issuer, Technology-sector, and September-transition exclusions. Failure to recover data remains an access gap; negligible/nonrepeatable doses, sign/rank instability under defensible precision, or absorption of treatment by event/issuer structure would be evidence against the current design.

The public Stage A tables are deliberately redacted. Detailed licensed identifiers, file locators, batch metadata, and integrity hashes live only in a permission-restricted SCC lineage directory. Whether the remaining aggregate fund-year statistics meet the institution's redistribution policy is a maintained compliance assumption requiring the researcher's institutional/license confirmation before any broader public release.

## 4. Executed-evidence matrix

| Evidence object | Primary source link | What the execution can support | What it cannot support | Main artifact |
|---|---|---|---|---|
| Historical/current Select Sector weighting regimes | [S&P U.S. Indices Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf) | Rule text, thresholds/targets, rule level, timing, and retrospective change history for bounded regimes | A complete historical event assignment vector or provider inputs | `source_and_rule_registry.csv` |
| September 2024 Select Sector rule transition | [S&P consultation results, 2024-09-03](https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20240903-1474128/1474128_sp-select-sector-indices-results-20240903.pdf) | Contemporaneous rule change, pro-forma start, implementation close, effective open; one common policy transition | Eleven independent experiments or the complete September assignment vector | `source_and_rule_registry.csv`; `rebalance_event_ledger.csv` |
| Historical cap screens and selected 2024 Technology weights | [S&P capping analysis, 2024-08](https://www.spglobal.com/spdji/en/documents/additional-material/select-sector-capping-impact-analysis-20240808.pdf) | Selected, rounded, same-table cap-distortion evidence and conservative event screening | Exact signed rebalance changes, full vectors, precise boundary classification from rounded displays, or trader-time publication | `assignment_doses_and_evidence.csv` |
| December 2024 reference-date change | [S&P reference-date update, 2024-12-02](https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20241202-1475776/1475776_constituent-weighting-reference-date-update-20241202.pdf) | Timing change and first implementation/pro-forma dates | Complete December event assignment | `source_and_rule_registry.csv` |
| Portfolio-object and capping definitions | [S&P Index Mathematics Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-index-math.pdf) | Current definitions separating uncapped/capped objects and adjustment factors | Historical event inputs or equilibrium counterfactuals | `source_and_rule_registry.csv` |
| Historical-pro-forma access context | [S&P Equity Indices Policies & Practices](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-equity-indices-policies-practices.pdf?force_download=true) | That provider data-delivery mechanisms exist and have timing conventions | Public availability of historical file contents | `source_and_rule_registry.csv`; `remaining_input_gaps.csv` |
| Nasdaq-100 historical rule changes | [Nasdaq-100 Methodology Change Log](https://indexes.nasdaqomx.com/docs/Methodology_Change_Log_NDX.pdf) | Bounded historical rule regimes and issuer/company-level transitions | July 2023 full assignment vector | `source_and_rule_registry.csv` |
| Nasdaq-100 security-level rule evidence in 2019 and 2020 Q1 | [SEC filing, 2019-11-22](https://www.sec.gov/Archives/edgar/data/886982/000156459019044233/gs-424b2.htm); [SEC filing, 2020-03-24](https://www.sec.gov/Archives/edgar/data/886982/000156459020012750/gs-424b2.htm) | Contemporaneous descriptions support security/stock-level mechanics through 2020 Q1 and prevent an issuer-level backcast | A Nasdaq adoption notice, exact 2020 Q2 transition date, or any event assignment vector | `source_and_rule_registry.csv`; `rebalance_event_ledger.csv` |
| Nasdaq-100 issuer-level rule evidence by 2020 Q3 | [SEC filing, 2020-07-01](https://www.sec.gov/Archives/edgar/data/886982/000156459020031554/gs-424b2.htm) | Bounds issuer-level mechanics as present by July 2020 when combined with the provider change log | The exact day within the unresolved 2020 Q2 transition or exact event inputs | `source_and_rule_registry.csv`; `rebalance_event_ledger.csv` |
| July 2023 Nasdaq-100 special rebalance | [Official schedule notice](https://indexes.nasdaqomx.com/docs/NDX_SpecialRebalance_2023.pdf); [official press release](https://www.nasdaq.com/press-release/the-nasdaq-100-index-special-rebalance-to-be-effective-july-24-2023-2023-07-07) | Reference, announcement/pro-forma, and effective dates; a single confirmed intervention without additions/deletions | Several independent shocks or precise security-level doses | `rebalance_event_ledger.csv`; `assignment_doses_and_evidence.csv` |
| July 17, 2023 TTD-for-ATVI replacement | [Official Nasdaq announcement, 2023-07-12](https://www.nasdaq.com/press-release/the-trade-desk-inc.-to-join-the-nasdaq-100-index-beginning-july-17th-2023-2023-07-12) | Establishes a separate constituent replacement inside the special-rebalance anticipation window | A capping treatment, exact weights, or an intervention caused by the July 24 special rebalance | `source_and_rule_registry.csv`; `rebalance_event_ledger.csv` |
| July 2023 direction/turnover context | [Nasdaq, “All About Index Concentration”](https://www.nasdaq.com/articles/all-about-index-concentration) | Provider's approximate aggregate turnover and qualitative redistribution | Exact machine-readable old/new vector | `assignment_doses_and_evidence.csv` |
| Nasdaq historical weighting-file access state | [Nasdaq Global Index Watch — NDX Weighting](https://indexes.nasdaqomx.com/Index/Weighting/NDX) | The public/entitlement interface that was inspected | Historical July 2023 file contents from the public page state | `source_and_rule_registry.csv`; `remaining_input_gaps.csv` |
| FOMC dates and communication packages | [Federal Reserve calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm); [historical materials](https://www.federalreserve.gov/monetarypolicy/fomc_historical.htm) | Scheduled-meeting calendar, separately retained exceptions, and meeting-level package metadata | Independent shocks for each phase or a structural monetary-policy shock measure | `fomc_calendar.csv`; `assignment_and_fomc_support.csv` |
| Monetary-policy event-study data availability | [SF Fed USMPD](https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/) | Workbook version/schema/coverage availability screening | Constructed factors, surprise values, returns, real-time information, or power | `logs/stage_e_usmpd_registry.csv` |
| Local WRDS/SCC archive | Authorized read-only archive; no public link | Aggregate availability, snapshot coverage, price/link coverage, and target-table search results; public artifacts suppress licensed identifier values and file lineage | Exact index assignments, verified target membership, intraday paths merely from file presence, or an independent legal conclusion on redistribution | `local_data_catalog.csv`; `fund_identifier_and_coverage_audit.csv`; Stage A logs |

## 5. Literature and provisional contribution matrix

This is a **review map, not a completed novelty finding**. The academic papers below came from the upstream prompt or were added as obvious mechanical-demand comparators. Gate 1 did not conduct the prompt's required exhaustive journal/working-paper/citation search, and it did not independently adjudicate every paper's latest version, empirical design, or result. DOI/publisher links make the references verifiable; Opus must inspect the papers and search forward/backward citations before accepting any “remaining increment.” “Not found in this package” never means “never studied.” In the table, **U** means that the full-paper identification, sample, or result was not independently adjudicated in Gate 1; it is an evidence-status label, not a negative finding.

| Candidate closest literature | Question to verify | Mechanism to verify | Identification status | Relevant-result status | How this project could collapse into the existing contribution | Exact remaining increment, conditional on passing the missing gates | Package verification status |
|---|---|---|---|---|---|---|---|
| Hasbrouck (2003), [“Intraday Price Formation in U.S. Equity Index Markets”](https://doi.org/10.1046/j.1540-6261.2003.00609.x), *Journal of Finance* | How price discovery is distributed among index-related instruments and component portfolios | Trading and common-payoff links among cash, ETF, and futures markets | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | A new ranking of stock, ETF, and futures leadership would be an update/extension | Rule-assigned weight changes that alter common-news incorporation in a fixed residual basket, with non-arithmetic quality consequences | DOI/citation resolved; scientific overlap unresolved |
| Fang and Sanger, [“Index Price Discovery in the Cash Market”](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1926287), [DOI](https://doi.org/10.2139/ssrn.1926287), SSRN working/conference paper | Whether component stocks and the ETF contribute to index price discovery | Stock-by-stock cash aggregation versus ETF trading, with informed ETF trading as a proposed modifier | Abstract only: TAQ second-by-second reconstructed S&P 500 component index and Hasbrouck information shares; full specification not checked | SSRN abstract reports that the ETF supplies nearly half of price discovery and more when ETF trading is informed; full-paper evidence not checked | A constituent-cash versus ETF information-share result could be directly pre-existing | Exogenous weight assignments changing transmission to a pre-fixed residual basket and market-quality outcomes, after mechanical replay | SSRN landing page/abstract and DOI resolved; publication history, current version, full paper, and citations unresolved |
| Tse (2006), [“Intraday Price Discovery in the DJIA Index Markets”](https://doi.org/10.1111/j.1468-5957.2006.00639.x), *Journal of Business Finance & Accounting* | How the cash index, ETF, and floor/electronic futures contribute to DJIA price discovery | Electronic trading advantages across linked index markets | U—publisher abstract inspected; full-paper design/sample not adjudicated | Publisher abstract reports E-mini leadership and an important electronically traded ETF role; full-paper evidence not checked | A multi-market leadership and electronic-venue result could make a similar ranking non-novel | Assigned-weight effects on constituent-to-residual common-news incorporation, not another linked-instrument ranking | DOI/publisher abstract resolved; full scientific overlap unresolved |
| Buckle, Chen, Guo, and Tong (2018), [“Do ETFs Lead the Price Moves? Evidence from the Major US Markets”](https://doi.org/10.1016/j.irfa.2017.12.005), *International Review of Financial Analysis* | How cash, ETF, and futures price discovery evolved across major U.S. indices | Instrument substitution and estimator-dependent leadership over 2003–2013 | U—publisher abstract inspected; full-paper design/sample not adjudicated | Abstract reports conclusions that differ by information-share, permanent/transitory, and weighted-price-contribution measures; full-paper evidence not checked | A long-sample ETF/cash/futures leadership update or estimator comparison could already be covered | Exogenous assigned weights tied to common-news transmission and fixed residual-stock quality outcomes | DOI/publisher abstract resolved; full scientific overlap unresolved |
| Wallace, Kalev, and Lian (2019), [“The Evolution of Price Discovery in US Equity and Derivatives Markets”](https://doi.org/10.1002/fut.22019), *Journal of Futures Markets* | How ETF–futures price discovery changes over time | Secular market-structure and trading-activity changes | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | A newer period or concentration interaction alone would be insufficient | An assignment design that separates rule-driven weights from secular market-structure change | DOI/citation resolved; scientific overlap unresolved |
| Chordia, Green, and Kottimukkalur (2018), [“Rent Seeking by Low-Latency Traders”](https://doi.org/10.1093/rfs/hhy025), *Review of Financial Studies* | How markets respond at high frequency to macro announcements | Latency advantages around public-news releases | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | A coarser FOMC response-path exercise could add little | Rule-assigned constituent weights changing cross-security dependence at data-supported temporal resolution | DOI/citation resolved; scientific overlap unresolved |
| Dimpfl and Schweikert (2023), [“Information Shares for Markets with Partially Overlapping Trading Hours”](https://doi.org/10.1016/j.jbankfin.2023.106970), *Journal of Banking & Finance* | How information shares should be interpreted with different trading support | Non-overlapping hours and estimator structure | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | Applying another information-share estimator to a same-payoff system would be methodological replication | A correctly specified heterogeneous-payoff constituent design with explicit clocks/support, if information shares remain suitable | DOI/citation resolved; scientific overlap unresolved |
| Ernst, [“Stock-Specific Price Discovery From ETFs”](https://www.terpconnect.umd.edu/~ternst/docs/Ernst_ETF.pdf), working-paper starting reference | Whether ETFs participate in stock-specific price discovery and how constituent weight matters | Tandem stock–ETF trading and cross-instrument information incorporation | U—latest paper, sample, and design not adjudicated; Opus must locate and verify | U—no empirical result accepted here without the latest full paper | A result that high-weight stocks and ETFs interact more may already be the paper's mechanism | Common-public-information transmission to a pre-fixed residual basket after rule-driven weight changes, plus system-level quality consequences | Author-hosted PDF link resolved; version/publication status and citations unresolved |
| Glosten, Nallareddy, and Zou (2021), [“ETF Activity and Informational Efficiency of Underlying Securities”](https://doi.org/10.1287/mnsc.2019.3427), *Management Science* | Whether ETF activity affects information incorporation in underlying stocks | ETF trading/arbitrage and systematic-information processing | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | A finding only that ETFs improve common-information incorporation may be existing | Differential incorporation caused by assigned index weights rather than ETF activity/ownership, with mechanical replay | DOI/publisher record resolved; precise boundary unresolved |
| Ben-David, Franzoni, and Moussawi (2018), [“Do ETFs Increase Volatility?”](https://doi.org/10.1111/jofi.12727), *Journal of Finance* | Whether ETF activity propagates volatility to constituents | Arbitrage transmission of nonfundamental liquidity shocks | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | Rebalancing-flow or volatility effects could mimic information transmission | An effect surviving demand-pressure, reversal, liquidity, and nonfundamental-propagation tests, with information-quality meaning | DOI/publisher record resolved; used as a competing-mechanism comparator |
| Khomyn, Putniņš, and Zoican (2024), [“The Value of ETF Liquidity”](https://doi.org/10.1093/rfs/hhae041), *Review of Financial Studies* | How ETF liquidity creates value and affects participation | Liquidity, clientele, fees, and investor horizons | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | A pure ETF-liquidity story would be adjacent rather than new | Weight-driven common-information incorporation after separating liquidity and horizon mechanisms | DOI/publisher record resolved; precise relevance unresolved |
| Jiang, Vayanos, and Zheng (2025), [“Passive Investing and the Rise of Mega-Firms”](https://academic.oup.com/rfs/article/38/12/3461/8280528), *Review of Financial Studies*; [NBER version](https://doi.org/10.3386/w28253) | How passive investing affects the relative scale/value of large firms | Passive flows and disproportionate demand effects | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | Passive demand or endogenous firm growth could explain the proposed pattern | Within-event assigned-weight evidence about information processing, not price levels, with demand separated as mediator/confound | Publisher and NBER records resolved; precise overlap unresolved |
| Haddad, Huebner, and Loualiche (2025), [“How Competitive Is the Stock Market?”](https://doi.org/10.1257/aer.20230505), *American Economic Review* | How portfolio demand determines stock-market competition | Investor substitution/demand elasticity and passive investing | U—full-paper theory/design not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | A demand-elasticity or portfolio-substitution result would belong to this literature | A distinct causal common-news information-architecture effect with explicit quality, and only defensible welfare, implications | DOI/citation resolved; scientific overlap unresolved |
| Shleifer (1986), [“Do Demand Curves for Stocks Slope Down?”](https://doi.org/10.1111/j.1540-6261.1986.tb04518.x), *Journal of Finance* | Whether index inclusion reveals downward-sloping stock demand | Index-fund demand and price pressure | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | Event returns caused by mechanical index demand are classic price pressure | Transmission/quality changes after weight replay and reversal/flow tests, using outcomes outside the focal stock's arithmetic contribution | DOI/publisher record resolved; essential confound comparator |
| Kaul, Mehrotra, and Morck (2000), [“Demand Curves for Stocks Do Slope Down”](https://doi.org/10.1111/0022-1082.00230), *Journal of Finance* | Whether announced index-weight changes move prices without membership changes | Mechanical demand induced by weight revisions | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | A weight-change price response alone is already squarely covered | A change in public-information incorporation after assignment, distinct from contemporaneous demand pressure | DOI/publisher record resolved; especially close institutional comparator |
| Greenwood (2005), [“Short- and Long-Term Demand Curves for Stocks”](https://doi.org/10.1016/j.jfineco.2004.03.007), *Journal of Financial Economics* | How multi-security index redefinitions shift demand across stocks and horizons | Demand shocks, hedging spillovers, and reversal | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | Cross-stock effects from simultaneous reweighting may already be demand/hedging spillovers | Fixed-residual information incorporation that rejects measured-demand and reversal benchmarks | DOI/publisher record resolved; essential mechanical/interference comparator |
| Chang, Hong, and Liskovich (2015), [“Regression Discontinuity and the Price Effects of Stock Market Indexing”](https://doi.org/10.1093/rfs/hhu041), *Review of Financial Studies* | Whether rank-based index assignment causes price effects | Local assignment around index cutoffs | U—full-paper design/sample not adjudicated; Opus must verify | U—no empirical result accepted here without full-paper verification | Calling capping thresholds an RD without one-dimensional local assignment would be invalid imitation | A demonstrated boundary or exact-dose design respecting multidimensional/rank mechanics and manipulation/precision | DOI/publisher record resolved; current Gate 1 package establishes no RD support |

Missing literature work that the independent referee should treat as substantive rather than clerical:

1. Refresh Fang and Sanger's publication/current-version and forward-citation status, and verify the full paper beyond the SSRN abstract.
2. Refresh Thomas Ernst's latest version/publication status and forward citations.
3. Search the priority journals specified in the upstream prompt through the review date, plus specialist market-microstructure, ETF, indexing, rebalancing, passive-investing, common-information, and lead–lag work.
4. Trace backward and forward citations from Hasbrouck, Fang–Sanger, Tse, Buckle–Chen–Guo–Tong, Ernst, Glosten–Nallareddy–Zou, Greenwood, Kaul–Mehrotra–Morck, and Chang–Hong–Liskovich.
5. Search for papers using sector-index capping, issuer caps, quarterly reweighting, special rebalances, and FOMC news—not just titles containing “concentration” or “mega-cap.”
6. Determine whether any paper already combines exogenous index weights with stock-to-residual/ETF information transmission or market-wide information quality. The package makes no “first paper” claim.

## 6. Unresolved assumptions and evidence gaps

### 6.1 Assignment and institutional measurement

| Gap/assumption | Current evidence | Why it matters | Evidence or change needed |
|---|---|---|---|
| Exact Select Sector assignments | Rules, selected rounded values, and some binding-event evidence exist, but no complete reconciled pilot vector is established | No exact signed dose, common-state cap distortion, HHI/turnover, or design matrix | Authorized historical March/June/September 2024 pro-forma/assignment files, or complete contemporaneous membership, prices, shares, IWF/float factors, issuer mapping, corporate actions, and rule replay with reconciliation; then prove a repeatable earlier-event path |
| Exact July 2023 Nasdaq-100 assignment | Schedule and qualitative/aggregate effects are documented; historical pro forma is not recovered | It is only one institutional cross-check and has no precise security-level dose | Official 2023-07-14 pro-forma/index-share file or complete contemporaneous inputs and reconciliation |
| Point-in-time target constituent history | Archive search did not resolve exact target rows for the needed families | Holdings and generic membership cannot define the provider universe | Authoritative constituent intervals with effective dates, issuer/share-class lineage, additions/deletions, and benchmark changes |
| Provider-consistent company/float inputs | Local links can aid reconciliation but are not provider assignment inputs | Company-level caps depend on issuer aggregation and float-adjusted capitalization | Historical provider mapping, shares, IWF/float factors, precision, and effective-date corporate actions |
| Public-information timing | Some source dates/pro-forma dates are known; holdings filing/publication/download semantics are incomplete | Anticipation and trader-time availability cannot be inferred from report dates | Contemporaneous publication timestamps and source-vintage metadata, with unknown times left unknown |
| Holdings snapshot and local coverage gaps | The archive audit records absent candidate report months and isolated field/return coverage limitations | Interpolation can create false pre/post portfolios or selectively change the residual universe | Resolve each design-relevant fund-month against saved batch metadata/provider documentation; predeclare handling of missing rows and retain the observed gap rather than filling it silently |
| Rounded retrospective tables | Selected rows can screen cap distortions | Rounding can change threshold/binding classification and incomplete vectors cannot conserve weight | Exact source files; otherwise conduct honest interval/boundary sensitivity and retain B/U status |

### 6.2 Identification and counterfactual

| Gap/assumption | Current evidence | Why it matters | Evidence or change needed |
|---|---|---|---|
| Mechanical-weight confound | Explicitly identified, not yet replayed | The index identity alone can make high-weight stocks look more important | Apply actual/alternative fixed weights to identical, corporate-action-consistent price paths; report decomposition-order sensitivity; use focal-stock-excluded targets |
| Rebalancing demand/price pressure | Existing literature and event mechanics make it plausible | Flow, liquidity, hedging, and reversals can mimic information transmission | Measure predicted/realized demand where feasible; pre/post reversal and liquidity tests; avoid controlling away mediators when estimating total effects |
| Heterogeneous macro-news exposure | Not resolved by using the same signal stock across baskets | Different basket betas, sector composition, and residual noise can generate different responses/predictability | Pre-period exposure estimation, fixed residual membership, common support, matched non-giants, and falsification under simulated heterogeneous loadings |
| Signal precision and quote quality | Not measured in Gate 1 | Earlier/cleaner quotes can look like causal transmission | Quote-age/venue/feed controls, timestamp perturbations, symmetric prediction, and latency/noise simulations |
| Endogenous threshold crossing and provider discretion | Numerical rules are documented, but a valid one-dimensional discontinuity is not | Rule publication alone does not create random assignment | Exact running variables/ranks and inputs; manipulation/precision analysis; multidimensional boundary treatment; abandon RD language if unsupported |
| Interference and dependence | Shared dates, issuers, baskets, and FOMC meetings are mapped | Basket rows and repeated issuers are not independent experiments | Define event-group/issuer/meeting inference, leave-one-group analyses, spillover-aware comparisons, and a small number of defensible clusters |
| Counterfactual comparison | No clean comparison is yet established | Same-stock/cross-index designs may share treatment or differ in exposure | Freeze one estimand and comparison before outcomes; demonstrate remaining matrix variation after fixed effects/controls; state strongest exclusion and falsification |
| September 2024 transition | One common policy change affects many baskets | Treating sectors as independent shocks grossly overstates support | Use one intervention group with cross-sectional exposures and dependence-aware inference, or omit it in leave-one-transition analysis |

### 6.3 Outcome measurement and data feasibility

| Gap/assumption | Current evidence | Why it matters | Evidence or change needed |
|---|---|---|---|
| Modern intraday stock/ETF paths | Not established; available MIDAS material is daily | Daily data cannot measure millisecond/second adjustment, quote disagreement, clocks, or event-level variance | Bounded quote/trade sample for frozen securities and sessions, with identifiers, exchange/SIP timestamps, condition codes, prices/sizes, quote age, halts, and source changes |
| Futures-inclusive claim | Futures histories/roll/clock package is not established here | Stock–ETF evidence cannot answer ETF–cash–futures architecture | Either acquire actual contracts, rolls, quotes/trades, basis/carry and clock metadata, or explicitly narrow to stock–ETF |
| Residual portfolio definition | Prospective only | Post-treatment survival/quote availability or changing weights can manufacture effects | Pre-announcement frozen membership and aggregation; fixed initial quantities with corporate-action adjustments; value- and breadth-sensitive outcomes |
| Efficient-price/quality benchmark | Not chosen or validated | Price agreement is not fundamental accuracy; later price/futures is not truth | External/cross-fitted shock benchmark or explicit latent-price assumptions; terminal-window sensitivity; no circular shock construction |
| Common-news shock | FOMC calendar and USMPD availability only | Calendar overlap is not a surprise measure or valid instrument for giant prices | Verify shock construction, package phases, real-time availability, central-bank information, and direct effects on every market |
| Data licensing, redistribution, and access | Archive access is verified only for audited families; future packages remain uncertain; public Stage A identifiers/locators are redacted, but aggregate-output redistribution has not received an independent license determination | Feasibility claims must distinguish documentation from entitlement, and a technically redacted export is not itself a legal conclusion | Obtain institutional/license confirmation for public aggregate release and written/technical confirmation for the bounded pilot; do not purchase until assignment and design gates clear |

### 6.4 Statistical power and inference

1. Calendar overlap counts are not independent shocks, treatments, or clusters. The authoritative summary deliberately reports meetings, intervention groups, ledger event rows, and event-group–meeting pairs separately.
2. No exact signed assignment vector exists in the executed package, so absolute dose support, residualized rank, leverage, information-effective support, and dominance diagnostics are correctly not computed.
3. No intraday outcome pilot exists, so event-level variance and covariance cannot be calibrated and no meaningful MDE can be reported.
4. Slow-moving regimes, repeated issuers, shared meeting dates, shared constituents, and one common transition reduce effective variation.
5. A future design analysis must simulate both a no-transmission-change null with changing weights/exposures/noise/clocks and a known transmission change; resampling must re-estimate generated weights, exposures, and forecasts where appropriate.
6. Inference must be tied to the actual assignment and shock units, with honest few-cluster limitations. Tick counts cannot rescue thin intervention support.
7. Primary outcomes, horizons, event rules, groups, transformations, and exclusions should be frozen after measurement development and before main outcome inspection.

### 6.5 Novelty and economic importance

1. Novelty is unresolved because Gate 1 was not the exhaustive literature review required by the upstream prompt.
2. A larger arithmetic contribution by giant stocks, a newer leadership ranking, or another information-share estimator is not a sufficient contribution.
3. A robust predictive relationship is not automatically causal transmission, fundamental information, or market-wide quality.
4. Even a credible intervention effect must show why it matters beyond who leads: faster completion, reduced disagreement/reversal, broader residual-stock incorporation, or resilience under a pre-specified mechanism.
5. Welfare language would require a separate model/evidence; faster or more synchronized prices are not automatically socially better.
6. Publication potential is conditional on clearing assignment, comparison, measurement, novelty, and power gates. No acceptance probability is claimed here.

### 6.6 Current Gate 1 posture represented by the artifacts

- **Observable treatment:** the public records support documented rule regimes and selected binding events, but the package does not yet establish a complete grade-A historical assignment vector. Exact-dose treatment is therefore not presently observable.
- **Comparison credibility:** the package maps mechanical, exposure, timing, issuer, date, and spillover threats but does not establish a credible counterfactual. This remains a scientific design gap, not a clerical omission.
- **Independent common-news support:** eligible FOMC dates and event intersections are reproducibly mapped, but overlap is not independent variation or statistical power. The controlling counts and counting units are in `logs/gate1_summary.json`.
- **Future outcome measurability:** the audited archive does not establish the modern intraday paths required for the intended speed/quality outcomes. Daily data are not substituted.
- **Smallest decision-changing next step:** recover authorized, timestamped, complete Select Sector assignment/pro-forma inputs and point-in-time constituent/issuer/float lineage for the 2024 pilots; reconcile the rule replay; then freeze one counterfactual and inspect exact design support before investing in intraday data. The Nasdaq July 2023 pro forma is a separate cross-check, not a substitute for repeated Select Sector support.

The full rationale and exact wording also appear in `FINAL_DECISION.md`. This package does not replace that memo and does not claim an external referee endorsed it.

## 7. Artifact map and review order

Recommended review order:

1. `FINAL_DECISION.md` — final Gate 1 judgment and the exact next input/design action.
2. `logs/gate1_summary.json` — authoritative machine-readable counts and scope flags.
3. `remaining_input_gaps.csv` — decision-relevant unresolved inputs, statuses, and minimum resolutions.
4. `docs/EVIDENCE_CONTRACT.md` — definitions, evidence grades, and prohibited equivalences.
5. `source_and_rule_registry.csv` — source-level regime logic and provenance.
6. `rebalance_event_ledger.csv` — event universe, grouping, timing, and binding classifications.
7. `assignment_doses_and_evidence.csv` — available doses and exact limitations.
8. `fomc_calendar.csv` and `assignment_and_fomc_support.csv` — official common-news calendar and overlap mapping.
9. `comparison_and_interference_audit.csv` — proposed estimand/comparison threats and intentionally blocked diagnostics.
10. `local_data_catalog.csv` and `fund_identifier_and_coverage_audit.csv` — aggregate SCC archive audit.
11. `src/` and `tests/` — builders, validators, and executable invariants.
12. `logs/` — command/retrieval/test provenance; prefer the latest correction/final validation records over superseded intermediate logs.

| Artifact | Unit of observation | Primary use | Critical caution |
|---|---|---|---|
| `local_data_catalog.csv` | logical dataset/search object | What the SCC audit actually found | Availability does not prove target coverage |
| `fund_identifier_and_coverage_audit.csv` | fund × year | identifiers, snapshot gaps, mapping/price coverage | Holdings are screening, not assignment |
| `source_and_rule_registry.csv` | source/rule regime | versioned rule logic and source provenance | `rule_source_grade=A` is not event-dose grade A |
| `rebalance_event_ledger.csv` | scheduled-check/intervention row | complete potential-event calendar and grouping | Scheduled check is not realized treatment |
| `assignment_doses_and_evidence.csv` | event × security/all-vector record | observability grade and available numerical evidence | Selected rounded subsets are not complete vectors |
| `fomc_calendar.csv` | meeting/exception record | eligible common-news dates and package flags | Phases of one meeting are dependent |
| `assignment_and_fomc_support.csv` | event × anchor × meeting, or one unresolved-anchor record | distances, anchors, support bands, overlap flags | Rows are not independent observations |
| `comparison_and_interference_audit.csv` | event row | design threats and support gating | `NOT_COMPUTED` is deliberate where vectors are incomplete |
| `remaining_input_gaps.csv` | gap | blocker, minimum resolution, next action | Access gaps are not economic falsification |
| `logs/gate1_summary.json` | package summary | controlling counts/status distributions | Must come from the same reviewed commit |
| `src/*.py` | executable builder/validator | reproducibility and guardrails | Verify generated outputs match committed tables |
| `tests/*.py` | invariant test | schema, calendar, semantics, non-substitution | Passing unit tests does not validate causal assumptions |

## 8. Ready-to-paste referee instruction for Opus 5 High

Copy the following instruction together with this package and, if possible, the full `index-reweighting-gate1/` folder or repository link.

```text
You are an independent, skeptical referee for a prospective empirical-finance paper. Work read-only: do not edit the repository, contact vendors, purchase data, use credentials, or claim access you do not have. This is a manual-transfer review. No external Opus or Claude referee review of this Gate 1 execution is included or should be inferred.

Read the entire attached review package, including both verbatim prompts, and inspect the linked/attached Gate 1 artifacts and executable tests. Treat every citation, novelty statement, event classification, count, and contribution claim as a hypothesis to verify—not as an authority. Use primary sources and the current versions of papers wherever possible. Independently search the closest literature, including backward and forward citations, rather than accepting the supplied matrix at face value. Distinguish “not found” from “never studied.”

Independently evaluate:

1. Novelty: identify the closest papers and whether the proposed increment is more than a newer sample, more securities, a concentration interaction, or another price-discovery measure. Pay special attention to constituent–ETF tandem trading, systematic-information incorporation, index reweighting/demand shocks, passive flows, and index-instrument price discovery.
2. Economic importance: determine what outcome would matter beyond relabeling the price-discovery leader. State whether the mechanism has implications for speed, accuracy, breadth, reversals, disagreement, or resilience, and whether any welfare claim is supportable.
3. Mechanical-weight and demand confounds: assess whether arithmetic index composition, heterogeneous common-news loadings, provider float/share inputs, rebalancing flows, hedging, liquidity, signal precision, or quote quality can generate the intended findings without changed information transmission.
4. Causal identification: audit the assignment mechanism, treatment definition, counterfactual, timing/anticipation, threshold/rank dimensionality, provider discretion, shared issuers/dates, interference, spillovers, and inference units. Do not accept a published numerical rule as an RD or instrument without a valid assignment argument.
5. Measurement validity: assess whether the proposed stock, residual-basket, ETF, and optional futures objects have comparable payoffs, timestamps, clocks, units, corporate-action treatment, and support. Evaluate whether the information clock, common-news shock, efficient-price/quality benchmark, horizons, and fixed residual portfolio are defensible.
6. Data feasibility: verify what the executed archive audit actually establishes, what is only documented, what remains entitlement-dependent, and the smallest exact-assignment and intraday-data package needed for a credible pilot. Do not treat daily MIDAS or holdings snapshots as intraday paths or exact assignments.
7. Statistical power: use the distinct intervention-group, issuer, regime, and FOMC-meeting structure—not event-row or quote counts—to judge support. Determine what simulation-based design analysis and MDE calibration are possible only after exact doses and pilot outcome variances exist.

Verify the source-to-row lineage for the pilot events. Audit assignment-observability A/B/C/U separately from rule/source-completeness A/B/U and event-classification-evidence A/B/U; do not transfer one grade dimension into another. Reproduce or spot-check the builders/tests, and use `logs/gate1_summary.json` from the reviewed commit as the authoritative source for counts. Flag stale logs or inconsistencies rather than averaging them. Confirm that no licensed raw rows or credentials are exposed.

For every major objection:

- classify it as FATAL TO THE CORE CLAIM, FATAL TO THE CURRENT DESIGN BUT A NARROWER CLAIM MAY SURVIVE, or FIXABLE;
- explain the exact reasoning and which claim it affects;
- identify the evidence, source, diagnostic, or design change needed to resolve it;
- state what result would clear the objection and what result would make it fail; and
- distinguish lack of access from evidence that the economic mechanism is absent.

Return a structured referee report with:

A. Executive verdict and the strongest prospective contribution.
B. Verified closest-literature/contribution matrix, correcting any supplied citation or overlap claim.
C. Evidence-integrity audit (sources, event timing, assignment grades, counts, code/tests, and reproducibility).
D. Major objections ranked by severity, each labeled fatal/fixable as above with a resolution test.
E. Assessment of novelty, economic importance, mechanical confounds, causal identification, measurement validity, data feasibility, and power.
F. The minimum next evidence/design package and a stopping rule.
G. A conditional PROCEED / REDESIGN / STOP recommendation. State the conditions under which your recommendation would change.
H. A realistic publication-potential assessment for (i) a credible specialist-journal paper, (ii) a broader general-finance paper, and (iii) a plausible top-three-finance contribution. Do not invent numerical acceptance probabilities; state the contribution and evidence threshold for each tier.
I. A short list of claims the current Gate 1 package supports, claims it does not support, and unresolved points where the evidence is genuinely ambiguous.

Be adversarial but not performative. Do not assume either the executing model or your own first impression is authoritative. If primary evidence is unavailable, say exactly what you could not verify and make your conclusion conditional.
```

## 9. How the eventual response to the referee should be handled

When the actual Opus report is returned, the research plan should be revised point by point. For each criticism, the response should state: (i) accepted, contested, or unresolved; (ii) the evidence and reasoning; (iii) the concrete plan/table/code change; and (iv) any remaining condition. Neither model's judgment should be treated as authoritative merely because it is confident. No such independent report is included or simulated here.

## Appendix A — Upstream research-agent prompt (verbatim)

The text below is reproduced exactly from `index_concentration_research_agent_prompt.md` (SHA-256 above).

# Research-Agent Prompt
## Index Concentration and the Architecture of Price Discovery

### 1. Your assignment

Act as a skeptical research coauthor with expertise in financial economics, market microstructure, high-frequency econometrics, and empirical identification. Complete the research blueprint below into an integrated, literature-grounded, technically defensible research plan for **one paper**.

The central question is:

> As a broad equity index becomes increasingly dominated by a small number of very large companies, does the incorporation of common public information become more dependent on information transmission between those companies' shares and index instruments? What consequences does this have for the speed, accuracy, breadth, and resilience of market-wide information incorporation?

Do not assume that such a transition has occurred, that constituent stocks must gain importance, or that concentration must improve or impair efficiency. The project must distinguish a substantive change in information processing from arithmetic changes in index composition, changing exposures to macroeconomic news, and measurement artifacts.

Your task is to complete and critically revise this blueprint—not simply restate it, generate an attractive introduction, or list possible regressions. Make explicit design choices. Where a proposed method fails, explain the failure and replace it with the strongest defensible alternative. Where no defensible alternative exists, narrow the claim or recommend stopping that version of the project.

Produce a research plan, not fabricated findings. Do not claim to have accessed licensed data, reconstructed historical weights, estimated models, or verified institutional permissions unless you have actually done so. Distinguish established evidence, proposed assumptions, testable hypotheses, and unresolved dependencies throughout.

### 2. Starting position and scope

The inherited proposal centered on SPY–ES and QQQ–NQ, primarily around FOMC announcements during 2020–2023, without constituent stocks by default. That design is insufficient for the present question. This assignment explicitly expands the **proposed scientific scope** to constituent stocks, historically correct index weights, and the information relationships connecting stocks, ETFs, and futures. This is not authorization to purchase data or access accounts.

Use the S&P 500 constituent–ETF–futures system as the provisional primary setting. Use the Nasdaq-100 system as a deliberately selected comparison, not an interchangeable broad-market proxy or automatically valid control group. Explain its differences in composition, weighting rules, factor exposures, and trading environment.

Treat 2020–2023 as a possible pilot, not a binding main sample. Evaluate a longer window covering materially different concentration regimes; 2010–2025 is a candidate to assess, not a claim of verified data availability. Select the final period according to historical comparability, credible timestamps, concentration variation, event support, and data feasibility. A shorter reliable sample may be preferable to a longer incomparable one, but it must still identify something economically meaningful.

The paper is about **index-weight concentration and information processing**. ETF assets under management, ETF ownership of stocks, concentration across ETF products, and technological change are distinct objects. They may be mechanisms or competing explanations; they must not silently substitute for the main treatment.

Do not revive the cryptocurrency paper, add unrelated asset classes, or let infrastructure planning displace the economic question.

### 3. Reassess the literature before claiming a contribution

Conduct an updated literature search as of your execution date. Explicitly search this priority set: **American Economic Review, Quarterly Journal of Economics, Journal of Political Economy, Econometrica, Review of Economic Studies, Review of Economics and Statistics, Journal of the European Economic Association, Journal of Finance, Journal of Financial Economics, and Review of Financial Studies**. This is the requested search set, not a claim that there is a unique journal ranking.

Also search closely related specialist journals, relevant working papers, authors' research pages, and backward and forward citations. Do not overlook an older constituent–index paper because its title lacks “mega-cap,” “concentration,” or “Big Tech.” Search adjacent work on systematic versus firm-specific information, cross-stock lead–lag relationships, correlated trading, index reweighting, ETF arbitrage, and informational efficiency.

The following references are starting points, not an exhaustive review or proof of a gap:

| Starting reference | Boundary the completed plan must examine |
|---|---|
| Hasbrouck (2003), *Intraday Price Formation in U.S. Equity Index Markets*, Journal of Finance. DOI: 10.1046/j.1540-6261.2003.00609.x. | Existing index-instrument price discovery and interactions with component portfolios. |
| Wallace, Kalev, and Lian (2019), *The Evolution of Price Discovery in US Equity and Derivatives Markets*, Journal of Futures Markets. DOI: 10.1002/fut.22019. | Historical changes in ETF–futures leadership; updating an old ranking is insufficient. |
| Chordia, Green, and Kottimukkalur (2018), *Rent Seeking by Low-Latency Traders: Evidence from Trading on Macroeconomic Announcements*, Review of Financial Studies. | Public-announcement price discovery and the temporal resolution needed for meaningful speed claims. |
| Dimpfl and Schweikert (2023), *Information Shares for Markets with Partially Overlapping Trading Hours*, Journal of Banking & Finance. DOI: 10.1016/j.jbankfin.2023.106970. | Trading-hour differences and the interpretation of price-discovery shares. |
| Ernst, *Stock-Specific Price Discovery From ETFs*, working-paper starting reference; verify the latest version and status. | Stock-specific information, stock–ETF tandem trading, and the importance of constituent weights. |
| Glosten, Nallareddy, and Zou (2021), *ETF Activity and Informational Efficiency of Underlying Securities*, Management Science. DOI: 10.1287/mnsc.2019.3427. | ETF activity and the incorporation of systematic information into underlying stocks. |
| Ben-David, Franzoni, and Moussawi (2018), *Do ETFs Increase Volatility?*, Journal of Finance. DOI: 10.1111/jofi.12727. | Nonfundamental shocks and arbitrage-based propagation as alternatives to information transmission. |
| Khomyn, Putnins, and Zoican (2024), *The Value of ETF Liquidity*, Review of Financial Studies. | Differences between investment scale, secondary-market liquidity, and investor trading horizons. |
| Jiang, Vayanos, and Zheng (2025), *Passive Investing and the Rise of Mega-Firms*, Review of Financial Studies. | Passive flows, large-company prices, and the boundary between demand effects and information processing. |
| Haddad, Huebner, and Loualiche (2025), *How Competitive Is the Stock Market? Theory, Evidence from Portfolios, and Implications for the Rise of Passive Investing*, American Economic Review. DOI: 10.1257/aer.20230505. | Investor-demand adjustment and why passive-investing effects require an economic mechanism. |

Also locate Fang and Sanger's *Index Price Discovery in the Cash Market* and verify its version and publication history. Evaluate its actual overlap rather than relying on a title or abstract.

For the closest papers, inspect the relevant theory, empirical specification, sample, and identification argument wherever accessible. Record whether your assessment relies on a full paper, an abstract, or an unverified citation. Do not attribute findings that you have not checked.

Produce a contribution matrix showing the question, mechanism, identification, relevant result, and exact remaining increment relative to each closest paper. Include a column explaining how our proposed result could collapse into that paper's existing contribution. Distinguish “not found in this search” from “has never been studied.”

The proposed increment must be more than a newer sample, more stocks, another information-share measure, or a concentration interaction appended to an established regression.

### 4. State the economic mechanism before selecting estimators

Begin with the following conceptual obstacle:

> A correctly matched ETF and futures contract refer to the same underlying index. Greater concentration changes their common exposure. Why should that change their relative information-processing roles, or increase dependence on constituent-stock trading, rather than affect both instruments symmetrically?

Construct a parsimonious multi-asset mechanism that answers this question. One useful starting representation uses normalized security payoffs:

\[
V_i=b_i'F+u_i, \qquad V_I(w)=\sum_i w_iV_i,
\]

where \(F\) contains common fundamental factors and \(u_i\) contains firm-specific information. An ETF and its matched future represent economically adjusted claims on the same index payoff, while individual stocks retain heterogeneous common-factor loadings and firm-specific risk. This is a conceptual payoff representation, not permission to equate raw stock prices with index prices.

Public news changes beliefs about \(F\), but traders may differ in interpretation, processing delays, trading costs, inventory capacity, or access to instruments. Specify which asymmetry is economically necessary for weights to alter trading choices or the information conveyed by observed prices. Do not assume an advantage for giants simply to generate the desired prediction.

Develop competing hypotheses, including:

**Index-instrument dominance or resilience.** Common news is incorporated primarily through index instruments even at high concentration, potentially because they remain efficient vehicles for aggregate exposure.

**Greater giant–index interaction.** Concentration makes some large stocks more useful for expressing or inferring aggregate exposures, increasing their incremental role in joint price adjustment.

**Faster centralization with greater dependence.** More concentrated information processing improves normal-state adjustment but makes system performance more sensitive to impaired trading in a few important names.

**Mechanical or exposure-driven change only.** Apparent giant leadership rises because weights, macro sensitivities, liquidity, or measurement quality change, without a change in information transmission.

For each hypothesis, derive a directional prediction or a clearly stated condition determining the sign, the necessary assumptions, and an observation that would contradict it. Identify which predictions distinguish the hypotheses rather than fit all of them.

A tractable model is useful only if it disciplines measurement or identification. Supply a minimal formal model or a tightly specified mechanism with comparative statics; do not turn the paper into an unrelated theory project. Distinguish information already public from new information inferred through trading, and distinguish price informativeness from socially valuable information production.

### 5. Define concentration, giants, and the relevant market system

Let \(w_{i,e^-}\) be the historically valid index weight available before announcement \(e\). The provisional main concentration measure is

\[
C_{e^-}=\sum_i w_{i,e^-}^{2}, \qquad N^{\mathrm{eff}}_{e^-}=1/C_{e^-}.
\]

Specify whether this is measured at the security or issuer level. Prefer issuer-level concentration for the economic concept, with a transparent mapping from multiple share classes to traded securities. Do not double-count a company as two independent information-processing firms.

Provisionally define giants as the ten largest issuers at the preceding month-end, freezing group membership within the month. Use historically available information and retain an auditable index-membership history. Examine top-five and alternative predeclared group definitions as sensitivity checks. Do not select today's successful technology companies retrospectively.

Treat “large constituent” and “technology company” as different classifications. Distinguish within-firm changes in index importance from changing identities of the largest companies. Explain how concentration differs from sector composition, systematic-risk concentration, investor ownership concentration, and liquidity concentration.

Construct a giant-stock basket and a residual-constituent basket. For a correctly defined fixed-quantity event-window portfolio, its simple return can be decomposed as

\[
R^B_e(h)=\sum_i w_{i,e^-}R_{i,e}(h)
=W_{G,e^-}R^G_e(h)+(1-W_{G,e^-})R^R_e(h).
\]

Define every term and adjustment. Explain when this represents the target index and when divisor changes, distributions, corporate actions, ETF cash, or tracking differences require a different mapping. Do not present a weighted sum of log returns as an exact index identity.

Observe the remainder of the index as well as giants. A study containing only a few large stocks and index instruments cannot establish a change in market-wide information incorporation. A representative residual sample may support a pilot, but its representativeness and the limits on aggregate claims must be explicit.

### 6. Make mechanical composition the first empirical adversary

The essential distinction is between changes in the weight placed on existing stock-price processes and changes in those processes or their interactions.

Develop an accounting exercise using identical observed constituent-price paths under actual and alternative fixed weights. Explain what changes purely because the aggregation rule changes. Use stable, historically feasible reference portfolios and common support; do not introduce survivorship bias by retaining only firms that survive the full sample.

For a statistic \(M\) depending on weights \(w\) and observed price paths \(P\), a useful conceptual decomposition is

\[
M(w_1,P_1)-M(w_0,P_0)
=\{M(w_1,P_0)-M(w_0,P_0)\}
+\{M(w_1,P_1)-M(w_1,P_0)\}.
\]

Make this operational only where assets, units, and support are comparable. Explain decomposition-order dependence and consider a symmetric version when appropriate. The second term is a non-accounting remainder, **not automatically a causal behavioral effect**.

Build a simulation benchmark in which weights change but information-processing technology and transmission relationships do not. Allow heterogeneous macro sensitivities, idiosyncratic risk, quote noise, trading intensity, and asynchronous updates. Determine whether the proposed statistics falsely report an increasingly important giant-stock channel.

Require leave-giant-out targets and matched non-giant comparisons where appropriate. Examine whether giants predict subsequent adjustments in other stocks or independently traded instruments beyond contemporaneous public news and the mechanical index identity.

Reweighting realized prices is an accounting counterfactual. It does not recover equilibrium prices, liquidity, or trading choices under an alternative index rule. State this limitation explicitly.

### 7. Select common-information events and define the information clock

Use a complete, rule-based sample of scheduled FOMC statements during suitable overlapping trading sessions as the provisional primary event setting. Verify each historical release time and institutional regime; do not apply current announcement conventions retrospectively. Separate statements, simultaneously released materials, and press conferences. Treat phases from the same meeting as dependent observations.

Evaluate whether this setting alone provides enough independent events and concentration variation. Additional scheduled macroeconomic releases may improve support, but only through an explicitly justified expansion. Do not pool premarket CPI announcements with regular-session FOMC announcements as if their trading environments were identical.

Specify the information being priced. Distinguish a public announcement package from a separately identified structural monetary-policy shock. Address target-rate news, expected-policy-path news, central-bank information, and overlapping announcements only to the degree supported by the chosen surprise measures and sample size.

Use an externally constructed macro surprise where defensible. The San Francisco Fed's U.S. Monetary Policy Event-Study Database is a candidate source to investigate, not a substitute for original stock and futures quotes. Verify its version, event windows, instruments, coverage, and use restrictions.

Crucially, a surprise measured using prices over a later window may support a retrospective announcement-response analysis but is not necessarily information available during the first milliseconds or seconds. Do not use future-window information inside a supposedly real-time prediction model. Do not define the shock from the same equity-index outcome and then interpret the resulting relation as independent identification.

Public news is not automatically a valid instrument for giant-stock prices: it can directly affect ETFs, futures, and all other stocks, violating the exclusion restriction needed to identify a giant-to-index causal channel.

Include pre-event behavior, announcement leakage, simultaneous firm-specific news, and rule-based matched nonannouncement periods. Do not select control days because their realized returns are small.

### 8. Separate three empirical questions

#### A. Does the observable information-processing pattern change?

Estimate announcement-response paths for index instruments, the giant basket, and the residual basket. Adjust interpretation for different common-news loadings. Larger responses do not mean faster incorporation.

A starting descriptive specification is

\[
R_{m,e}(h)=a_{m,h}+b_{m,h}'S_e
+d_{m,h}'(C_{e^-}S_e)+g_{m,h}'X_{e^-}+\varepsilon_{m,e,h}.
\]

Complete or replace this equation with explicit definitions, units, exposure adjustment, sample restrictions, and an identification discussion. Explain which variation identifies each coefficient and why a concentration interaction is not automatically causal. Allow for changing macro sensitivities without estimating an unrestricted model that the number of events cannot support.

Where using event fixed effects, specify which relative responses or cross-sectional interactions remain identified. Do not write a regression that absorbs the main source of variation and then interpret a nonexistent concentration coefficient.

#### B. Do giants provide incremental predictive information?

Construct a small, interpretable forecasting comparison. For a fixed target and horizon, compare out-of-sample loss using an index-instrument information set with loss after adding historically available giant-stock information. A conceptual object is

\[
\Delta L_{G\rightarrow I}(h)
=L_{\mathrm{test}}(\text{index history and available news})
-L_{\mathrm{test}}(\text{same information plus giant history}).
\]

Define the target return, forecast origin, available information, loss, training sample, and horizon. Examine the reverse direction and the giant-to-residual direction. Use equal-complexity comparisons with matched non-giants. Separate training and evaluation by entire events or temporal blocks, not random ticks from the same event.

Investigate whether the incremental signal survives controls for common-news content, stale quotes, different reaction loadings, correlated order flow, and feed delays. A forecast improvement for subsequent prices is evidence of predictability, not by itself evidence of fundamental information or causal transmission.

For each claim, explain what would distinguish observation of earlier giant quotes from genuine dependence on those quotes. A contemporaneous common shock with heterogeneous response delays can generate apparent directional prediction without one market learning from another.

#### C. Does concentration change market-wide information quality?

Choose a small number of outcomes tied to the mechanism. The provisional priorities are announcement-response completion, temporary pricing disagreement among claims on the same basket, and adjustment in the residual constituents. Resilience is a conditional mechanism extension, not a mandatory additional paper.

Explain how a finding about relative leadership relates—or fails to relate—to these system outcomes. A transfer of leadership can leave overall information incorporation unchanged.

### 9. Measure speed, accuracy, and breadth without inventing the efficient price

Select one primary information-processing outcome and one primary market-quality outcome after a measurement-focused pilot. Provide economic units, aggregation rules, and interpretation. Keep the number of primary horizons small; a provisional diagnostic grid is 100 milliseconds where credible, 1 second, 5 seconds, 30 seconds, and 2 minutes. Retain only horizons justified by the data and the mechanism.

Do not call one-second data evidence about who incorporates news first when the relevant adjustment may occur at much finer resolution. If the data only identify slower completion, overshooting, or residual disagreement, frame the contribution accordingly.

Possible speed measures include convergence of pooled shock-response coefficients toward a justified later-horizon response, or appropriately censored response-completion times. Avoid event-by-event normalization by a noisy or near-zero final return. Address sign changes, overshooting, nonmonotone adjustment, and additional news during the terminal window.

For pricing quality, distinguish agreement among prices from accuracy relative to fundamentals. Consider independently constructed or cross-fitted common-news benchmarks, latent-price estimates with explicit identifying assumptions, and temporary basis deviations among economically matched instruments. Explain benchmark contamination and test sensitivity to different terminal windows or measurement systems.

Do not declare the futures price to be the true value while testing whether futures incorporate information first. A later price is not automatically the correct fundamental value, and a macro-surprise regression predicts an average response rather than revealing every event's true efficient price.

Report information incorporation in the residual basket under both economically justified value weights and a breadth-sensitive aggregation such as equal weighting. Distinguish index-level improvement from improvement across companies. Increased contemporaneous comovement is not sufficient evidence of better information incorporation.

Any resilience claim must specify the impairment, its plausibly independent variation, and its effect on trading elsewhere. A few selected halts or outages cannot establish general fragility, and deleting giant quotes in a simulation is not equivalent to removing giant trading in the real market.

Do not equate faster adjustment or lower basis dispersion with higher welfare without an additional model and evidence.

### 10. Use price-discovery methods only where their economic restrictions hold

Distinguish same-payoff price discovery from information transmission between different securities. Raw prices of individual stocks, a residual portfolio, an ETF, and a future generally should not be placed in a single-common-efficient-price system simply because all respond to the same announcement.

An economically adjusted ETF, matched future, and correctly reconstructed full cash basket may justify a same-payoff framework. Individual stocks generally require heterogeneous factor loadings and firm-specific components. Propose a low-dimensional factor, state-space, or other defensible alternative if constituent-level dynamics are modeled jointly.

For any information-share or error-correction analysis, state cointegration restrictions, carry adjustments, treatment of announcement jumps, sampling frequency, estimation support, and sensitivity to noise and correlated innovations. Show identification or ordering uncertainty rather than selecting one convenient ordering.

Do not estimate a high-dimensional short-window model with hundreds of constituents and a handful of announcements. Do not concatenate disconnected event windows as though they were continuous trading time. Do not count a published index, indicative NAV, or another mechanically computed feed as an independent price-discovery venue.

Keep information shares as supporting evidence unless their economic interpretation and finite-sample performance are particularly strong for this design. A complicated statistic should not replace a transparent answer to the central question.

### 11. Build an explicit identification hierarchy

Separate **conditional historical evidence**, **evidence about a specific weight-changing intervention**, and **causal information transmission between markets**. These are different achievements.

For the historical analysis, assess confounding from secular improvements in trading technology, data-feed changes, passive investment, liquidity, firm growth, sector composition, macro exposures, monetary-policy regimes, and the endogenous effect of past returns on weights. Lagging concentration does not make it exogenous. Predetermined liquidity can itself reflect earlier concentration; distinguish descriptive conditioning from causal adjustment.

For stronger identification, investigate rule-driven index reweighting or weight caps. One documented candidate is the Nasdaq-100 special rebalance announced on July 7, 2023 and effective before the July 24, 2023 market open; Nasdaq stated that it redistributed weights without adding or removing securities. Treat this as a candidate institutional setting, not an already valid natural experiment.

Audit announcement and implementation dates, anticipation, weight-rule mechanics, eligible prior and subsequent episodes, trading-flow effects, contemporaneous earnings and macro news, and the number of independent observations available. Determine whether the proposed setting changes the intended economic object and provides adequate comparison support.

Identify treatment at the appropriate level: a particular rule-induced weight vector, an exposure to a reweighting, or another well-defined intervention. “Increase HHI by one unit” is not a complete causal treatment when different reallocations can produce that change and have different consequences.

Select one preferred identification strategy after the audit. Provide its estimand, assignment mechanism, comparison group, identifying assumptions, implementation equation, inference level, and strongest falsification. Rank fallback approaches rather than listing many unconnected methods.

Address anticipation, endogenous threshold crossing, interference across overlapping indexes, and shared constituent trading. The same stock observed through two index memberships does not create two independent stock-price realizations. A cap-weighted and an equal-weighted index have different payoffs, and shared stocks do not make them clean treatment and control systems.

Distinguish the total effect of a reweighting—including induced flows and liquidity adjustments—from a hypothetical direct effect holding those channels fixed. Do not control away post-treatment mediators and then call the coefficient the total effect. Do not present a mechanically constructed instrument without defending its exclusion restriction.

A well-established new fact can be valuable without quasi-experimental identification. If the strongest defensible design is descriptive, state that clearly and explain what contribution remains. Conversely, do not use causal language merely to make the paper appear more publishable.

### 12. Specify decisive mechanism tests and falsifications

Produce a compact matrix linking each hypothesis to its predicted pattern, feasible test, closest competing explanation, and rejection criterion. Prioritize tests capable of invalidating the preferred interpretation.

At minimum, address a mechanical-weight benchmark; matched non-giant groups; giant-excluded target portfolios; common-shock exposure differences; reverse-direction prediction; timestamp perturbations within plausible uncertainty bounds; quote-age restrictions; changing membership; and nonannouncement placebo windows.

Distinguish systematic public-news results from stock-specific information effects. Earnings announcements can be a separately justified mechanism contrast, but must not silently replace the main common-information question.

Separate contemporaneous agreement, persistent predictive content, and temporary reversals. Test whether results could instead reflect demand pressure, hedging, or noise transmission. Order-flow patterns alone do not reveal trader identity or informed intent.

Choose which tests are essential for the headline claim and which are supplementary. Do not use an endless robustness menu to compensate for a missing identification argument.

### 13. Data feasibility and the minimum viable scientific design

Build a data-to-claim matrix covering historically correct constituents and weights; stock and ETF quotes and trades; actual futures contracts and roll metadata; announcement calendars and surprise measures; corporate actions; and pre-event liquidity and exposure variables.

For each item, identify an authoritative candidate source, required fields, historical resolution, known limitations, licensing uncertainty, and the claim that fails if it is unavailable. Distinguish verified documentation from verified user access. Do not invent WRDS schemas, commercial coverage, or an entitlement to exchange feeds.

Check whether weights correspond to index methodology or merely ETF holdings or approximate market-cap shares. These are not automatically interchangeable. Preserve point-in-time membership, float adjustments where needed, identifier mappings, and share-class treatment.

Audit exchange versus dissemination timestamps, SIP versus direct-feed timing, cross-location clock comparability, quote age, odd-lot treatment, trading halts, locked or crossed markets, price scales, and source changes. Displayed timestamp precision is not evidence of equivalent economic timing accuracy. Do not calibrate unknown clock offsets by maximizing the lead–lag result under study.

Use actual futures contracts with predeclared roll rules and appropriate basis treatment. Do not infer executable arbitrage profits from midpoint differences. Keep closed markets, stale quotes, missing feeds, and unavailable licenses as distinct states.

Define a minimal pilot that includes the index instruments, historically selected giants, a defensible residual-stock group, and events spanning different concentration levels. State what requires full constituent coverage. A pilot establishes scientific feasibility, not a paper's final result.

Keep data engineering at the level necessary to judge feasibility. No production download scripts, invented credentials, or extensive infrastructure plans are required for this assignment.

### 14. Inference, power, and design discipline

Identify the effective sources of independent variation. Quotes are not independent macroeconomic shocks. Multiple markets responding to the same announcement are not independent experiments. Slowly changing concentration also means that the number of announcements can overstate independent concentration variation.

Propose inference that respects event dependence, shared meetings, overlapping portfolios, persistent concentration regimes, and any policy or reweighting assignment level. Explain limitations with few clusters or a single intervention. Do not solve them by choosing a convenient bootstrap label.

Use simulation-based design analysis before interpreting empirical nulls. Include a no-transmission-change null with changing weights, heterogeneous exposures, quote noise, stale observations, and plausible clock offsets. Also simulate a known transmission change to assess detection power and whether the method separates speed from noise reduction.

Report minimum detectable effects in interpretable economic units and assess whether the historical support can detect a scientifically meaningful change. Re-estimate generated weights, betas, latent factors, and forecasting models within resampling or cross-fitting procedures where uncertainty requires it.

Separate a measurement-development sample from final evaluation where feasible. Freeze principal outcomes, event rules, group definitions, horizons, transformations, and exclusions before inspecting the main concentration results. Correct for the small prespecified family of primary tests.

A statistically insignificant result is not evidence of stable architecture unless the confidence interval excludes changes of meaningful size. Conversely, a statistically detectable microsecond difference is not necessarily economically consequential.

### 15. Decide what would actually constitute a contribution

Evaluate the following possible outcomes separately:

**Only arithmetic changes.** Giants have larger measured contributions because their weights rose. Explain why this would generally fail to establish the proposed contribution.

**A robust change in conditional predictive relationships.** State the new fact and its remaining causal limits; assess whether it meaningfully exceeds the closest literature.

**A defensible effect of a specific weight-changing intervention.** State what the intervention identifies and whether changes in market-wide quality accompany changes in leadership.

**Different speed and quality effects.** Concentration could speed adjustment but worsen reversals, improve index pricing without helping other stocks, or change leadership with no aggregate effect. Do not compress these outcomes into one favorable narrative.

**Precisely estimated stability.** Explain when stability despite concentration growth would test an economically important hypothesis rather than merely reproduce a familiar ranking.

**Insufficient novelty, support, or measurement.** Identify the specific failure and recommend a focused redesign or stopping the project, rather than searching for a significant secondary result.

Assess publication potential conditionally. Explain the economic and evidentiary threshold for a credible specialist-journal paper, a broader finance paper, and a plausible top-three-finance contribution. Do not invent acceptance probabilities or treat a fashionable motivation as a substitute for contribution. Recommend **proceed**, **proceed only after specified gates**, **redesign**, or **stop**, with a reasoned basis.

### 16. Required final deliverable

Write the completed plan entirely in English. Aim for approximately 8,000–12,000 substantive words, excluding references, but prioritize a coherent, decision-ready design over length. Use equations where they clarify estimands and tables where they expose comparisons; avoid padding and repetitive caveats.

Organize it around: an executive research decision; a precise contribution statement and literature matrix; economic mechanisms and discriminating hypotheses; definitions and portfolio construction; event and sample selection; primary outcomes and estimators; the mechanical benchmark; the preferred identification strategy and fallback; mechanism tests; data feasibility; inference and power; expected exhibit shells; and scientific continuation gates.

Complete the actual choices within these sections. Do not merely return instructions to “choose a measure,” “find an instrument,” or “run robustness checks.” Explain the strongest feasible choice, why it is preferred, and what remains conditional on information unavailable to you.

Include one integrated mapping from **claim → estimand → identifying variation → outcome → required data → decisive falsification → interpretation limit**. Provide a short proposed abstract written without invented findings and a compact list of main tables and figures, each tied to a question rather than a method name.

End with an adversarial assessment of the five strongest referee objections and whether the plan genuinely answers them. State the single strongest prospective contribution, the single greatest unresolved vulnerability, and the earliest scientific result or feasibility failure that would change the recommendation.

The completed plan must answer this final question:

> What evidence would distinguish a real change in how the market incorporates common information from a larger arithmetic role for the same stocks—and what would establish that the change matters beyond relabeling the price-discovery leader?

## Appendix B — Gate 1 execution prompt (verbatim)

The text below is reproduced exactly from `index_reweighting_gate1_execution_prompt.txt` (SHA-256 above).

# Execution Prompt: Rule-Based Index Reweighting — Assignment and Support Audit

## 1. Assignment and decision to be made

Act as a skeptical empirical-finance coauthor and research programmer. Execute a bounded, evidence-producing feasibility audit for one prospective paper. Do not write another full research plan, fabricate empirical results, or begin headline outcome regressions.

The motivating question is whether changes in a company's assigned weight in a traded index basket alter common-information incorporation in other securities, beyond arithmetic portfolio reweighting, heterogeneous common-news exposure, signal precision, and temporary rebalancing pressure.

The immediate question is narrower:

> Can the existing WRDS archive, supplemented by publicly accessible primary-source institutional records, support a defensible sample of repeated rule-based index reweightings with observable assignments, credible comparison support, and sufficient distinct intervention and common-news dates to justify a later measurement pilot?

This is Question 1—assignment and support—from the prior project evaluation. A successful audit supports proceeding to a later pilot, not declaring the paper identified or adequately powered. A failed retrieval establishes an access gap, not necessarily the nonexistence of the data or economic mechanism.

Use the attached `P1_Refraction_WRDS_Data_Usage_Manual_UPDATED_20260903(1).md` as the archive guide, denoted [M]. Its statements about physical holdings must be checked on the actual filesystem. Earlier proposals and referee reports are hypotheses to evaluate, not authorities. In particular, do not assume that every rebalance binds, that published rules imply random assignment, or that using the same signal stock across baskets automatically cancels precision confounds.

The inherited historical-HHI study is not the preferred design. Do not revive it as the main paper because it is easier to estimate. Do not pivot to mutual-fund conversions, cryptocurrency, or earnings-information papers. Preserve all frozen P1 and Refraction specifications and outputs.

## 2. Scope, access, and data contract

Use 2018–2025 as the provisional archival screening window, with earlier observations only where independently verified and useful. Treat 2026 as a separate partial extension, not part of a complete primary year. Availability for an entire dataset family does not establish coverage for any particular ETF or date.

Prioritize the U.S. Select Sector index family and its historically corresponding U.S.-listed SPDR ETFs. Audit Nasdaq-100 quarterly and special reweightings separately; the July 2023 episode is an institutional cross-check, not several independent interventions. A current ticker list is a discovery aid, not a point-in-time universe. Account for fund inception, classification changes, benchmark changes, and sector reorganizations. Do not substitute similarly named UCITS or differently capped products.

The documented archive is:

```text
ARCHIVE=/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902
PROJECT=${ARCHIVE}/p1_refraction_wrds_shared
BASELINE_MANIFEST=${ARCHIVE}/_migration_meta/FINAL_SCC_MANIFEST.tsv
POST_SNAPSHOT=${PROJECT}/raw/rescue_remaining/near_taq
```

Check these paths before claiming access. If unavailable, accept a user-supplied relocated root preserving relative paths. If neither exists, complete the public-record and analytical parts, produce the runnable audit code, and clearly mark every unexecuted local-data task `BLOCKED_ACCESS`. Do not report invented row counts or a local audit as completed.

The manual documents the following starting expectations, not verified inputs for this run:

- Legacy CRSP daily security data approximately 2014–2024, with newer/CIZ candidate extensions including 2025; harmonization and per-security coverage remain necessary [M §§6–7].
- CRSP holdings-report snapshots approximately 2018–June 2026, not daily holdings histories [M §12].
- Daily MIDAS security summaries for 2012–2025, not intraday quotes, event-time order imbalance, or observed quote-arrival paths [M §26A].
- Corporate actions, fund metadata, Compustat, I/B/E/S, and linking tables, subject to actual schema and coverage checks. The recovered legacy CRSP–TAQ link ends in 2014 [M §§10–24, 26B].
- No modern raw TAQ or IID/QID access was established; the documented tests found no access [M §40]. Exact historical index assignment inputs and CME intraday histories are not established by this manual.

Do not reopen failed WRDS entitlement searches absent evidence that access changed. Do not purchase data, start paid trials, contact vendors, register accounts, or bypass access controls. Public institutional research and permitted downloads are allowed. Keep proprietary data and credentials within the authorized research environment.

## 3. Stage A: verify only the local data relevant to the decision

Treat the SCC mirror as read-only. Write code, metadata, logs, and derived outputs to a new run-specific directory outside the archive. Never delete, overwrite, or synchronize the raw archive from the intentionally pruned WRDS source. In particular, never use whole-project `rsync --delete` [M §§2, 64–65].

Read the baseline manifest and directly scan the post-snapshot area. Locate relevant logical datasets across `raw/`, `raw/maximal/`, `raw/rescue/`, and `raw/rescue_remaining/`. Inspect schemas and Parquet metadata before selective reads. Resolve overlapping copies rather than stacking them. Retain file-level provenance; use canonical monthly MIDAS files, not superseded quarterly copies. Do not reconstruct the entire archive unnecessarily.

Produce an auditable, narrow catalog covering candidate funds, holdings, stock/ETF daily returns, corporate actions, issuer mappings, and historical sector or index membership if actually present. Index return series, industry membership, and constituent membership are different objects; verify which one a table contains. Do not infer index membership from a suggestive filename.

For each candidate fund and period, report available identifiers, holdings-report dates and gaps, mapped constituent coverage, price coverage, critical missing fields, duplicates, and source changes. Distinguish the holdings as-of date from filing, publication, and download dates. A retrospective reconstruction may use later-published evidence about an earlier holding, but such evidence cannot be described as information available to traders beforehand.

Use effective-date links and preserve security-to-issuer relationships. Do not extrapolate the legacy TAQ link into modern years or join long histories on ticker alone. Confirm actual bid/ask or open-price fields before promising those measures. Extract ETFs separately from common-stock filters where required.

CRSP holdings may support fund identification, historical composition screening, and validation for this new audit. They may not replace frozen SEC N-PORT treatment data for P1/G9, and they do not automatically become exact index assignments here. Do not turn a fund's total shares outstanding into daily creation/redemption flows; the manual explicitly rejects that use for the tested SPY series [M §§10, 34].

## 4. Stage B: establish the historical rule and event universe

Build a source-linked rule registry before reconstructing treatment. For every applicable regime, record the source, document/publication date, effective interval, relevant index, and whether the rule operates at company or security-line level. Preserve the full order of operations: input weighting, trigger checks, rank-based selection, single-company capping, aggregate capping, redistribution, and secondary checks.

Distinguish a trigger threshold from the target weight or aggregate weight after adjustment. A rank-dependent weight cliff is not necessarily a one-dimensional HHI cutoff. Identify whether the candidate discontinuity is in treatment levels, slopes, rank ordering, or a multidimensional boundary. Never declare regression discontinuity solely because the methodology contains numbers.

Start with these verified document leads; retrieve and inspect them yourself:

**[S1] S&P DJI, September 3, 2024, Select Sector constituent-weighting consultation results.** The notice distinguishes old and updated procedures, changes the secondary check, and specifies implementation before the September 23 market open and pro forma visibility beginning September 13. Do not conflate the trading close implementing a change with its next-open effective date.

```text
https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20240903-1474128/1474128_sp-select-sector-indices-results-20240903.pdf
```

**[S2] S&P DJI, August 2024 Select Sector capping analysis.** Use its explanation and historical examples to locate candidate events and validate rule logic. Separate actual/current-rule information from proposed-method backtests. A simulated historical application is not a realized historical treatment. Rounded top-15 tables are not complete, precise assignment vectors.

```text
https://www.spglobal.com/spdji/en/documents/additional-material/select-sector-capping-impact-analysis-20240808.pdf
```

**[S3] Nasdaq, July 7, 2023 special-rebalance schedule.** It distinguishes the July 3 reference date, July 14 pro forma release, and July 24 effective date. A public notice that a file was released does not establish that its historical contents are freely accessible.

```text
https://indexes.nasdaqomx.com/docs/NDX_SpecialRebalance_2023.pdf
```

Find additional contemporaneous methodology versions and announcements as needed. Do not backcast today's rules. For PDF tables, check the rendered table, headers, footnotes, and page numbers against extracted text. Record blocked retrievals and evidentiary limitations rather than relying silently on search snippets.

Build a calendar of potential quarterly and secondary checks, but classify each occurrence separately as confirmed binding, confirmed nonbinding, uncertain, or outside the applicable regime. Scheduled checks are not realized treatments. Keep discretionary or methodology-change episodes separate from routine applications. Include eligible nonbinding and near-boundary observations, not only famous dramatic changes.

Begin reconstruction pilots with Technology Select Sector cases in March and June 2024, the September 2024 rule transition, and the July 2023 Nasdaq special rebalance. These are source-availability tests, not a representative final sample. The September transition is one common policy change across affected indexes, not an independent experiment for each constituent.

## 5. Stage C: determine whether treatment is genuinely observable

For every event, distinguish four portfolio objects: the uncapped reference portfolio; the rule-assigned index portfolio; observed ETF holdings; and any creation/redemption basket. Do not equate them. Full ETF holdings are not automatically the portfolio an authorized participant must deliver, and post-rebalance fund holdings may reflect implementation choices.

Classify assignment evidence:

**A — Exact or defensibly reconstructed assignment.** An official historical pro forma/assignment file, or the complete verified inputs required to reproduce the contemporaneous rule. Record numerical precision and reconciliations.

**B — Independently documented event with incomplete dose.** An official record establishes binding or gives selected weights, but the full vector, precision, or reference inputs remain incomplete.

**C — Screening proxy only.** Holdings snapshots or approximate market capitalization suggest a cap but cannot identify exact assignment.

**U — Unknown or inaccessible.** Evidence is insufficient; never recode this as nonbinding.

Only class A supports an exact-dose analysis. Class B can establish event existence and sometimes a narrower event-level design; explain its limits. Class C may guide where to look next, not supply a confirmed running variable or instrument.

Where complete data exist, put old and new portfolios on the same valuation date. For example, with corporate-action-consistent quantities,

\[
\Delta w^{reb}_{i,e}=w^{new}_{i,e}(p_e^*)-w^{old}_{i,e}(p_e^*).
\]

Separately define the cap distortion at that reference state,

\[
d^{cap}_{i,e}=w^{rule}_{i,e}(p_e^*)-w^{uncapped}_{i,e}(p_e^*).
\]

These are different objects: the first measures a rebalance change; the second a cap-induced level difference. Neither automatically isolates a pure policy effect. Decompose membership changes, float/share updates, corporate actions, and rule changes where feasible. For the September methodology change, replay old and new rules on identical inputs as an accounting comparison, not a counterfactual equilibrium.

Do not identify rule-induced changes by subtracting weights from differently dated snapshots. Do not interpolate holdings across a cap event, treat CRSP total market capitalization as exact provider float-adjusted capitalization, or use post-event prices to backfill pre-event assignment inputs. Return-drift projections are screening exercises only unless fixed quantities and all intervening actions are verified.

Implement rule replay and reconciliation only where inputs justify it. Unit tests should check weight conservation, issuer aggregation, regime-specific ordering, precision/rounding, and reconciliation at the correct valuation date. For a complete common-support vector, report signed doses, issuer HHI before/after, and one-way weight turnover. Incomplete vectors must not silently be renormalized into a purported full-index result.

If reference inputs are uncertain, assess whether defensible uncertainty ranges change binding status, rank ordering, or dose sign. Do not invent narrow float-factor bounds merely to clear the gate. Distinguish “no access to exact inputs” from “no economically meaningful assignments exist.”

## 6. Stage D: test usable support, not just row counts

Extend beyond the pilots only when the reconstruction pathway works or a clearly bounded narrower event design is possible. Produce a complete status ledger for the chosen period, including unresolved rows and all exclusions.

Report events and dose distributions by index family, rule regime, calendar quarter, and issuer. Separate single-company caps, aggregate caps, secondary checks, and changes of methodology. Show how much support remains after omitting the largest episode, dominant issuer, technology sector, and September 2024 transition. Repeated appearances of the same companies are not independent draws of treatment.

For an RD-like design, identify the actual assignment boundary and inspect observations on both sides. Preserve rank or multidimensional assignment where required. Assess sensitivity to input precision, bandwidth, market-cap drift, discrete support, provider discretion, and anticipation. Predictability of an announced rule is not itself proof of invalidity; unpredictability is not proof of exogeneity.

Use pre-announcement daily data for size, prior relative returns, volatility, market exposure, and available liquidity/activity characteristics. These can reveal imbalance and concentration of treatment support; they cannot certify a common-news transmission mechanism. Use only fields actually present and avoid conditioning on post-treatment liquidity when discussing a total effect.

For the most promising feasible design, write down the proposed treatment/exposure design matrix before using outcome results. Examine variation remaining after the intended fixed effects and controls, matrix rank, collinearity, and dominance by dates or issuers. A coefficient absorbed by fixed effects has no identifying support.

A transparent support diagnostic may use residualized dose information shares:

\[
\ell_k=\widetilde d_k^2/\sum_j\widetilde d_j^2,
\qquad N^{info}=1/\sum_k\ell_k^2.
\]

Define rows, weighting, and residualization; also aggregate information shares by event date, regime, and issuer. This is a concentration-of-design-information diagnostic, not an independent-observation count or a power calculation. Report absolute dose range alongside it. If the denominator is zero, report no support rather than an arbitrary score.

Do not impose inherited cutoffs such as “40 events” or a fixed leverage percentage as universal scientific laws. Explain whether the actual support justifies the proposed estimand and comparison, and what inferential assumptions remain.

## 7. Stage E: intersect assignments with common-news opportunities

Build a verified calendar of scheduled FOMC statement dates from official Federal Reserve records and historical materials, recording package differences, projections, and press conferences. Treat phases of one meeting as dependent. Use the USMPD only for event metadata and availability screening at this stage; factor construction is not a prerequisite for counting support.

**[S4] Federal Reserve calendars and historical materials:**

```text
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
https://www.federalreserve.gov/monetarypolicy/fomc_historical.htm
```

**[S5] San Francisco Fed USMPD:**

```text
https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/
```

For each intervention, record the input reference date, earliest documented public announcement, pro forma availability, implementation close, effective open, secondary adjustment, and next intervention. Unknown times remain unknown. Avoid treating reference dates as public information dates.

Tabulate the nearest eligible pre/post statements and their distances from each stage. As descriptive support checks, also report statement counts within 20-, 40-, and 60-trading-day bands, explicitly marking bands that overlap anticipation, subsequent reweightings, or other interventions. Do not select a band based on returns or require all three to pass.

Count unique FOMC meetings, intervention dates, basket assignments, and reusable comparisons separately. Construct an overlap map showing shared stocks, common rebalance dates, and common news dates. Multiple sectors responding to the same statement do not supply multiple independent macro shocks. Reusing a statement across intervention windows does not create new information.

The essential result is whether repeated weight assignments intersect with usable before/after common-information observations. Many quarterly rebalances can still supply very little usable FOMC support.

## 8. Preserve the intended economic test and its limits

For the strongest candidate, specify how a future outcome would be measured on a residual portfolio whose membership and aggregation rule are fixed independently of treatment outcomes. Prefer pre-announcement-defined constituent-level outcomes or fixed-initial-quantity, corporate-action-adjusted residual portfolios. Distinguish fixed quantities from constant weights. Do not let post-treatment quote availability or survival silently select the residual set.

Excluding the focal stock removes its direct arithmetic contribution, but not changes in the other constituents' weights or common exposures. The same stock used as a signal for two baskets does not automatically cancel signal-precision effects when target loadings or residual noise differ. A positive forecast-gain difference would still require validation against common-news and measurement explanations.

Treat changes in funds' rebalancing demand and liquidity as possible components of an intervention's total effect. Do not claim they have been ruled out merely because a result is announcement-specific. Controls exposed through shared stocks may be affected; spillover bias is not necessarily attenuation.

Choose at most one preferred identification route after inspecting assignment support. State its treatment, counterfactual comparison, required assumptions, assignment/inference units, and strongest falsification. If only an intervention-specific reduced-form association is supportable, say so. Do not describe a same-stock comparison or a published threshold as a completed identification argument.

## 9. Explicitly close Questions 2 and 3 at the appropriate level

For Question 2, mathematical counterexamples and simulations can expose invalid statistics. Existing daily returns may inform daily covariance or exposure inputs, but they do not calibrate intraday latency, quote noise, direct-response speeds, or cross-market transmission. Do not create pseudo-ticks from daily prices and report them as an empirical validation. Passing a chosen simulation does not prove identification against every observationally equivalent mechanism.

For Question 3, classify the required future outcomes individually. The documented archive alone does not support intraday residual-adjustment paths, ETF–cash or ETF–futures quote disagreement, cross-market clocks, or their empirically calibrated event-level variance. Do not substitute daily returns for those outcomes or scale daily variance by time to claim an intraday MDE. Daily MIDAS cannot supply the missing path.

A stock–ETF-only pilot may avoid a CME dependency if its scientific claim is explicitly narrowed; it would not answer a futures-inclusive question. Exact index assignment history remains a separate requirement from market quotes. SEC N-PORT, daily ETF creation flows, and CPI/NFP consensus are not prerequisites for this FOMC-based assignment audit merely because they were gaps in the original P1/Refraction projects.

## 10. Outputs and decision rules

Return a concise decision memo, approximately 2,000–3,000 words, plus reproducible code, logs, and compact machine-readable tables. Produce at minimum:

```text
RUN_README.md
local_data_catalog.csv
fund_identifier_and_coverage_audit.csv
source_and_rule_registry.csv
rebalance_event_ledger.csv
assignment_doses_and_evidence.csv
assignment_and_fomc_support.csv
comparison_and_interference_audit.csv
remaining_input_gaps.csv
FINAL_DECISION.md
src/                 # executable code actually used, with configuration and tests
logs/                # commands, retrievals, tests, and execution status
```

Use one evidence key consistently across tables. Every reported quantity must trace to a source and computation. Missing or blocked tables may contain a documented status, never fabricated observations. Include only a few decision-relevant figures where helpful: event/evidence coverage, assignment support, and intervention–FOMC overlap.

End with separate conclusions for observable treatment, comparison credibility, independent support, and future outcome measurability. Choose one final recommendation:

**PROCEED TO A TARGETED MEASUREMENT PILOT:** The audit establishes a defensible intervention sample and comparison worth testing. State the smallest missing assignment/quote-data package, securities, dates, sessions, identifiers, and fields. Do not purchase it or imply that measurement, power, novelty, or publication have already passed.

**REVISE / RESOLVE A SPECIFIC INPUT GAP:** Institutional variation is promising but the assignment vector, historical inputs, comparison, or common-news support remains unresolved. Identify the precise next retrieval or design change and why it could alter the decision.

**STOP THIS REWEIGHTING DESIGN:** The audited economic or statistical support does not justify the intended claim. Do not use this label merely because your execution environment lacked access. State what failed and do not rescue the project by searching for significant daily outcomes.

The deliverable must distinguish audited facts, proxy-based indications, maintained assumptions, unexecuted tasks, and genuine design failures. Success is an evidence-based decision about the next research investment—not a positive coefficient, a long plan, or a large number of files.
