import importlib.util
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memo" / "validate_w1_readiness.py"
SPEC = importlib.util.spec_from_file_location("validate_w1_readiness", MODULE_PATH)
assert SPEC and SPEC.loader
READINESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READINESS)


def test_w1_draft_is_structurally_coherent():
    report = READINESS.audit()
    assert report["structural_errors"] == []


def test_w1_draft_remains_fail_closed_before_pi_signature():
    report = READINESS.audit()
    assert report["blockers"]
    assert report["open_decisions"] == list(range(1, 18))
    assert report["pending_event_locators"]
