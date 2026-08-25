"""The weight every occupation-level exposure number is built on.

DAX_om is a wage-bill-weighted share of occupation tasks. These weights are
that weighting. If they are wrong, every exposure number is wrong by exactly
that factor and nothing downstream would show it -- which is why the builder
refuses far more than it repairs.

Fixtures reproduce the layout the 2026-08-24 input inventory measured: FT as
seven percentage rows per (occupation, task) summing to 100, IM and RT as one
row each, tab-delimited, in a zip.
"""
import hashlib
import importlib.util
import io
import json
import pathlib
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_onet_task_weights", ROOT / "w2" / "build_onet_task_weights.py")
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)

RATING_COLS = ["O*NET-SOC Code", "Task ID", "Scale ID", "Category",
               "Data Value", "N", "Standard Error", "Lower CI Bound",
               "Upper CI Bound", "Recommend Suppress", "Date", "Domain Source"]
STATEMENT_COLS = ["O*NET-SOC Code", "Task ID", "Task", "Task Type",
                  "Incumbents Responding", "Date", "Domain Source"]


def _row(cols, **kw):
    return "\t".join(str(kw.get(c, "")) for c in cols)


def rating_rows(soc, task, importance, freq_pcts, suppress="N", date="07/2021"):
    """Seven FT band rows plus one IM and one RT, as O*NET publishes them."""
    out = []
    for cat, pct in zip(range(1, 8), freq_pcts):
        out.append(_row(RATING_COLS, **{
            "O*NET-SOC Code": soc, "Task ID": task, "Scale ID": "FT",
            "Category": cat, "Data Value": pct,
            "Recommend Suppress": suppress, "Date": date}))
    out.append(_row(RATING_COLS, **{
        "O*NET-SOC Code": soc, "Task ID": task, "Scale ID": "IM",
        "Category": "", "Data Value": importance,
        "Recommend Suppress": suppress, "Date": date}))
    out.append(_row(RATING_COLS, **{
        "O*NET-SOC Code": soc, "Task ID": task, "Scale ID": "RT",
        "Category": "", "Data Value": 90.0,
        "Recommend Suppress": suppress, "Date": date}))
    return out


DAILY = [0, 0, 0, 0, 100, 0, 0]        # frequency_score 5.0
YEARLY = [100, 0, 0, 0, 0, 0, 0]       # frequency_score 1.0


def make_archive(tmp_path, ratings, statements=None, name="db_26_1_text.zip"):
    statements = statements or []
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("db_26_1_text/Task Ratings.txt",
                   "\t".join(RATING_COLS) + "\n" + "\n".join(ratings) + "\n")
        z.writestr("db_26_1_text/Task Statements.txt",
                   "\t".join(STATEMENT_COLS) + "\n" + "\n".join(statements) + "\n")
    return path


def run(tmp_path, archive, extra=None):
    out = tmp_path / "weights.parquet"
    code = B.main(["--archive", str(archive),
                   "--expect-sha", B.sha256(archive),
                   "--output", str(out)] + (extra or []))
    return code, out


def two_task_archive(tmp_path):
    return make_archive(tmp_path,
                        rating_rows("11-1011.00", "1", 4.0, DAILY)
                        + rating_rows("11-1011.00", "2", 2.0, YEARLY))


# --- the definition itself ------------------------------------------------

def test_the_primary_weight_is_importance_times_frequency_score(tmp_path):
    """Hand-computed: 4.0*5.0 = 20 and 2.0*1.0 = 2, so shares are 20/22 and 2/22."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = run(tmp_path, two_task_archive(tmp_path))
    assert code == 0
    df = pd.read_parquet(out).set_index("task_id")
    assert df.loc["1", "task_weight_share"] == pytest.approx(20 / 22)
    assert df.loc["2", "task_weight_share"] == pytest.approx(2 / 22)
    assert df.loc["1", "frequency_score"] == pytest.approx(5.0)


def test_the_two_variants_are_built_and_differ_from_the_primary(tmp_path):
    """W2-D4. Frozen before anyone looks, so they must actually be present."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = run(tmp_path, two_task_archive(tmp_path))
    df = pd.read_parquet(out).set_index("task_id")
    assert df.loc["1", "importance_only_share"] == pytest.approx(4 / 6)
    assert df.loc["1", "equal_weight_share"] == pytest.approx(0.5)
    assert df.loc["1", "importance_only_share"] != pytest.approx(
        df.loc["1", "task_weight_share"])


def test_shares_sum_to_one_within_every_occupation(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    archive = make_archive(
        tmp_path,
        rating_rows("11-1011.00", "1", 4.0, DAILY)
        + rating_rows("11-1011.00", "2", 2.0, YEARLY)
        + rating_rows("29-1141.00", "3", 3.0, [0, 0, 50, 50, 0, 0, 0]))
    code, out = run(tmp_path, archive)
    df = pd.read_parquet(out)
    for column in ("task_weight_share", "importance_only_share",
                   "equal_weight_share"):
        sums = df.groupby("onet_soc")[column].sum()
        assert all(abs(v - 1.0) < 1e-9 for v in sums), f"{column}: {dict(sums)}"


def test_normalisation_is_within_occupation_not_across(tmp_path):
    """An across-occupation normalisation would make every DAX_om wrong."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    archive = make_archive(
        tmp_path,
        rating_rows("11-1011.00", "1", 4.0, DAILY)
        + rating_rows("29-1141.00", "2", 1.0, YEARLY))
    code, out = run(tmp_path, archive)
    df = pd.read_parquet(out)
    # Each occupation has one task, so each share is exactly 1.0 despite very
    # different raw weights (20 versus 1).
    assert list(df["task_weight_share"]) == [1.0, 1.0]


# --- refusals -------------------------------------------------------------

def test_a_wrong_archive_sha_is_refused(tmp_path):
    archive = two_task_archive(tmp_path)
    out = tmp_path / "w.parquet"
    code = B.main(["--archive", str(archive), "--expect-sha", "0" * 64,
                   "--output", str(out)])
    assert code == 2
    assert not out.exists()


def test_a_suppressed_pair_is_dropped_whole(tmp_path):
    """Suppression is published per rating row; keeping half a pair would
    build a weight out of records O*NET says not to publish."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    archive = make_archive(
        tmp_path,
        rating_rows("11-1011.00", "1", 4.0, DAILY)
        + rating_rows("11-1011.00", "2", 2.0, YEARLY, suppress="Y"))
    code, out = run(tmp_path, archive)
    df = pd.read_parquet(out)
    assert list(df["task_id"]) == ["1"]
    assert df.loc[0, "task_weight_share"] == pytest.approx(1.0)
    receipt = json.loads(out.with_suffix(".receipt.json").read_text())
    assert receipt["counts"]["dropped_recommend_suppress"] == 1


def test_incomplete_frequency_bands_are_dropped_not_renormalised(tmp_path):
    """Renormalising over a partial distribution invents a frequency profile."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    partial = [r for r in rating_rows("11-1011.00", "2", 2.0, YEARLY)
               if "\tFT\t7\t" not in r]
    archive = make_archive(
        tmp_path, rating_rows("11-1011.00", "1", 4.0, DAILY) + partial)
    code, out = run(tmp_path, archive)
    assert code == 0
    receipt = json.loads(out.with_suffix(".receipt.json").read_text())
    assert receipt["counts"]["dropped_incomplete_frequency_bands"] == 1


def test_frequency_bands_that_do_not_sum_to_100_are_refused(tmp_path):
    """The inventory measured every pair within 0.05 of 100. A pair at 60
    means this archive is not the one that was inventoried."""
    archive = make_archive(tmp_path,
                           rating_rows("11-1011.00", "1", 4.0,
                                       [60, 0, 0, 0, 0, 0, 0]))
    out = tmp_path / "w.parquet"
    code = B.main(["--archive", str(archive), "--expect-sha", B.sha256(archive),
                   "--output", str(out)])
    assert code == 2
    assert not out.exists()


def test_duplicate_rating_rows_are_refused(tmp_path):
    """A repeated grain would double-count into every weight."""
    rows = rating_rows("11-1011.00", "1", 4.0, DAILY)
    archive = make_archive(tmp_path, rows + [rows[0]])
    out = tmp_path / "w.parquet"
    code = B.main(["--archive", str(archive), "--expect-sha", B.sha256(archive),
                   "--output", str(out)])
    assert code == 2


def test_an_ambiguous_member_name_is_refused(tmp_path):
    """Two members ending in the same suffix: read one and the other is
    silently ignored -- the fault that put a constant column in the DWA bound."""
    path = tmp_path / "db.zip"
    body = ("\t".join(RATING_COLS) + "\n"
            + "\n".join(rating_rows("11-1011.00", "1", 4.0, DAILY)) + "\n")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("a/Task Ratings.txt", body)
        z.writestr("b/Task Ratings.txt", body)
        z.writestr("a/Task Statements.txt", "\t".join(STATEMENT_COLS) + "\n")
    out = tmp_path / "w.parquet"
    code = B.main(["--archive", str(path), "--expect-sha", B.sha256(path),
                   "--output", str(out)])
    assert code == 2


# --- the reconciliation that W2-D1 requires --------------------------------

def test_reconciliation_passes_against_a_matching_reference(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    ref = tmp_path / "onet_timeshares.csv"
    ref.write_text("onet_soc,task_id,task_time_share\n"
                   f"11-1011.00,1,{20/22!r}\n11-1011.00,2,{2/22!r}\n")
    code, out = run(tmp_path, two_task_archive(tmp_path),
                    ["--reconcile-against", str(ref)])
    assert code == 0
    receipt = json.loads(out.with_suffix(".receipt.json").read_text())
    assert receipt["reconciliation"]["status"] == "RECONCILED"


def test_a_wider_reference_scope_is_a_fact_not_a_failure(tmp_path):
    """The SCC finding. onet_timeshares.csv spans 19,259 task statements while
    only 17,879 are rated; the wage-join's 15,274 is a third quantity again.

    The first version of this reconciler refused on that asymmetry, which
    asked the operator to invent a suppression rule to explain a difference
    between artifacts that needs no explaining.
    """
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    ref = tmp_path / "onet_timeshares.csv"
    ref.write_text("onet_soc,task_id,task_time_share\n"
                   f"11-1011.00,1,{20/22!r}\n11-1011.00,2,{2/22!r}\n"
                   "11-1011.00,9,\n"          # unrated: blank share
                   "29-1141.00,8,0\n")        # suppressed: zero share
    code, out = run(tmp_path, two_task_archive(tmp_path),
                    ["--reconcile-against", str(ref)])
    assert code == 0
    rec = json.loads(out.with_suffix(".receipt.json").read_text())["reconciliation"]
    assert rec["status"] == "RECONCILED"
    assert rec["reference_rows_blank_or_zero"] == 2
    assert rec["reference_blank_tasks_absent_here"] == 2
    assert rec["shared_tasks_compared"] == 2


def test_dropping_a_task_the_reference_weighted_is_refused(tmp_path):
    """A positive-share task with no row here is a scope change in the
    identified set, not a difference between artifacts."""
    ref = tmp_path / "ref.csv"
    ref.write_text("onet_soc,task_id,task_time_share\n"
                   f"11-1011.00,1,{20/22!r}\n11-1011.00,2,{2/22!r}\n"
                   "11-1011.00,3,0.5\n")
    out = tmp_path / "w.parquet"
    archive = two_task_archive(tmp_path)
    code = B.main(["--archive", str(archive), "--expect-sha", B.sha256(archive),
                   "--output", str(out), "--reconcile-against", str(ref)])
    assert code == 2
    assert not out.exists()


def test_inventing_a_task_the_reference_lacks_is_refused(tmp_path):
    ref = tmp_path / "ref.csv"
    ref.write_text("onet_soc,task_id,task_time_share\n"
                   f"11-1011.00,1,{20/22!r}\n")
    out = tmp_path / "w.parquet"
    archive = two_task_archive(tmp_path)
    code = B.main(["--archive", str(archive), "--expect-sha", B.sha256(archive),
                   "--output", str(out), "--reconcile-against", str(ref)])
    assert code == 2


def test_reconciled_implies_every_positive_reference_task_was_compared(tmp_path):
    """RECONCILED must never come back from comparing whichever rows overlapped.

    An earlier draft added a minimum-overlap floor for this. It was
    unreachable: the positive-missing refusal already fires whenever the
    reference carries a positive-share task the builder lacks, so by the time
    a run reaches the verdict the overlap is necessarily complete. The floor
    was removed rather than left in as a guard that cannot fire, and the
    property it was meant to express is asserted here instead.
    """
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    ref = tmp_path / "onet_timeshares.csv"
    ref.write_text("onet_soc,task_id,task_time_share\n"
                   f"11-1011.00,1,{20/22!r}\n11-1011.00,2,{2/22!r}\n"
                   "11-1011.00,9,\n")
    code, out = run(tmp_path, two_task_archive(tmp_path),
                    ["--reconcile-against", str(ref)])
    assert code == 0
    rec = json.loads(out.with_suffix(".receipt.json").read_text())["reconciliation"]
    assert rec["shared_tasks_compared"] == rec["reference_rows_with_positive_share"]
    assert rec["overlap_fraction_of_reference_positive"] == 1.0


def test_a_diverged_definition_is_refused_not_warned(tmp_path):
    """The one outcome W2-D1 exists to prevent, and it must stop the build:
    a divergence here is invisible in every downstream number."""
    ref = tmp_path / "onet_timeshares.csv"
    ref.write_text("onet_soc,task_id,task_time_share\n"
                   "11-1011.00,1,0.5\n11-1011.00,2,0.5\n")
    out = tmp_path / "w.parquet"
    archive = two_task_archive(tmp_path)
    code = B.main(["--archive", str(archive), "--expect-sha", B.sha256(archive),
                   "--output", str(out), "--reconcile-against", str(ref)])
    assert code == 2
    assert not out.exists()


# --- what the receipt must carry ------------------------------------------

def test_the_receipt_refuses_the_time_share_name(tmp_path):
    """W2-D2. The single artifact the wage-bill weighting rests on must not
    claim to measure time, in a paper whose contribution is measurement honesty."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    code, out = run(tmp_path, two_task_archive(tmp_path))
    receipt = json.loads(out.with_suffix(".receipt.json").read_text())
    assert "not_a_time_share" in receipt
    assert receipt["output"]["share_column"] == "task_weight_share"
    assert "task_time_share" not in receipt["output"]["columns"]


def test_the_receipt_carries_the_known_defect_and_its_fix_path(tmp_path):
    """W2-D3. A defect recorded nowhere is a defect that gets rediscovered."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    code, out = run(tmp_path, two_task_archive(tmp_path))
    receipt = json.loads(out.with_suffix(".receipt.json").read_text())
    defect = receipt["known_defect"]
    assert defect["id"] == "W2-D3"
    assert "ordinal" in defect["what"]
    assert defect["fix_path"]


def test_the_receipt_carries_the_vintage_year_counts(tmp_path):
    """W2-D5. The caveat must be statable from data, not from memory."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    code, out = run(tmp_path, two_task_archive(tmp_path))
    receipt = json.loads(out.with_suffix(".receipt.json").read_text())
    assert receipt["vintage_caveat"]["rating_row_year_counts"] == {"2021": 18}


def test_the_contract_and_the_builder_agree_on_the_filename():
    """A contract naming one file while the builder writes another is a W2
    stage that can never pass, and nothing would say why."""
    import yaml
    contract = yaml.safe_load(
        (ROOT.parent / "ops" / "contracts" / "dax_built_backbone.yaml").read_text())
    required = contract["required_files"]
    assert "onet_task_weights.parquet" in required, required
    assert "onet_timeshares.parquet" not in required, (
        "W2-D2 renamed this; the old name asserts a measured time share that "
        "O*NET does not publish")
    assert B.main.__module__  # builder default writes the same name
    import inspect
    src = inspect.getsource(B.main)
    assert "onet_task_weights.parquet" in src
