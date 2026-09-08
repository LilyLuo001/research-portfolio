from __future__ import annotations

import hashlib
from pathlib import Path


PAPER = Path(__file__).resolve().parents[1]


def test_tectonic_builder_is_executable_and_produces_all_five_outputs() -> None:
    script = PAPER / "scripts" / "build_substantive_revision_tectonic.sh"
    source = script.read_text(encoding="utf-8")
    assert script.stat().st_mode & 0o111
    for stem in (
        "YAX_REVISED_MANUSCRIPT",
        "YAX_FOCUSED_ONLINE_APPENDIX",
        "YAX_REFEREE_RESPONSE",
        "YAX_REVISION_DIAGNOSIS",
        "YAX_SOURCE_DIFF",
    ):
        assert stem in source
        assert (PAPER / "build" / f"{stem}.pdf").is_file()
    assert "check_latex_log.sh" in source


def test_generated_source_diff_is_excluded_from_its_own_input() -> None:
    source = (
        PAPER / "scripts" / "build_substantive_revision_tectonic.sh"
    ).read_text(encoding="utf-8")
    assert "':(exclude)revision/source_diff.txt'" in source
    assert "sed -E 's/[[:space:]]+$//'" in source


def test_pdf_hash_manifest_matches_current_outputs() -> None:
    manifest = PAPER / "build" / "SUBSTANTIVE_REVISION_PDF_SHA256.txt"
    rows = [line.split() for line in manifest.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 5
    for expected, relative in rows:
        path = PAPER / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_style_keeps_pdftex_only_glyph_primitive_guarded_and_avoids_tiny_floats() -> None:
    source = (PAPER / "styles" / "michaillat-paper.sty").read_text(encoding="utf-8")
    assert "\\ifPDFTeX" in source
    assert "\\pdfgentounicode=1" in source
    assert "\\renewcommand{\\floatpagefraction}{0.45}" in source
