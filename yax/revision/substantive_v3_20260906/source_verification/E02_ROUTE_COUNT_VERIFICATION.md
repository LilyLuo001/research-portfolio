# E02 route-count verification

Date verified: 2026-09-08
Requirement: E02

## Finding

The correct count is **6,188,956 route-expanded descendants**. The referee's
`36,188,956` is not a second result and must not be substituted into the
manuscript.

## Render evidence

I visually inspected the supplied current appendix rather than relying on PDF
text extraction. Printed page 3 ends with the sentence fragment “and creates”
and then the centered page footer `3`. Printed page 4 begins with
“6,188,956 route-expanded descendants.” A text extractor that concatenates the
page footer and the next page's first token can therefore produce the apparent
string `36,188,956`.

Supplied artifacts inspected:

- `AI_revision_V3/inputs/current_appendix.pdf`, SHA-256
  `017858f43a1acffc0371a32be3958a33c1ae7f1988b83b32dbc05139d39506e8`;
- `AI_revision_V3/inputs/inspection/appendix_p3.png`, SHA-256
  `bd26652fdb6d1475feaaa9f4e8fae40093072453758253d7ba13930c1ca6e9b5`;
- `AI_revision_V3/inputs/inspection/appendix_p4.png`, SHA-256
  `0be1ce21f6a871bfe9b2a2854b4b29798b842419bed83ee42a5acdc2284cf1a3`.

The package is retained outside the analysis repository at
`/Users/lilyluo/Documents/Codex/2026-08-25/her/work/AI_revision_V3_execution_20260906/AI_revision_V3/`.

## Calculation evidence

The rendering agrees with independent machine-readable artifacts:

- `yax/revision/substantive_r3_20260905/data_audit/results/EXECUTION_RECEIPT.json`
  records `routed_rows: 6188956` (SHA-256
  `de7511cbd63b1b2d97ebea39c93c79f425760b829ae32ed7acc4e234913d7935`);
- `yax/revision/substantive_r3_20260905/data_audit/results/SAMPLE_FLOW_CORRECTED.csv`
  records `fractional_routed_descendants,6188956` (SHA-256
  `6d5bb5971c0714c85265d7fee3452f34e50f1b17a30abf652a0876e8256a38ce`);
- the later unified sample-flow receipt independently records the same routed
  count (SHA-256
  `1cbf26c1d3d5fa56a7f0be2ff8c00ade9a9d6ef6afa49d8b93842b43eee450e1`).

This is a count of fractional route-expanded rows, not distinct respondents.
The response to the referee should explain the page-footer concatenation
politely, confirm that the source calculation was rechecked, and state that no
numerical correction to 36 million was made.
