from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "yax_gate3_design_variables", HERE / "verify_design_variables.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def valid_headers():
    base = sorted(AUDIT.REQUIRED | {"AGE", "EMPSTAT"})
    return {"wide": base + ["ASECWT"], "march_repair": base}


def test_authorized_headers_support_only_sampling_sensitivity():
    result = AUDIT.audit_headers(valid_headers(), dict(AUDIT.EXPECTED))
    assert result["status"] == "PASS_AUTHORIZED_EXTRACT_HEADER_AUDIT"
    assert result["public_PSU_or_stratum_variables"] == []
    assert result["replicate_weight_variables"] == []
    assert result["interpretation"]["design_based_inference"] is False
    assert result["interpretation"]["SERIAL"].startswith("unique only within")


@pytest.mark.parametrize("added", ["PSU", "STRATA", "REPWTP1", "REPWT1"])
def test_unexpected_design_variable_forces_reconsideration(added):
    headers = valid_headers()
    headers["wide"] = headers["wide"] + [added]
    with pytest.raises(RuntimeError, match="interpretation must be revisited"):
        AUDIT.audit_headers(headers, dict(AUDIT.EXPECTED))


def test_missing_link_or_weight_variable_fails_closed():
    headers = valid_headers()
    headers["march_repair"].remove("CPSID")
    with pytest.raises(RuntimeError, match="lacks required"):
        AUDIT.audit_headers(headers, dict(AUDIT.EXPECTED))


def test_hash_change_fails_closed():
    hashes = dict(AUDIT.EXPECTED)
    hashes["wide"] = "0" * 64
    with pytest.raises(RuntimeError, match="hash differs"):
        AUDIT.audit_headers(valid_headers(), hashes)
