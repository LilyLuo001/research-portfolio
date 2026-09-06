# LaTeX template provenance

- Upstream: `https://github.com/pmichaillat/latex-paper`
- Retrieved: 2026-09-05
- Upstream commit: `9235e6d01550da645cdc576481d483bbe9214def`
- License: MIT, copyright 2022-present Pascal Michaillat
- Vendored unchanged: `paper.sty`, `paper.bst`, `appendix.sty`, and `LICENSE.md`, renamed under `paper/styles/` to make provenance explicit.
- Excluded: upstream example prose, generated PDFs, auxiliary files, combined figure PDF, README examples, and upstream Git metadata.

The circulation build uses the vendored `michaillat-paper.sty` and bibliography style as its primary visual scaffold. The ReStat build uses a separate `restat-submission.sty` wrapper to implement 12-point Times-like type, double spacing, one-inch margins, page numbers, and review-oriented captions. Shared substantive sections, equations, tables, citations, and empirical claims are included from the same source tree in both modes. The vendored files are not edited; all project-specific and journal-specific changes live in separate style files.
