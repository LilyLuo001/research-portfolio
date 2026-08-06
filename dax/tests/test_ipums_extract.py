import importlib.util
import json
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memo" / "power_calcs" / "ipums_extract.py"
SPEC = importlib.util.spec_from_file_location("ipums_extract", MODULE_PATH)
assert SPEC and SPEC.loader
IPUMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IPUMS)
FROZEN_SPEC = ROOT / "memo" / "power_calcs" / "ipums_preperiod_extract_v1.json"


def test_frozen_spec_is_pre_event_only():
    spec = json.loads(FROZEN_SPEC.read_text(encoding="utf-8"))
    IPUMS.validate_spec(spec)
    assert len(spec["samples"]) == 16


def test_post_event_sample_is_rejected():
    spec = json.loads(FROZEN_SPEC.read_text(encoding="utf-8"))
    spec["samples"]["cps2023_03b"] = {}
    with pytest.raises(ValueError, match="post-event sample prohibited"):
        IPUMS.validate_spec(spec)


def test_missing_preperiod_month_is_rejected():
    spec = json.loads(FROZEN_SPEC.read_text(encoding="utf-8"))
    del spec["samples"]["cps2022_06s"]
    with pytest.raises(ValueError, match="exactly 2021-11 through 2023-02"):
        IPUMS.validate_spec(spec)
