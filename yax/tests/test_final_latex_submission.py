from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"


def words(path: Path) -> list[str]:
    return re.findall(r"\b[\w’'-]+\b", path.read_text(encoding="utf-8"))


def test_required_latex_source_tree_is_complete():
    required = [
        PAPER / "main" / "restat.tex",
        PAPER / "main" / "working.tex",
        PAPER / "appendix" / "appendix.tex",
        PAPER / "submission" / "cover_letter_restat.tex",
        PAPER / "bibliography" / "references.bib",
        PAPER / "Makefile",
    ]
    required += sorted((PAPER / "main" / "sections").glob("*.tex"))
    required += sorted((PAPER / "appendix" / "sections").glob("*.tex"))
    assert len(list((PAPER / "main" / "sections").glob("*.tex"))) == 10
    assert len(list((PAPER / "appendix" / "sections").glob("*.tex"))) == 12
    assert all(path.is_file() and path.stat().st_size for path in required)


def test_abstract_lengths_and_red_team_response():
    assert len(words(PAPER / "main" / "abstract_restat.tex")) <= 100
    assert 160 <= len(words(PAPER / "main" / "abstract_working.tex")) <= 190
    memo = (PAPER / "internal" / "YAX_RESTAT_DESK_REDTEAM.md").read_text(encoding="utf-8")
    response = memo.split("## Response (150 words)", 1)[1]
    assert len(re.findall(r"\b[\w’'-]+\b", response)) == 150


def test_journal_facing_text_has_no_internal_codes_or_machine_paths():
    files = list((PAPER / "main").rglob("*.tex")) + list((PAPER / "tables").glob("*.tex"))
    text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    prohibited = [
        "YAX", "V1.1", "Phase", "Gate", "LOCO-B2", "LOCO-G1",
        "G-PARTIAL", "AE-R1", "POWER-C3", "SUBMIT-S1", "HB-C",
        "SC-A", "SC-R1", "FLOW-M5", "/Users/", "/home/",
    ]
    for token in prohibited:
        assert token not in text


def test_bibliography_has_no_et_al_author_fields():
    bib = (PAPER / "bibliography" / "references.bib").read_text(encoding="utf-8")
    assert not re.search(r"author\s*=\s*\{[^}]*\bet\s+al\.", bib, flags=re.I)
    assert len(re.findall(r"^@", bib, flags=re.M)) >= 30


def test_makefile_exposes_required_targets():
    makefile = (PAPER / "Makefile").read_text(encoding="utf-8")
    for target in ("restat", "working", "appendix", "cover", "all", "clean"):
        assert re.search(rf"^{target}:", makefile, flags=re.M)
