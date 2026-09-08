# E04 precision-consolidation audit

Status: complete editorial integration, subject to final PDF rendering.

The online appendix now contains one consolidated table for the principal
normal-theory MDE80 diagnostics. The table distinguishes coefficient targets
from paired coefficient differences and states each scale. It covers the core
pooled and family-month comparisons, direct and continuous within-family
support, computer-use and remotability conditioning, industry and education
heterogeneity, the architecture range, and all six primary flow margins.

The table defines MDE80 once as `(1.96 + 0.84) * SE` and states that it is a
normal-theory resolution diagnostic rather than a wild-score critical value,
equivalence margin, or acceptance threshold. The source audit checks the
load-bearing rows against the existing result-backed tables and refuses the
build if the consolidated entries or interpretation boundary disappear.

Evidence:

- presentation: `paper/tables/r3_appendix_precision_summary.tex`
- manuscript integration: `paper/appendix/sections/r3_E_inference.tex`
- validation: `paper/scripts/audit_substantive_revision.py`

The source-level audit passes. Visual placement remains part of the final PDF
render review and is not claimed complete here.
