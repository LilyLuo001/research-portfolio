# Final export and figure static QA

## Material bug

`write_private_ad_parquet()` does not export the coded `explicit_new_graduate` outcome used by Decision 14 and `entry_conditioned_duties()`. It exports only the combined `entry_core_including_conditional`, the conditionality-restricted combined indicator, internship, and junior/entry label. Consequently, the new explicit-new-graduate-only Q2 sensitivity cannot be reconstructed or checked from `AD_LEVEL_MEASURES.parquet`, even though the aggregate comparison and Figure 2 use it. Add an ad-level field derived from `entry_outcomes.explicit_new_graduate` (and preferably the paired `explicit_no_experience` component for transparent decomposition of the broad indicator).

No other material issue was found in the bounded scope: the Q2 aggregation retains broad, unconditional-only, and explicit-new-graduate-only definitions; uses all technology groups for the headline rows; preserves unknown membership separately; applies the same `w3=1/pi3` estimator and variance path; and limits duties to advertised-worker current duties. Both renderers select unique fields present in their bound aggregate CSVs and describe the waiver limitation truthfully. The wrapper CLI keys and paths match the analysis and renderer interfaces. `pi12` and `nested_design_weight` nulls are preserved in the Parquet export, while main estimates remain based only on `pi3`.

## Root repair

Added separate private `entry_explicit_new_graduate` and `entry_explicit_no_experience` columns directly from the existing validated outcomes. This closes the identified reconstruction gap without changing labels, estimators, or sample. Final cloud analysis/Parquet production remains pending.
