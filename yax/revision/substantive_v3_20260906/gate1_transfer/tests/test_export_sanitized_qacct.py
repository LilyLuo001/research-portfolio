from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / "export_sanitized_qacct.py"
LOADER = importlib.util.spec_from_file_location("yax_gate1_qacct_exporter", SCRIPT)
assert LOADER is not None and LOADER.loader is not None
EXPORTER = importlib.util.module_from_spec(LOADER)
sys.modules[LOADER.name] = EXPORTER
LOADER.loader.exec_module(EXPORTER)


def record(*, job: str = "7474618", task: str = "undefined") -> str:
    return f"""==============================================================
qname        econ
hostname     scc-gd4.scc.bu.edu
jobnumber    {job}
taskid       {task}
owner        synthetic
start_time   Sun Sep  6 06:39:26 2026
end_time     Sun Sep  6 06:40:01 2026
failed       0
exit_status  0
ru_wallclock 35
maxvmem      1.043G
"""


def test_exact_single_nonarray_record_is_sanitized_and_bound():
    value = EXPORTER.parse_exact_record(record(), "7474618")
    assert set(value) == EXPORTER.OUTPUT_FIELDS
    assert value["jobnumber"] == "7474618"
    assert value["start_time"] == "Sun Sep 06 06:39:26 2026"
    assert value["ru_wallclock"] == 35.0
    assert value["qacct_export_provenance"] == {
        "status": "RUNNER_RECORDED_BYTE_PINNED_CONSISTENCY",
        "role": "scheduler_accounting_export",
        "qacct_resolved_executable_sha256": EXPORTER.QACCT_SHA256,
        "qacct_version": EXPORTER.QACCT_VERSION,
        "exporter_code_sha256": EXPORTER.sha256_file(SCRIPT),
        "join_rule": "one_delimiter_one_record_exact_jobnumber_nonarray",
    }
    assert "/usr/" not in json.dumps(value)


@pytest.mark.parametrize(
    "payload,job,match",
    [
        (record(job="7474619"), "7474618", "exactly join"),
        (record(task="1"), "7474618", "array-task"),
        (record() + record(), "7474618", "one delimited record"),
        (record().replace("failed       0", "failed       nan"), "7474618", "integer"),
    ],
)
def test_ambiguous_mismatched_or_malformed_records_fail_closed(
    payload: str, job: str, match: str
):
    with pytest.raises(EXPORTER.QacctExportError, match=match):
        EXPORTER.parse_exact_record(payload, job)


def test_scheduler_file_publication_is_no_replace(tmp_path: Path):
    target = tmp_path / "cells.json"
    payload = b'{"jobnumber":"7474618"}\n'
    assert EXPORTER.publish_new_file(target, payload) == ()
    assert target.read_bytes() == payload
    with pytest.raises(EXPORTER.QacctExportError, match="already exists"):
        EXPORTER.publish_new_file(target, b"{}\n")
    assert target.read_bytes() == payload
