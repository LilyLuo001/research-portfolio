import gzip
import importlib.util
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "w2" / "split_ipums_preperiod_outcome_blind.py"
SPEC = importlib.util.spec_from_file_location("split_preperiod", MODULE_PATH)
assert SPEC and SPEC.loader
SPLIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SPLIT)
ACTUAL_RECEIPT = (
    ROOT / "memo" / "power_calcs" / "ipums_extract9_preperiod_split_receipt_v1.json"
)


def test_prefix_parser_stops_before_protected_suffix():
    raw = b'2023,"000,serial",1,POST_OUTCOME_SENTINEL,9999\n'
    prefix = SPLIT.parse_prefix(raw, 3)
    assert prefix == [b"2023", b"000,serial", b"1"]
    assert all(b"SENTINEL" not in value for value in prefix)


def test_splitter_writes_only_preperiod_rows_and_safe_receipt(tmp_path, capsys):
    sentinel = "POST_OUTCOME_SENTINEL_MUST_NOT_ESCAPE"
    source = tmp_path / "wide.csv.gz"
    output = tmp_path / "pre.csv.gz"
    receipt_path = tmp_path / "receipt.json"
    content = (
        "YEAR,SERIAL,MONTH,EMPSTAT,OCC2010,WTFINL\n"
        "2017,1,1,10,100,2.5\n"
        "2022,2,11,12,200,3.5\n"
        f"2022,3,12,{sentinel},{sentinel},{sentinel}\n"
        f"2026,4,7,{sentinel},{sentinel},{sentinel}\n"
    ).encode()
    with gzip.open(source, "wb") as handle:
        handle.write(content)

    receipt = SPLIT.split_preperiod(source, output, receipt_path)
    printed = capsys.readouterr().out
    with gzip.open(output, "rt") as handle:
        delivered = handle.read()
    receipt_text = receipt_path.read_text(encoding="utf-8")

    assert sentinel not in delivered
    assert sentinel not in printed
    assert sentinel not in receipt_text
    assert "2017,1,1,10,100,2.5" in delivered
    assert "2022,2,11,12,200,3.5" in delivered
    assert receipt["rows_written_preperiod"] == 2
    assert receipt["rows_rejected_postperiod"] == 2
    assert receipt["protected_fields_decoded_for_rejected_rows"] is False
    assert receipt["postperiod_rows_written"] is False
    assert receipt["postperiod_outcomes_printed"] is False
    assert json.loads(receipt_text)["status"] == (
        "PASS_OUTCOME_BLIND_PREPERIOD_SPLIT"
    )


def test_extract9_split_receipt_preserves_seal_and_accounts_for_every_row():
    receipt = json.loads(ACTUAL_RECEIPT.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS_OUTCOME_BLIND_PREPERIOD_SPLIT"
    assert receipt["rows_total"] == 9262480
    assert receipt["rows_written_preperiod"] == 6188956
    assert receipt["rows_rejected_postperiod"] == 3073524
    assert receipt["rows_written_preperiod"] + receipt["rows_rejected_postperiod"] == receipt["rows_total"]
    assert receipt["protected_fields_decoded_for_rejected_rows"] is False
    assert receipt["postperiod_rows_written"] is False
    assert receipt["postperiod_outcomes_printed"] is False
    assert len(receipt["preperiod_month_counts"]) == 71
    assert len(receipt["rejected_month_counts"]) == 43
