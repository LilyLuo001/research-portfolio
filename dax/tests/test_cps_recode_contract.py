import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "memo" / "power_calcs" / "cps_recode_contract_v1.json"
BUILDER_PATH = ROOT / "memo" / "power_calcs" / "build_cps_recode_contract.py"
SPEC = importlib.util.spec_from_file_location("build_cps_recode_contract", BUILDER_PATH)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILDER
SPEC.loader.exec_module(BUILDER)


def test_contract_is_metadata_only_and_pins_extract9_sources():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["sources"]["microdata_read"] is False
    assert contract["sources"]["ddi"]["sha256"] == (
        "5933bc48ed736a00fa70547ef503f571c6f1f9c03aef7d24ce511af3550fb319"
    )
    assert contract["sources"]["basic_codebook"]["sha256"] == (
        "1bf294152576efad9601491860f8238ee72d8291f939fb4ed467edff42815d45"
    )


def test_primary_recode_is_exact_and_does_not_assign_nonemployed_occupation():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["employment"]["employed_codes"] == [10, 12]
    assert contract["occupation"]["primary_variable"] == "OCC2010"
    assert contract["occupation"]["raw_variable_role"].endswith("never exposure merge")
    assert contract["occupation"]["missing_occ2010_codes"] == [9999]
    assert 9999 not in contract["occupation"]["valid_occ2010_codes"]
    assert 1020 in contract["occupation"]["valid_occ2010_codes"]


def test_class_worker_and_work_status_sensitivities_are_fail_closed():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["class_of_worker"]["primary_sample_restriction"] == "none"
    assert contract["class_of_worker"]["private_wage_salary_codes"] == [21, 22, 23]
    assert contract["class_of_worker"]["general_wage_salary_codes"] == [20]
    assert contract["class_of_worker"]["missing_unknown_codes"] == [99]
    assert contract["work_status"]["full_time_schedule_codes"] == [10, 11, 12, 13, 14, 15]
    assert contract["weight"]["valid_rule"] == "finite and strictly positive"


def test_asec_march_months_are_structural_gaps_never_asecwt_substitutes():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["structural_gaps"]["omit_months"] == [
        "2017-03", "2018-03", "2019-03", "2020-03", "2021-03"
    ]
    assert "never substitute ASECWT" in contract["structural_gaps"]["reason"]
