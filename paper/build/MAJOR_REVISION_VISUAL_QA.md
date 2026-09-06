# Major-revision PDF visual QA

Date: 2026-09-05

All pages were rendered with Poppler at 72 dpi and inspected in contact sheets.
Title pages and the principal results, composition, architecture-precision,
mobility, response, and diagnosis pages were re-rendered at 150 dpi and
inspected individually.  No clipping, overlap, blank page, unreadable table, or
missing figure was observed.  The SCC build logs contain no LaTeX errors,
undefined references, multiply defined labels, or overfull boxes.

| Artifact | Pages | SHA-256 | QA |
|---|---:|---|---|
| `YAX_WORKING_PAPER_MAJOR_REVISION.pdf` | 25 | `39315398c0bea4f87e055af537080627a976faa5cddc53963f4c5a4df26ba067` | PASS |
| `YAX_ONLINE_APPENDIX_MAJOR_REVISION.pdf` | 29 | `f5aed632c4f09b35c745371e1e4a8cc04a5a69e458927b97717b753172ff970a` | PASS |
| `YAX_REFEREE_RESPONSE_MAJOR_REVISION.pdf` | 8 | `184541a944ea4a9ea5c481e62ffdd7a82027a602c3cad23b77ba47c60077f723` | PASS |
| `YAX_REVISION_DIAGNOSIS_MAJOR_REVISION.pdf` | 3 | `2a565350c63c1d0501f66ad4cda8f293ddb22f588ef7984760a394fd5c77dae9` | PASS |

The manuscript and appendix PDFs came from the successful SCC batch build.
The response and diagnosis were rebuilt from the same synchronized source to
add PDF title/author metadata; their visual content was unchanged and their
final metadata and page counts were rechecked with `pdfinfo`.
