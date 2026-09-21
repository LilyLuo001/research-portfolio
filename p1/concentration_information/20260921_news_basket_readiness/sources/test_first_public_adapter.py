import csv
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import first_public_adapter as adapter
FIELDS = ["event_id", "url_hash", "publisher_or_issuer", "published_time_status", "first_public_status", "interval_precision", "missing_reason"]
IDS = ["P1-2023-08-01", "P1-2023-06-02", "P1-2023-08-03", "P1-2023-01-01", "P1-2023-02-02", "P1-2023-01-03"]

def write_view(path, rows, fields=FIELDS):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

def rows():
    return [{"event_id": ident, "url_hash": adapter.SOURCE_BINDINGS[ident][1], "publisher_or_issuer": adapter.SOURCE_BINDINGS[ident][0], "published_time_status": "ABSENT", "first_public_status": "UNKNOWN_SOURCE_VIEW_UNAVAILABLE", "interval_precision": "UNKNOWN", "missing_reason": "NO_HISTORICAL_PROVENANCE_VIEW"} for ident in IDS]

def run(path):
    return subprocess.run([sys.executable, str(HERE / "first_public_adapter.py"), str(path)], capture_output=True, text=True)

def test_accepts_exact_private_view(tmp_path):
    path = tmp_path / "view.csv"; write_view(path, rows())
    result = run(path)
    assert result.returncode == 0
    assert adapter.SOURCE_LIST_SHA256 in result.stdout

def test_rejects_extra_prohibited_column_before_rows(tmp_path):
    path = tmp_path / "view.csv"; write_view(path, rows(), FIELDS + ["EPS"])
    assert run(path).returncode != 0

def test_rejects_duplicate_event_id(tmp_path):
    data = rows(); data[-1]["event_id"] = data[0]["event_id"]
    path = tmp_path / "view.csv"; write_view(path, data)
    assert run(path).returncode != 0

@pytest.mark.parametrize("field", ["url_hash", "publisher_or_issuer"])
def test_rejects_event_source_binding_swap(tmp_path, field):
    data = rows(); data[0][field] = data[1][field]
    path = tmp_path / "view.csv"; write_view(path, data)
    assert run(path).returncode != 0

def test_rejects_duplicate_allowlisted_header(tmp_path):
    path = tmp_path / "view.csv"; write_view(path, rows(), FIELDS[:-1] + ["missing_reason", "missing_reason"])
    assert run(path).returncode != 0

def test_rejects_ragged_extra_and_missing_cells(tmp_path):
    path = tmp_path / "extra.csv"; path.write_text(",".join(FIELDS) + "\n" + ",".join(rows()[0][x] for x in FIELDS) + ",LEAK\n")
    assert run(path).returncode != 0
    path = tmp_path / "missing.csv"; path.write_text(",".join(FIELDS) + "\n" + ",".join(rows()[0][x] for x in FIELDS[:-1]) + "\n")
    assert run(path).returncode != 0

def test_rejects_contradictory_certification(tmp_path):
    data = rows(); data[0].update(first_public_status="FIRST_PUBLIC_CERTIFIED", missing_reason="NONE")
    path = tmp_path / "view.csv"; write_view(path, data)
    assert run(path).returncode != 0
