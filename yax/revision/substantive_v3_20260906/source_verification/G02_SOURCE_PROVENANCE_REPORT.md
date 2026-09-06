# G02 source-provenance report

Validation status: **PASS** for the provenance layer.

This is not a G02 completion certificate. It authenticates the source files, maps every unique source reference already present in the immutable seed, and cross-links those references to `ACCEPTANCE_CHECK_CROSSWALK.csv`. G02 still requires an exhaustive extraction of every numbered and unnumbered source request.

## Coverage

- Registered source documents: 6
- Unique source references in the seed: 76
- Resolved to authenticated text spans: 62
- Explicitly unresolved: 14
- Immutable seed SHA-256: `38de2d5b80e72c85f3dd06086a862cea63c521d511a5baacb7f6390f66eeeb59`
- Acceptance crosswalk SHA-256: `3598080b42a5063d04b196ba32485af00107fe064befbf1e468d0b1218752ac0`

For resolved locators, `span_sha256` hashes the exact source bytes for the inclusive physical line range, retaining original line endings.

## Unresolved or synthetic provenance

| source ref | reason |
|---|---|
| `A:minor front matter inherited` | synthetic_inherited_locator_not_present: The supplied A report contains front-matter metadata at lines 3-7 but no request labeled 'minor front matter inherited'; assigning those metadata lines to this requirement would invent a source request. |
| `C:1` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:2.1` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:2.2` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:3.1` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:3.2` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:3.3` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:3.4` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:4` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:4.1` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:4.2` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:4.3` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:5` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |
| `C:6` | numbered_locator_system_absent_from_supplied_summary: The supplied C file states that it is a non-verbatim working summary and has no section or paragraph marker matching this source_ref. Topical matching would not establish the requested provenance. |

The numbered `C:*` locators cannot be reconstructed from the supplied C file: that document identifies itself as a non-verbatim summary and contains no matching numbering. They are therefore preserved as unresolved rather than mapped by topic.

## Validation boundary

The machine checks authenticate documents and resolved spans, preserve unresolved provenance, confirm exact coverage of the seed's unique source references, confirm cross-links to the current acceptance-check crosswalk, and verify that the seed hash is unchanged. They do not determine whether the source prose has been exhaustively atomized or whether any scientific request has been completed.
