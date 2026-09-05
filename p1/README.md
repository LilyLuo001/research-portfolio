# P1 current entry point

Start with `docs/基金转换实验_博士研究计划.md`, then
`p1/strategic_pivot/POST_V3_RESEARCH_DECISION-2026-09-06.md`,
`p1/STATUS-2026-09-05.md`, and `p1/etf_weight_shape_gates/README.md`.

The 2026-09-06 post-V3 decision is the current research authority. Its verdict
is `NOT YET` on fund-level construction and `NO` on a full Gate 0/1 rewrite
now. No SCC run or regression is authorized. The only proposed path is first a
bounded novelty/estimand check and, only if that survives, a small
post-treatment-coefficient-free fund-flow bridge pilot under a separate, newly
frozen fund-flow specification.

The 2026-09-05 V3 data-contract checkpoint is the current execution authority.
All earlier ETF weight-shape Gate 0/1 outputs are invalidated, Gate 2 did not
run, and no full rerun is authorized. The targeted contract pilot passed, but
that is not a Gate result; the old full implementation remains fail-closed
before archive access. A contract-conformant full rewrite is not currently
authorized.

Current empirical inputs live in `p1/universe_v2/output/` and `p1/exposure/`.
The root files `events_merged.csv` and `conv_exposure_free.parquet`, plus the
older T1/T2 coverage/scenario outputs, are legacy reconciliation baselines. Do
not use their 172/96/389 counts as the current universe.

No headline outcome estimation is authorized from this state. The current
decision is in `p1/strategic_pivot/POST_V3_RESEARCH_DECISION-2026-09-06.md`;
the older `strategic_recommendation.md` is retained for audit only. The formal
ex-ante audit in `p1/viability/` classifies the original frozen stock design as
`C. NOT PRACTICALLY VIABLE UNDER THE CURRENT DESIGN`: observed continuous-dose
information has only 2.90 all-sponsor and 2.88 exclude-Dimensional effective
waves, and the clustered MDE is above the frozen 0.5-SD benchmark. Exposure
construction and outcome/regression work remain paused.

The narrower fund-level ETF-architecture project is now a `NOT YET` candidate,
not an authorized replacement: it must reconcile strategy-boundary net capital
with documented inherited assets and documented class transfers, leaving unresolved
sources explicitly unidentified. ETF share classes remain a separate validation
estimand. High-dose stock transmission remains secondary.
Refraction/FOMC is not authorized until an outcome-blind first stage passes.
The Fed/source row-list gap and unsigned economic-sponsor crosswalk remain
documented data issues, but closing them cannot by itself satisfy the measured
stock-level power deficit. The current archive contains no TAQ outcome data.
