"""Regression tests for the W3 DWA coverage bound.

The bug these pin was found on the SCC against the real O*NET 26.1 release and
would have produced a confident false negative rather than an error: a
delimiter sniffed from a byte sample picks comma on Occupation Data.txt,
because its prose Description column carries more commas than the sample has
tabs. The header then folds into a single column whose name still contains
every substring the lookups search for, so the lookups "succeed", every
occupation title becomes the whole row, no GDPval label matches, and the
script reports coverage 0.0.

A false 0.0 here would have killed the DWA approach -- the one the literature
supports -- on a parsing mistake.
"""

import importlib.util
import pathlib
import zipfile

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "mapping" / "dwa_coverage_bound.py"
SPEC = importlib.util.spec_from_file_location("dwa_bound", PATH)
assert SPEC and SPEC.loader
BOUND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUND)


# Occupation Data.txt's real shape: tab-delimited, with a comma-heavy prose
# Description column. Commas outnumber tabs, which is what fooled the sniffer.
PROSE = ("Plan, direct, or coordinate activities, including budgeting, "
         "staffing, scheduling, and reporting, across teams, sites, and units.")
OCCUPATION_TABLE = (
    "O*NET-SOC Code\tTitle\tDescription\n"
    f"15-1252.00\tSoftware Developers\t{PROSE}\n"
    f"29-1141.00\tRegistered Nurses\t{PROSE}\n"
)


def test_delimiter_comes_from_the_header_not_a_byte_sample():
    rows = BOUND._read_delimited("Occupation Data.txt", OCCUPATION_TABLE.encode())
    assert list(rows[0]) == ["O*NET-SOC Code", "Title", "Description"]
    assert rows[0]["Title"] == "Software Developers"


def test_a_folded_header_is_refused_rather_than_parsed():
    """If a delimiter mistake ever slips through, fail loudly instead."""
    folded = '"O*NET-SOC Code\tTitle",Description\n"15-1252.00\tDev",x\n'
    with pytest.raises(BOUND.LayoutError, match="did not split"):
        BOUND._read_delimited("mangled.txt", folded.encode())


def test_one_folded_column_cannot_satisfy_two_requirements():
    """The deeper fault: substring lookup let a single column match everything.

    This is what converted a parse error into a plausible wrong answer.
    """
    folded = ["o*net-soc code\ttitle\tdescription"]
    assert not BOUND._distinct_assignment(folded, ("o*net-soc code", "title"))

    proper = ["o*net-soc code", "title", "description"]
    assert BOUND._distinct_assignment(proper, ("o*net-soc code", "title"))


def test_distinct_assignment_backtracks():
    """A greedy first-match would fail this; the requirement is a matching."""
    columns = ["task id", "id"]
    assert BOUND._distinct_assignment(columns, ("task id", "id"))


def _release(tmp_path: pathlib.Path) -> pathlib.Path:
    zip_path = tmp_path / "onet.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("db/Occupation Data.txt", OCCUPATION_TABLE
                    + f"47-2111.00\tElectricians\t{PROSE}\n")
        zf.writestr("db/Task Statements.txt",
                    "O*NET-SOC Code\tTask ID\tTask\tTask Type\n"
                    "15-1252.00\t1\tWrite code\tCore\n"
                    "29-1141.00\t2\tChart care\tCore\n"
                    "47-2111.00\t3\tPull wire\tCore\n"
                    "47-2111.00\t4\tPrepare reports\tCore\n")
        zf.writestr("db/Tasks to DWAs.txt",
                    "O*NET-SOC Code\tTask ID\tDWA ID\tDWA Title\n"
                    "15-1252.00\t1\tD01\tWrite code\n"
                    "29-1141.00\t2\tD02\tChart\n"
                    "47-2111.00\t3\tD03\tPull\n"
                    "47-2111.00\t4\tD01\tWrite code\n")
    return zip_path


def test_end_to_end_reaches_a_task_through_a_shared_dwa(tmp_path):
    """The mechanism direct matching threw away.

    Electricians are not a GDPval occupation, but "Prepare reports" shares a
    DWA with a software-developer task, so it is reachable. 3 of 4 tasks.
    """
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    parquet = tmp_path / "gdpval.parquet"
    pd.DataFrame({
        "task_id": ["t1", "t2"],
        "sector": ["Information", "Health Care"],
        "occupation": ["Software Developers", "Registered Nurses"],
        "prompt": ["SENTINEL_TASK_TEXT_A", "SENTINEL_TASK_TEXT_B"],
    }).to_parquet(parquet)

    out = tmp_path / "receipt.json"
    assert BOUND.main([
        "--onet", str(_release(tmp_path)),
        "--gdpval-parquet", str(parquet),
        "--output", str(out),
    ]) == 0

    import json
    receipt = json.loads(out.read_text())
    assert receipt["coverage_bound"]["tasks_covered"] == 3
    assert receipt["coverage_bound"]["share_of_all_tasks"] == 0.75
    assert receipt["gdpval"]["unmatched_occupation_labels"] == []
    # counts and column names only; no task text may cross into the receipt
    serialised = json.dumps(receipt)
    assert "SENTINEL_TASK_TEXT" not in serialised
    assert receipt["gdpval"]["schema"] == ["task_id", "sector", "occupation", "prompt"]


def test_a_total_title_miss_is_refused_not_reported_as_zero(tmp_path):
    """Zero matches means a parse or vintage fault, never a coverage finding."""
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    parquet = tmp_path / "gdpval.parquet"
    pd.DataFrame({
        "task_id": ["t1"], "sector": ["X"],
        "occupation": ["Occupation That Does Not Exist"],
        "prompt": ["SENTINEL_TASK_TEXT_C"],
    }).to_parquet(parquet)

    out = tmp_path / "receipt.json"
    assert BOUND.main([
        "--onet", str(_release(tmp_path)),
        "--gdpval-parquet", str(parquet),
        "--output", str(out),
    ]) == 2
    assert not out.exists(), "a refused run must not write a receipt"
