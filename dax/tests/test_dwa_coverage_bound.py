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
import json
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


def test_reported_titles_table_cannot_win_over_occupation_data():
    """The real O*NET 26.1 fault, found on the SCC.

    Sample of Reported Titles.txt offers 'O*NET-SOC Code' and 'Reported Job
    Title'. Under substring matching those are two DISTINCT columns, one per
    requirement, so the injective check passes and archive order hands it the
    win. Its titles are colloquial incumbent-reported ones, so none of the 44
    canonical GDPval labels match and the run refuses.

    Exact column names separate them: Occupation Data has a column named
    exactly 'Title'.
    """

    tables = {
        "Sample of Reported Titles.txt": [
            {"O*NET-SOC Code": "15-1252.00", "Reported Job Title": "Coder",
             "Shown in My Next Move": "Y"},
        ],
        "Occupation Data.txt": [
            {"O*NET-SOC Code": "15-1252.00", "Title": "Software Developers",
             "Description": "x"},
        ],
    }
    name, rows, alternatives = BOUND._select(
        tables, required={"o*net-soc code", "title"})
    assert name == "Occupation Data.txt"
    assert alternatives == []
    assert rows[0]["Title"] == "Software Developers"


def test_task_ratings_cannot_stand_in_for_task_statements():
    """The third selection fault, found on the SCC.

    Task Ratings.txt carries O*NET-SOC Code and Task ID and no DWA ID, so it
    met every column requirement, and 'Task Ratings' sorts before 'Task
    Statements' -- the tie-break made the wrong pick deterministic. Its grain
    is task x scale x category, so Task ID repeats; the real universe table
    has one row per task. Grain is what separates them.
    """

    tables = {
        "Task Ratings.txt": [
            {"O*NET-SOC Code": "15-1252.00", "Task ID": "1", "Scale ID": "IM", "Category": "1"},
            {"O*NET-SOC Code": "15-1252.00", "Task ID": "1", "Scale ID": "FT", "Category": "2"},
        ],
        "Task Statements.txt": [
            {"O*NET-SOC Code": "15-1252.00", "Task ID": "1", "Task": "Write code"},
            {"O*NET-SOC Code": "15-1252.00", "Task ID": "2", "Task": "Review code"},
        ],
    }
    name, rows, alternatives = BOUND._select(
        tables, required={"o*net-soc code", "task id", "task"},
        forbidden={"dwa id"}, unique="task id")
    assert name == "Task Statements.txt"
    assert alternatives == []


def test_a_repeating_key_disqualifies_a_universe_table():
    repeating = {"x.txt": [{"Task ID": "1", "Task": "a"}, {"Task ID": "1", "Task": "b"}]}
    with pytest.raises(BOUND.LayoutError, match="one row per"):
        BOUND._select(repeating, required={"task id", "task"}, unique="task id")


def test_task_statements_and_tasks_to_dwas_are_not_confused():
    """Both carry O*NET-SOC Code and Task ID; the DWA id separates them."""
    tables = {
        "Task Statements.txt": [
            {"O*NET-SOC Code": "15-1252.00", "Task ID": "1", "Task": "x"},
        ],
        "Tasks to DWAs.txt": [
            {"O*NET-SOC Code": "15-1252.00", "Task ID": "1", "DWA ID": "D01"},
        ],
    }
    assert BOUND._select(tables, required={"task id", "dwa id"})[0] == "Tasks to DWAs.txt"
    tables["Task Statements.txt"][0]["Task"] = "x"
    assert BOUND._select(
        tables, required={"o*net-soc code", "task id", "task"},
        forbidden={"dwa id"}, unique="task id")[0] == "Task Statements.txt"


def test_selection_is_deterministic_not_archive_order():
    """Ties break on sorted name, never on the order the zip happens to list."""
    a = [{"O*NET-SOC Code": "1", "Title": "A"}]
    b = [{"O*NET-SOC Code": "2", "Title": "B"}]
    forward = BOUND._select({"zzz.txt": a, "aaa.txt": b}, required={"o*net-soc code", "title"})
    reverse = BOUND._select({"aaa.txt": b, "zzz.txt": a}, required={"o*net-soc code", "title"})
    assert forward[0] == reverse[0] == "aaa.txt"
    assert forward[2] == ["zzz.txt"]


def test_no_matching_table_is_refused():
    with pytest.raises(BOUND.LayoutError, match="no table has exactly"):
        BOUND._select({"x.txt": [{"unrelated": "1"}]}, required={"o*net-soc code", "title"})


# The two tests that lived here exercised _distinct_assignment, an injective
# substring-to-column matcher used when tables were selected by substring.
# Exact-name selection (_select) replaced it and is strictly stronger, and the
# folded-header case it guarded is now refused at parse time -- see
# test_a_folded_header_is_refused_rather_than_parsed. Removed rather than left
# testing a function that no longer exists.


def _release(tmp_path: pathlib.Path) -> pathlib.Path:
    zip_path = tmp_path / "onet.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        # the decoy that beat Occupation Data under substring matching
        zf.writestr("db/Sample of Reported Titles.txt",
                    "O*NET-SOC Code\tReported Job Title\tShown in My Next Move\n"
                    "15-1252.00\tCoder\tY\n29-1141.00\tFloor Nurse\tY\n")
        zf.writestr("db/Occupation Data.txt", OCCUPATION_TABLE
                    + f"47-2111.00\tElectricians\t{PROSE}\n")
        zf.writestr("db/Task Statements.txt",
                    "O*NET-SOC Code\tTask ID\tTask\tTask Type\n"
                    "15-1252.00\t1\tWrite code\tCore\n"
                    "29-1141.00\t2\tChart care\tCore\n"
                    "47-2111.00\t3\tPull wire\tCore\n"
                    "47-2111.00\t4\tPrepare reports\tCore\n")
        zf.writestr("db/Task Ratings.txt",
                    "O*NET-SOC Code\tTask ID\tScale ID\tCategory\tData Value\n"
                    "15-1252.00\t1\tIM\t1\t4.2\n15-1252.00\t1\tFT\t2\t3.1\n")
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

    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"onet": {"n_unique_task_ids": 4, "n_unique_onet_socs": 3}}))
    out = tmp_path / "receipt.json"
    assert BOUND.main([
        "--onet", str(_release(tmp_path)),
        "--gdpval-parquet", str(parquet),
        "--output", str(out), "--expect-audit", str(audit),
    ]) == 0

    receipt = json.loads(out.read_text())
    assert receipt["coverage_bound"]["tasks_covered"] == 3
    assert receipt["coverage_bound"]["share_of_all_tasks"] == 0.75
    assert receipt["gdpval"]["unmatched_occupation_labels"] == []
    used = receipt["sources"]["onet_tables_used"]
    assert used["occupations"] == "Occupation Data.txt"
    assert used["task_statements"] == "Task Statements.txt"
    assert used["task_to_dwa"] == "Tasks to DWAs.txt"
    # counts and column names only; no task text may cross into the receipt
    serialised = json.dumps(receipt)
    assert "SENTINEL_TASK_TEXT" not in serialised
    assert receipt["gdpval"]["schema"] == ["task_id", "sector", "occupation", "prompt"]


def test_a_universe_that_misses_the_pinned_counts_is_refused(tmp_path):
    """A share computed on the wrong denominator is not a finding.

    Three rounds of selection faults each produced a plausible number on a
    wrong universe. The repo already pins what the universe must be, so
    reconcile against it rather than trusting selection.
    """

    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    parquet = tmp_path / "gdpval.parquet"
    pd.DataFrame({"task_id": ["t1"], "sector": ["X"],
                  "occupation": ["Software Developers"],
                  "prompt": ["SENTINEL_TASK_TEXT_D"]}).to_parquet(parquet)
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"onet": {"n_unique_task_ids": 19259,
                                          "n_unique_onet_socs": 923}}))
    out = tmp_path / "receipt.json"
    assert BOUND.main([
        "--onet", str(_release(tmp_path)),
        "--gdpval-parquet", str(parquet),
        "--output", str(out), "--expect-audit", str(audit),
    ]) == 2
    assert not out.exists()


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
