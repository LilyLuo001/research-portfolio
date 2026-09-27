#!/usr/bin/env python3
import datetime as dt
import json
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRAME = runpy.run_path(str(ROOT / "prepare_evaluation_frame.py"))
FINAL = runpy.run_path(str(ROOT / "finalize_annotation_pack.py"))


def test_time_strata():
    f = FRAME["time_stratum"]
    assert f(dt.datetime(2015, 1, 1)) == "2015"
    assert f(dt.datetime(2017, 12, 31)) == "2016-17"
    assert f(dt.datetime(2019, 6, 1)) == "2018-19"
    assert f(dt.datetime(2022, 12, 31)) == "2020-22"
    assert f(dt.datetime(2023, 1, 1)) == "2023"
    assert f(dt.datetime(2024, 1, 1)) == "2024"
    assert f(dt.datetime(2025, 1, 1)) == "2025"
    assert f(dt.datetime(2026, 9, 6)) == "2026_partial"
    assert f(dt.datetime(2026, 9, 7)) is None
    assert f(dt.datetime(2014, 12, 31)) is None


def test_quota_conservation():
    cfg = json.loads((ROOT / "config_finalize_kunshan.json").read_text())
    assert sum(cfg["target_by_time"].values()) == 1000
    assert sum(cfg["supplemental_by_time"].values()) == 200
    assert sum(cfg["calibration_by_time"].values()) == 600
    assert all(cfg["calibration_by_time"][k] < cfg["target_by_time"][k] for k in cfg["target_by_time"])
    for period, total in cfg["target_by_time"].items():
        assert cfg["supplemental_by_time"][period] < total


def test_supplement_allocation():
    allocate = FINAL["allocate"]
    for n in (20, 24, 26, 32):
        got = allocate(n, ["predicted_complex", "predicted_candidate", "predicted_noncandidate"])
        assert sum(got.values()) == n
        assert all(x > 0 for x in got.values())


def test_codebook_contract_enums():
    codebook = json.loads((ROOT / "annotation_codebook.json").read_text())
    common = json.loads((ROOT.parent / "research_contract_v1/common_measurement.json").read_text())
    for key in ("presence", "strength", "experience_object", "technology_class", "technology_role",
                "task_family", "binding_status", "relation"):
        assert codebook[key] == common[key]
