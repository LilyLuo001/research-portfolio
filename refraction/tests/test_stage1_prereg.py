"""The Stage-1 pre-registration renderer.

The queue's REFR-R4-prereg note requires "zero model-generated digits": every number in the
document must be injected from frozen_config.yaml. These tests enforce that rather than
trusting it, and check that the document does not overstate its own status — it is a
prepared document, not a registration.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from refraction import build_stage1_prereg as b   # noqa: E402

CONFIG = yaml.safe_load((ROOT / "refraction" / "frozen_config.yaml").read_text())
DOC = ROOT / "refraction" / "STAGE1_PREREG.md"


@pytest.fixture(scope="module")
def body():
    return b.render(CONFIG)


def test_the_document_regenerates_identically_from_the_config(body):
    """It is a projection of the config, so it cannot drift from it."""
    assert DOC.exists(), "run refraction/build_stage1_prereg.py"
    assert DOC.read_text() == body


def test_every_number_in_the_document_traces_to_the_config(body):
    """The digits test. Each numeric literal must appear somewhere in frozen_config.yaml,
    so none can have been written from memory."""
    cfg_text = (ROOT / "refraction" / "frozen_config.yaml").read_text()
    cfg_numbers = set(re.findall(r"\d+(?:\.\d+)?", cfg_text))
    # headings are structural prose, not registered values — scan the content only
    content = "\n".join(l for l in body.splitlines() if not l.startswith("#"))
    structural = {"0", "1", "2", "3", "4", "5", "6", "7"}    # formula subscripts, "stage 1"
    doc_numbers = set(re.findall(r"\d+(?:\.\d+)?", content))
    orphans = {n for n in doc_numbers - cfg_numbers if n not in structural}
    assert not orphans, "numbers not traceable to the config: %s" % sorted(orphans)


def test_the_stage_one_contents_all_appear(body):
    """Whatever stage 1 claims to register must actually be in the document."""
    for item in ("cr_definition", "w_shrink_selection_algorithm", "decision_rules",
                 "gate_algorithms"):
        assert item in CONFIG["prereg"]["stage1"]["contents"], item
    for marker in ("CR_{f,t}", "midpoint_of_longest_feasible_run", "Gate-0 thresholds",
                   "INSUFFICIENT_IDENTIFYING_VARIATION", "equivalence margin",
                   "Invariants", "Lookahead"):
        assert marker in body, marker


def test_the_document_carries_the_frozen_grid_not_just_the_rule(body):
    spec = CONFIG["beta"]["w_shrink_grid_spec"]
    assert "refinement forbidden" in body or "refinement_after_sweep_forbidden" in body \
        or "Post-sweep refinement forbidden: yes" in body
    assert str(spec["n_points"]) in body
    for w in CONFIG["beta"]["w_shrink_sweep_grid"]:
        assert str(w) in body, w


def test_undecided_quantities_are_shown_as_undecided_not_omitted(body):
    """A null threshold that simply vanished from the document would read as settled."""
    assert CONFIG["beta"]["w_shrink"] is None
    assert CONFIG["network_exposure"]["first_stage_equivalence_margin"] is None
    assert body.count("**NOT SET** (stage 2)") >= 2


def test_the_document_does_not_claim_to_be_a_registration(tmp_path):
    out = tmp_path / "S1.md"
    assert b.main(["-o", str(out)]) == 0
    meta = json.loads((tmp_path / "S1.md.submission.json").read_text())
    assert meta["submitted"] is False
    assert meta["stage"] == 1
    assert "human_gate" in meta["submission_gate"]
    assert meta["sha256"] and meta["config_sha256"]


def test_the_prereg_guard_is_still_blocked_because_nothing_was_submitted():
    """Generating the document must not, by itself, unblock outcome access."""
    assert CONFIG["prereg"]["osf_timestamp"] is None
    assert CONFIG["prereg"]["stage1"]["timestamp"] is None
    r = subprocess.run([sys.executable, str(ROOT / "refraction" / "guards" / "prereg_guard.py"),
                        "check", str(ROOT / "refraction" / "frozen_config.yaml")],
                       capture_output=True, text=True)
    assert r.returncode == 1, "prereg_guard should still refuse post-outcome estimation"
