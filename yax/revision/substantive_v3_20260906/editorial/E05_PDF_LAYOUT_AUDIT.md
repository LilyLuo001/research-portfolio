# E05 PDF layout and draft-delivery audit

Date: 2026-09-08
Reviewer: execution agent (not independent)

## Result

`PASS_DRAFT_PDF_LAYOUT`; overall V3 status remains `RUN_UNVALIDATED`.

The five current draft PDFs were rebuilt from the editable TeX sources with
Tectonic 0.17.0. Each retained log passed `paper/scripts/check_latex_log.sh`:
there are no LaTeX errors, unresolved references or citations, or overfull
boxes. The source-level audit separately returned
`PASS_SUBSTANTIVE_R3_AUDIT` with 206 numerical checks and 405 hashed files.

## Rendered inspection

Every page was rasterized with Poppler and inspected in contact sheets. Dense
appendix table pages 9, 14, 20, and 26 were also inspected individually. The
inspection found no clipped text, clipped tables, black render boxes, blank
pages, or unreadably compressed tables. Raising `\floatpagefraction` from zero
to 0.45 removed the small isolated float pages in the earlier draft without
truncating any exhibit.

| Artifact | Pages | SHA-256 |
|---|---:|---|
| `paper/build/YAX_REVISED_MANUSCRIPT.pdf` | 19 | `246f331b02e37834549663edde86b1acadb77e827460e28976f833625995eb63` |
| `paper/build/YAX_FOCUSED_ONLINE_APPENDIX.pdf` | 29 | `d291939b0ed8053aa1e6c637ee5fa3b0b4dbc618b8db52793a6fb3d503c4159c` |
| `paper/build/YAX_REFEREE_RESPONSE.pdf` | 10 | `5c7cd6ac0765dec9ec1a424e0b4c661119632d79963182ba624001ebf638e019` |
| `paper/build/YAX_REVISION_DIAGNOSIS.pdf` | 4 | `97ef2d81ea93ffa37b9f6bc359c5de817f6a281376456d845d98993f77680967` |
| `paper/build/YAX_SOURCE_DIFF.pdf` | 23 | `aa5b5707eb716d94e0605feab8075ef6f1bc1db8fa3194cc419b87572b0aa237` |

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
scientific completeness. E05 still depends on unresolved S06/T02 validation.
E08 remains a draft delivery because downstream V3 empirical requirements and
the author-supplied affiliation/email are incomplete. Any later scientific or
author edit requires rebuilding, rehashing, and repeating this visual audit.
