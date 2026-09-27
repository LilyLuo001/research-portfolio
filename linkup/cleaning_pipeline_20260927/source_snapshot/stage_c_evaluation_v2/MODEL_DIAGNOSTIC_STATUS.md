# Model diagnostic status

The 1,000-record regional annotation frame is frozen: 600 calibration records
and 400 sealed-process records. The frame contains an 800-record probability
core and a separately marked 200-record prediction supplement drawn from 32
previously unused Kunshan-held shards. It is not a national or full-corpus
probability sample, and occupation coverage was not measured.

Job `123132130` produced the initial frame and then failed intentionally because
the 2020–22 pool had 157 eligible groups against a target of 160. Extension job
`123132322` completed the final frame. Observed overlap across the two splits was
zero for company-scrape identifier, exact normalized-text hash, and the
conservative masked-token signature. Parent/subsidiary/site harmonization and
semantic near-duplicate detection remain unverified.

Model review is diagnostic only. The calibration-only review is complete: the
primary model (`gpt-5.6-terra`) reviewed 32 records, and an independent model
family (`gpt-5.6-sol`) reviewed a fixed 8-record subset. Neither model accessed
the sealed-process records. No human labels are available, so the comparisons
are not accuracy estimates and do not establish semantic release.

Against primary model references, V5 education candidates had binary support on
31 records (19 TP, 4 FN, 0 FP, 8 TN; one unknown/conflict excluded). V5
experience candidates had binary support on 30 records (23 TP, 3 FN, 1 FP,
3 TN; one explicit-negative record and one unknown/conflict handled separately
by the protocol). On the fixed 8-record subset, the two models disagreed on zero
education-presence labels and one experience-presence label. These are small,
model-only calibration diagnostics.

Experience-object and technology-role totals count labeled evidence clauses,
not ads. The two models used different annotation granularity, the primary-32
and secondary-8 compositions are not directly comparable, and no matched-clause
agreement validation was performed. Coarse presence agreement therefore cannot
be used to infer that object extraction or object/requirement binding is ready.

Qualification presence remains an exploratory candidate measure. The observed
education false negatives (4 of 23 positive model references) and experience
false negatives/positive (3 of 26 positive model references, plus one false
positive) show that semantic cleaning is unfinished. The frozen V5 parser was
not changed in this round. The next useful review is targeted at experience
objects, technology roles, and binding errors rather than another full-corpus
parse.

Git contains the aggregate comparator, aggregate JSON/Markdown report, this
status, and the frozen code/contracts. Raw advertisements, row comparisons,
record-level selection metadata, annotations, hidden mappings, calibration
records, and sealed-process text remain outside Git.
