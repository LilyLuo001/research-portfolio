"""Contract-conformance tests at the P1 -> refraction boundary.

The existing suite builds every fixture the way assert_panel.py expects, so 42
green tests coexisted with a battery that raised KeyError on the real P1 file
(QUALITY-REVIEW-2026-08-19.md, R-1/R-5). These tests build the convexp frame the
way P1's FROZEN CONTRACT declares it — primary key [permno, wave_id] per
ops/contracts/conv_exposure.yaml — so a drift back to the imagined schema fails
here rather than on the first real run.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from refraction.pipeline.assert_panel import (  # noqa: E402
    _read_p1_convexp, a10_convexp_frozen, assert_p1_join_key_usable)

CONTRACT = ROOT / "ops" / "contracts" / "conv_exposure.yaml"


def _p1_frame(permno="10001", wave="W002", conv_exp=0.02):
    """A ConvExp frame in P1's frozen shape — note `wave_id`, not `wave`."""
    return pd.DataFrame({"permno": [permno], "wave_id": [wave],
                         "conv_exp": [conv_exp], "effective_date": ["2021-06-11"]})


def _panel(permno="10001", wave="W002", convexp=0.02):
    return pd.DataFrame({"permno": [permno], "wave": [wave], "ConvExp": [convexp]})


def test_contract_still_keys_on_wave_id():
    """If P1 ever re-keys conv_exposure, this test is the early warning."""
    c = yaml.safe_load(CONTRACT.read_text())
    assert c["primary_key"] == ["permno", "wave_id"], (
        "P1's frozen contract changed; refraction's read adapter must follow")


def test_a10_accepts_the_frozen_p1_schema():
    """The regression: this raised KeyError('wave') before the adapter existed."""
    out = a10_convexp_frozen(_panel(), _p1_frame())
    assert out["pass"], out["detail"]


def test_a10_still_accepts_an_already_normalised_frame():
    already = _p1_frame().rename(columns={"wave_id": "wave"})
    assert a10_convexp_frozen(_panel(), already)["pass"]


def test_a10_detects_a_real_mismatch_through_the_adapter():
    """The adapter must not paper over a genuine value disagreement."""
    out = a10_convexp_frozen(_panel(convexp=0.05), _p1_frame(conv_exp=0.02))
    assert not out["pass"]
    assert "mismatch" in out["detail"]


def test_a10_flags_nonzero_exposure_absent_from_the_frozen_file():
    out = a10_convexp_frozen(_panel(permno="99999", convexp=0.02), _p1_frame())
    assert not out["pass"]
    assert "absent" in out["detail"]


def test_adapter_rejects_a_frame_with_neither_spelling():
    bad = pd.DataFrame({"permno": ["1"], "cusip": ["x"], "conv_exp": [0.1]})
    with pytest.raises(KeyError, match="neither 'wave' nor 'wave_id'"):
        _read_p1_convexp(bad)


def test_blank_permno_is_refused_not_silently_merged():
    """P1's free-EDGAR path leaves permno as '' — empty string, not NaN, so a
    notna() check passes on a wholly unusable join key."""
    blank = _p1_frame(permno="")
    assert blank["permno"].notna().all(), "the trap: notna() reports it as present"
    with pytest.raises(ValueError, match="every one of .* blank"):
        assert_p1_join_key_usable(blank)


def test_usable_permno_passes_the_join_key_check():
    assert_p1_join_key_usable(_p1_frame())        # must not raise


def test_partially_blank_permno_is_allowed_through():
    """Only a wholly blank key is fatal; a partial crosswalk is a coverage
    question for A10/A11, not a reason to refuse the whole run."""
    part = pd.concat([_p1_frame(permno="10001"), _p1_frame(permno="")],
                     ignore_index=True)
    assert_p1_join_key_usable(part)               # must not raise
