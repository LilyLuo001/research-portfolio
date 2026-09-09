# E05/E08 PDF layout and draft-delivery audit

Date: 2026-09-09
Reviewer: execution agent (not independent)

## Result

`PASS_DRAFT_PDF_LAYOUT`; overall V3 status remains `RUN_UNVALIDATED`.

The five current draft PDFs were rebuilt from the settled editable TeX sources
with Tectonic 0.17.0. Each retained log passed
`paper/scripts/check_latex_log.sh`: there are no LaTeX errors, unresolved
references or citations, or overfull boxes. The five-file SHA-256 manifest
also verifies against the rebuilt PDFs.

## Rendered inspection

Every page was rasterized at 144 dpi with Poppler and inspected in contact
sheets: 25 manuscript pages, 49 appendix pages, 10 response pages, 6 diagnosis
pages, and 36 source-diff pages. Dense and newly added manuscript/appendix
exhibits were also inspected individually, including the family-support,
direct-tail, stock-accounting, precision, simulation, BCC/ACS, architecture,
and task-weight tables. The inspection found no clipped text or tables, black
render boxes, blank pages, unreadably compressed tables, or figures interrupting
the conclusion.

| Artifact | Pages | SHA-256 |
|---|---:|---|
| `paper/build/YAX_REVISED_MANUSCRIPT.pdf` | 25 | `971f725b963b201f5b5df22d97b15938799a5f44bc60eb01447b5e8b31bab72c` |
| `paper/build/YAX_FOCUSED_ONLINE_APPENDIX.pdf` | 49 | `6c70bc26ca471e5457494429a612337f268a4fe77c80c29c480fccd15682ea65` |
| `paper/build/YAX_REFEREE_RESPONSE.pdf` | 10 | `050adcebd7a6716b5947bb82f7fab1207e09f7b2b63ec3056d714b844eafab66` |
| `paper/build/YAX_REVISION_DIAGNOSIS.pdf` | 6 | `25f542379316582951ef751deeaff92688c4f99ad23d87a64af968b424ad4b9f` |
| `paper/build/YAX_SOURCE_DIFF.pdf` | 36 | `c2fe1af251bcad316cd04803af793a13f1cc24a3341256d7c23e592d93f6eab2` |

The PDF metadata carries the comparison-centered manuscript and appendix
titles. Text extraction confirms that the old question-form title is absent.
The TeX driver still contains explicit author-affiliation and email
placeholders; those are intentionally not invented.

## Build contract

`paper/scripts/build_substantive_revision_tectonic.sh` regenerates the unified
source diff from baseline commit `6b8d85e`, excluding the generated diff itself
to avoid recursive growth; builds each document with a fresh auxiliary state;
runs the log check; and writes the five-file SHA-256 manifest. The style file
uses the pdfTeX glyph-mapping primitive only under pdfTeX, allowing the same
source to compile under XeTeX/Tectonic while retaining native Unicode mapping.

## Remaining limits

This audit establishes the current files' buildability and layout, not final
scientific completeness. E08 remains a draft delivery because E10 has no
bounded sanitized public export, G02 has not established exhaustive source-
request extraction, F07 lacks an authorized `EARNWEEK2` extract, B02 lacks
exact public BCC membership, and E12 requires author-supplied metadata. Any
later scientific or author edit requires rebuilding, rehashing, and repeating
this visual audit.
