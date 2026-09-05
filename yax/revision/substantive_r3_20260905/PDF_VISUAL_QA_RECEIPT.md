# PDF visual-QA receipt

Recorded: 2026-09-06

## Build provenance

- Source commit: `120a07e98ef136e9286a06b5b673cac739056c5f`
- Clean SCC worktree: `<YAX_SCC_PROJECT_ROOT>/worktrees/paper_build_120a07e`
- SCC build job: `7472053`
- Scheduler result: `failed=0`, `exit_status=0`, wall clock 19 seconds, maximum virtual memory 183.277 MB
- Build command: `paper/scripts/scc_build_major_revision_pdfs.sh`
- Local transfer was verified against the SCC-generated SHA-256 manifest.

## Page-by-page inspection

Every page of every deliverable was rendered with Poppler at 110 dpi and inspected in ordered four-page contact sheets. Text was also extracted independently with `pdfplumber`. No clipped or overlapping text, broken table, missing figure, unreadable glyph, blank page, unresolved-reference marker, credential string, or private filesystem root was found.

| Deliverable | Pages | SHA-256 | Result |
|---|---:|---|---|
| `YAX_REVISED_MANUSCRIPT.pdf` | 21 | `dfd19a366777d5dfcd7bd867210e1f76d427113f88c01aa1b8d383a5dd5aa31d` | PASS |
| `YAX_FOCUSED_ONLINE_APPENDIX.pdf` | 29 | `017858f43a1acffc0371a32be3958a33c1ae7f1988b83b32dbc05139d39506e8` | PASS |
| `YAX_REFEREE_RESPONSE.pdf` | 9 | `2002db17738578dd82d0e2981a21002166dd161ba29b2b00aebd52ff75542599` | PASS |
| `YAX_REVISION_DIAGNOSIS.pdf` | 4 | `f65ff56abe4f79f998c314c39b47a305820bdae013fe0477b6e4a414d07ff5a8` | PASS |
| `YAX_SOURCE_DIFF.pdf` | 22 | `7b853c5aa538bfd4e78b526c0ef3afd9a95e80d2469552befe3b8bffaf3baa12` | PASS |

Total pages inspected: 85.

The `[AUTHOR TO COMPLETE]` fields remain intentionally visible because affiliation, email, acknowledgments, funding, conflicts, and journal-specific disclosures require author input. They are not build defects.

Status: `PASS_RENDERED_PDF_QA`
