# Blind human-review pack protocol

Due October 5: a maximum 40-ad pack for review by the user or RA. Due October
7: locked human labels, comparison results, unresolved cases, and support
counts. This is separate from the heldout 400, which remains unopened.

Freeze eligible first-linkage-supported groups and all exclusion-set hashes first. Draw
32 core ads deterministically within complete-period and broad occupation
availability strata without using extractor predictions, candidate counts,
model judgments, effect estimates, or review outcomes. Up to eight additional
challenge ads may be drawn using prespecified frozen text-complexity or
candidate flags; report
them separately and do not treat them as probability-weighted prevalence data.

The initial reviewer file contains an anonymous ID, the original advertisement
text needed to judge the clauses, non-outcome sampling strata, and blank human
label fields defined in `reviewer_pack_schema.json`. It contains no parser or
enrichment prediction, model judgment, predicted evidence span, or aggregate
result. Only authorized reviewers receive text; Git and aggregate deliverables
receive no raw text or row-level private mapping.

Reviewers mark explicit evidence spans and may choose unknown or insufficient
text. Absence of a detected phrase is never automatically a negative label.
Where two reviewers are available, lock independent labels before comparison;
otherwise disclose single-reviewer status. Record adjudication separately and
retain unresolved cases. After lock, compare frozen extraction with human
labels and call the result model-versus-human. Models never count as human
reviewers.

The time label shown to reviewers is a first-observation cohort for snapshot
text. It does not assert that the supplied description was the historical text
at CREATED, and the review cannot validate a historical requirements panel.

If some or all assigned reviews have not been returned by October 7, report the
assigned, returned, duplicate-reviewed, adjudicated, and unresolved counts. Do
not fill missing human labels with model judgments.
