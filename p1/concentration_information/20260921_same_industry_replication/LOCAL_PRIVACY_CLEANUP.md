# Publication boundary cleanup

Three task-generated local diagnostic copies contained date-coded block labels. They were never intended as public artifacts and were removed before Git staging after parent independently verified identical SCC copies by SHA-256. This is not a claim that the files were never temporarily local.

SCC stage root:
`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/derived/p1_concentration_information/20260921_same_industry_replication`

- Local `AUTHORITATIVE_SUPPORT_GATE.json` removed; SCC root copy retained, hash `aef51d91cb7b3b3e093cbbbcd522c58a83cb7af8e343464cf6fd151db6a94d05`.
- Local root and `metadata/` copies of `DESIGN_MATRIX_DIAGNOSTICS.json` removed; SCC `metadata/` copy retained, hash `ecdb91e55f6c8c05c73bb4042d2bc1dd15d6fce82b7f6023900190345c36484d`.

These local deletions remove duplicates, not the SCC evidence. The full private gate remains available to the SCC-only guarded runner. `.gitignore` prevents accidental future staging of these filenames or bulk private data. Public readers use `SUPPORT_GATE_SUMMARY.json` and the immutable pre-outcome hashes.

The original SCC estimation receipt is separately preserved; its local publication version redacts date-coded leave-one-block keys without changing estimates. The execution receipt records original-versus-public hashes. No response rows or raw returns were added to Git.
