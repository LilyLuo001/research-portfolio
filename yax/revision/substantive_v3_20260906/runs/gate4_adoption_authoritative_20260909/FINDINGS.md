# Focused RPS occupation-adoption extension

Status: **PASS_RECOMPUTED_FOCUSED_ADOPTION_EXTENSION**.

The exact-code merge retains 121 nonsuppressed detailed occupations from the
468-occupation frozen YAX support.  All five exposure quintiles and 20 SOC
major families are represented; each of those families has at least two
matched occupations.  Among the remaining YAX occupations, 318 have a
suppressed or missing RPS rate and 29 have no code in the released RPS table.

With one observation per occupation, the Pearson correlation between the
frozen beta exposure score and the pooled RPS adoption rate is 0.503631, the
Spearman correlation is 0.493741, and the OLS slope is 0.493023.  Mean adoption
is 0.263343 in Q1 and 0.530280 in Q5, a Q5-minus-Q1 difference of 0.266936.
The quintile profile is not monotone: Q4 has the highest mean, 0.575197.

After removing SOC-major-family means, 0.262215 of the unweighted exposure sum
of squares remains and the residualized adoption-on-exposure slope is 0.301958.
Weighting by the workbook's pooled respondent count gives a Pearson
correlation of 0.646527, a Q5-minus-Q1 difference of 0.332784, a within-family
exposure sum-of-squares share of 0.191472, and a residualized slope of 0.464531.
The respondent count is not treated as a survey or inverse-variance weight.

The workbook pools August 2025, November 2025, February 2026, and May 2026 and
does not provide detailed-cell standard errors or replicate weights.  The
results therefore have no p-values or confidence intervals.  They document a
positive descriptive alignment between a capability-based occupation score
and later self-reported use.  They do not measure adoption timing, explain the
CPS coefficient, or identify an effect of adoption on employment.
