import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from refraction.guards.prereg_guard import (  # noqa: E402
    LookaheadError, PreregError, assert_no_lookahead, assert_prereg_ok, prereg_status)

REPO_CONFIG = Path(__file__).resolve().parents[1] / "frozen_config.yaml"


def _write(tmp_path, **overrides):
    cfg = yaml.safe_load(REPO_CONFIG.read_text())
    for dotted, val in overrides.items():
        node = cfg
        *parents, leaf = dotted.split(".")
        for k in parents:
            node = node[k]
        node[leaf] = val
    p = tmp_path / "frozen_config.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return p


def test_repo_config_blocks_outcomes_now():
    """The committed config must block R6+ (nothing is registered yet)."""
    st = prereg_status(REPO_CONFIG)
    assert not st.ok
    with pytest.raises(PreregError):
        assert_prereg_ok(REPO_CONFIG)


def test_blocks_without_url(tmp_path):
    p = _write(tmp_path, **{"prereg.osf_timestamp": "2026-07-01T00:00:00Z",
                            "beta.w_shrink": 0.4})
    assert not prereg_status(p).ok  # osf_url still missing


def test_blocks_unfrozen_w_shrink(tmp_path):
    p = _write(tmp_path, **{"prereg.osf_timestamp": "2026-07-01T00:00:00Z",
                            "prereg.osf_url": "https://osf.io/xxxxx"})
    st = prereg_status(p)
    assert not st.ok and "w_shrink" in st.reason


def test_blocks_future_timestamp(tmp_path):
    p = _write(tmp_path, **{"prereg.osf_timestamp": "2026-07-01T00:00:00Z",
                            "prereg.osf_url": "https://osf.io/xxxxx",
                            "beta.w_shrink": 0.4})
    early = datetime(2026, 6, 30, tzinfo=timezone.utc)
    assert not prereg_status(p, now=early).ok


def test_rejects_unzoned_timestamp(tmp_path):
    p = _write(tmp_path, **{"prereg.osf_timestamp": "2026-07-01T00:00:00",
                            "prereg.osf_url": "https://osf.io/xxxxx",
                            "beta.w_shrink": 0.4})
    assert not prereg_status(p).ok


def test_passes_when_fully_frozen(tmp_path):
    p = _write(tmp_path, **{"prereg.osf_timestamp": "2026-07-01T00:00:00Z",
                            "prereg.osf_url": "https://osf.io/xxxxx",
                            "beta.w_shrink": 0.4})
    st = assert_prereg_ok(p, now=datetime(2026, 7, 2, tzinfo=timezone.utc))
    assert st.ok


def test_lookahead_boundary():
    assert_no_lookahead(date(2022, 12, 30), date(2023, 1, 2))  # strictly before: ok
    with pytest.raises(LookaheadError):
        assert_no_lookahead(date(2023, 1, 2), date(2023, 1, 2))  # equal = violation
    with pytest.raises(LookaheadError):
        assert_no_lookahead("2023-06-01", "2023-01-02", permno=1001, wave="W1")
