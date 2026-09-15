# P1 local outcome-blind design build

Build date: 2026-09-15. This is a bounded P1 metadata diagnostic. It is not a new plan, Gate 1 PASS, approval of a final sample, an effect estimate, or an ESS calculation. The accepted proposed contract remains SHA256 `00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f`.

## Measured attrition

The source tier universe has 4,191 stock-wave keys: 1,396 high, 1,398 low, and 1,397 middle. The high/low tail therefore contains 2,794 keys. The v1 eligibility snapshot represents 2,592 of those tail keys; 202 are absent before the 8 PRE/4 POST screen. Their retrieval/coverage representation is `UNKNOWN` and their absence must not be labeled no earnings or final ineligibility. The absent v1 keys are W002 high 59/low 73, W016 high 24/low 29, and W025 high 6/low 11.

Among the 2,592 represented v1 keys, 2,088 have 8 PRE/4 POST metadata support. The proposed overlap-clean screen retains 508. The all-12-events/minimum-two-analyst screen retains 895 as a separate branch from the 2,088 pool. Their intersection retains 182: W002 high 10/low 165, W016 high 2/low 1, and W025 high 2/low 2. W013 and W021 retain zero. The capped clean+all12 acquisition core contains 15, which is a selection cap rather than the full-pool ceiling.

The 71-unit acquisition union is reported separately because it expands across roster sources and is not the next attrition stage. All 71 rows remain `NOT_CERTIFIED`. Its 852 event associations comprise 568 PRE and 284 POST rows; 659/852 pass the event-level minimum-two-analyst metadata count. That flag does not certify SUE compatibility.

A separate v2 snapshot represents 4,186 of the 4,191 source-universe keys. Five are absent: W016 low 3 and W025 high 1/middle 1. Their retrieval/coverage representation is also `UNKNOWN`. Among represented v2 keys, 3,246 have 8 PRE/4 POST support. No v1 overlap or analyst flag was applied to this version, and it was never pooled with the 2,592/2,088 snapshot.

## Structural calendar support

The contract cell set first intersects release calendar quarters observed in both high and low tiers within each wave and regime. That common-H/L expansion contains 860 acquired-stock by wave/regime/quarter cells, of which 13 lack an observed event association. 4 one-tier-only wave/regime/quarter cells were excluded before any industry restriction and are reported separately. The broader all-quarter diagnostic contains 910 cells with 59 missing; it is not the contract cell set.

These are necessary calendar-support diagnostics only. The allowed event projection has no approved historical industry column, so the required industry-by-calendar-quarter-by-wave support and numeric rank remain unknown. No SUE or response values were read.

## Partial dependency graph

The graph contains 852 event-association nodes, 71 stock nodes, five wave nodes, and 417 observed release-date nodes. Its base partial components use only event-stock and event-release-date edges: 3 event components, with 828 event associations in the largest. The separately labeled wave-edge proxy has a component count of 1 and is not an inference rule. Calendar-quarter edges are relation-only and excluded from both algorithms. These topology counts are not ESS and do not validate an inference procedure.

The graph does not construct sponsor edges: sponsor identity is `UNKNOWN` and is not inferred from wave. The existing calendar metadata names a CRSP observed-session basis but does not record scientific approval, so all +1d response-date nodes remain explicitly `UNKNOWN`.

## Files

- `source_manifest.csv`: exact input hashes and allowed columns.
- `attrition_summary.csv` and `sequential_attrition_by_wave_tier.csv`: version-separated totals and per-wave/tier denominators.
- `snapshot_representation_gaps_by_wave_tier.csv`: exact counts absent before snapshot-specific support screens, labeled unknown.
- `event_level_analyst_eligibility.csv` and `event_analyst_eligibility_by_wave_tier_regime.csv`: 852-row metadata eligibility and grouped denominators.
- `structural_calendar_support_matrix.csv` and `structural_calendar_support_summary.csv`: common-H/L-quarter necessary support.
- `all_quarter_structural_calendar_support_matrix.csv` and `excluded_one_tier_quarters.csv`: broader diagnostic and quarters excluded from the contract cell set.
- `dependency_nodes.csv`, `dependency_edges.csv`, and `dependency_component_summary.csv`: partial observed graph and explicitly scoped topology counts.
- `actionable_missing_columns.csv`: exact missing inputs that block full design/rank construction.

## Scope controls

The build used explicit CSV `usecols` after header validation. It asserts v1 keys are a strict subset of the 2,794 source H/L tail, v2 keys are a strict subset of the 4,191 source universe, exact v1-support/overlap/intersection key equality, exact candidate analyst-flag alignment, the clean-plus-analyst conjunction, and uniqueness of the tier universe before joining. It did not read ownership/dose, liquidity, raw financial, EPS/forecast values, prices, returns, quote bodies, POST responses, or SUE. It made no SCC/network call, purchase, commit, or effect estimate. All snapshot labels remain provisional diagnostics.
