import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

MOD = Path(__file__).parents[1] / "code" / "sealed_support_and_conditional_power.py"
SPEC = importlib.util.spec_from_file_location("sealed", MOD)
sealed = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sealed
SPEC.loader.exec_module(sealed)


def test_direct_fit_equals_weighted_fwl_fixture():
    rng = np.random.default_rng(4)
    n = 80
    x0 = np.column_stack((np.ones(n), rng.normal(size=n), rng.normal(size=n)))
    z = np.column_stack((rng.normal(size=n), rng.normal(size=n)))
    w = rng.uniform(.2, 2.0, size=n)
    y = x0 @ np.array([[1.], [-.4], [.2]]) + z @ np.array([[.7], [-.3]]) + rng.normal(size=(n, 1))
    beta, fit = sealed.weighted_fwl(y, z, x0, w)
    q = np.sqrt(w)[:, None]
    direct = np.linalg.lstsq(q * np.column_stack((x0, z)), q * y, rcond=None)[0][-2:]
    assert np.allclose(beta, direct, atol=1e-10)
    assert np.allclose(fit.beta_operator @ y, beta, atol=1e-10)


def test_treatment_scaling_invariance_by_1000():
    rng = np.random.default_rng(8)
    n = 90
    x0 = np.column_stack((np.ones(n), rng.normal(size=n)))
    z = rng.normal(size=(n, 1)); y = .42 * z + x0 @ np.array([[.1], [.2]]) + rng.normal(size=(n, 1))
    w = rng.uniform(.5, 1.5, size=n)
    b1, _ = sealed.weighted_fwl(y, z, x0, w)
    b2, _ = sealed.weighted_fwl(y, 1000 * z, x0, w)
    assert np.allclose(b1, 1000 * b2, atol=1e-10)


def test_known_covariance_matches_small_monte_carlo_fixture():
    rng = np.random.default_rng(71)
    n = 16
    b = rng.normal(size=n)
    groups = {"stocks": np.array([str(i // 2) for i in range(n)]),
              "proxies": np.array([str(i // 4) for i in range(n)]),
              "waves": np.array([str(i // 8) for i in range(n)])}
    analytic = sealed._covariance_for_operator(b, groups, True)
    errors = sealed._draw_errors(np.random.default_rng(72), groups, 12000, True)
    empirical = np.cov(np.einsum("n,rnh->rh", b, errors).T)
    assert np.allclose(empirical, analytic, rtol=.08, atol=.02)


def test_rank_guard_and_missing_input_blocking():
    x0 = np.ones((6, 1)); z = np.ones((6, 1))
    with pytest.raises(sealed.RankFailure):
        sealed.weighted_fwl(np.zeros(6), z, x0, np.ones(6))
    with pytest.raises(sealed.MissingRequiredInputError):
        sealed.require_actual_design_inputs({"calendar": None, "sue": None, "mask": None})
    with pytest.raises(sealed.MissingRequiredInputError, match="MISSING_REQUIRED_INPUT_BLOCK"):
        sealed.require_actual_design_inputs({})
    with pytest.raises(sealed.MissingRequiredInputError, match="PROTECTED_VIEW_GUARD"):
        sealed.require_actual_design_inputs({name: Path(__file__) for name in sealed.REQUIRED_ACTUAL_DESIGN_COMPONENTS})
    with pytest.raises(sealed.MissingRequiredInputError, match="SPONSOR_GUARD"):
        sealed.require_signed_economic_sponsors(None)


def test_forbidden_path_denial():
    with pytest.raises(sealed.SealedInputError, match="FORBIDDEN_PATH_DENIED"):
        sealed.assert_safe_metadata_path(Path("/tmp/post_conversion_earnings_outcomes.csv"))
    with pytest.raises(sealed.SealedInputError, match="CANONICAL_EXPOSURE_ROOT_GUARD"):
        sealed.assert_safe_metadata_path(Path("/tmp/exposure_stock_wave_all.csv"))


def test_blank_future_leakage_and_sponsor_guard(tmp_path):
    p = tmp_path / "exposure_stock_wave_all.csv"
    p.write_text("permno,wave_id,effective_date,advisers,pre_report_date_max,primary_ready,exposure_ownership,is_dimensional\n"
                 ",W1,2026-01-01,Unsigned Proxy,2025-12-31,True,0.01,False\n")
    with pytest.raises(sealed.SealedInputError, match="BLANK_KEY_GUARD"):
        sealed.load_cells(p, fixture_only=True)
    p.write_text("permno,wave_id,effective_date,advisers,pre_report_date_max,primary_ready,exposure_ownership,is_dimensional\n"
                 "1,W1,2099-01-01,Unsigned Proxy,2025-12-31,True,0.01,False\n")
    with pytest.raises(sealed.SealedInputError, match="FUTURE_EFFECTIVE_DATE_GUARD"):
        sealed.load_cells(p, fixture_only=True)
    p.write_text("permno,wave_id,effective_date,advisers,pre_report_date_max,primary_ready,exposure_ownership,is_dimensional\n"
                 "1,W1,2026-01-01,Unsigned Proxy,2026-01-01,True,0.01,False\n")
    with pytest.raises(sealed.SealedInputError, match="LEAKAGE_GUARD"):
        sealed.load_cells(p, fixture_only=True)
    assert "unsigned proxy" in sealed.measured_support_rows({"a": [sealed.Cell("1", "W", "2025-01-01", .01, "proxy", False, "2024-01-01")]})[0]["limitation"].lower()


def test_ownership_unit_preannouncement_and_signed_sponsor_guards(tmp_path):
    p = tmp_path / "exposure_stock_wave_all.csv"
    header = "permno,wave_id,effective_date,advisers,pre_report_date_max,primary_ready,exposure_ownership,is_dimensional\n"
    p.write_text(header + "1,W1,2026-01-01,Unsigned Proxy,2025-12-31,True,10.0,False\n")
    with pytest.raises(sealed.SealedInputError, match="OWNERSHIP_UNIT_RANGE_GUARD"):
        sealed.load_cells(p, fixture_only=True)
    cells = [sealed.Cell("1", "W1", "2026-06-01", .01, "proxy", False, "2026-04-01")]
    with pytest.raises(sealed.MissingRequiredInputError, match="PRE_ANNOUNCEMENT_ELIGIBILITY_BLOCK"):
        sealed.validate_pre_announcement_eligibility(cells, None)
    with pytest.raises(sealed.SealedInputError, match="PRE_ANNOUNCEMENT_LEAKAGE_GUARD"):
        sealed.validate_pre_announcement_eligibility(cells, {"W1": "2026-02-01"})
    with pytest.raises(sealed.SealedInputError, match="PRE_ANNOUNCEMENT_LEAKAGE_GUARD"):
        sealed.validate_pre_announcement_eligibility(iter(cells), {"W1": "2026-02-01"})
    crosswalk = tmp_path / "sponsor.csv"
    crosswalk.write_text("adviser_proxy,economic_sponsor_id,signed_by,signed_date,status\nproxy,e1,,,SIGNED\n")
    with pytest.raises(sealed.MissingRequiredInputError, match="SPONSOR_GUARD"):
        sealed.require_signed_economic_sponsors(crosswalk, fixture_only=True)
    crosswalk.write_text("adviser_proxy,economic_sponsor_id,signed_by,signed_date,status\nproxy,e1,PI,2026-09-13,SIGNED\n")
    sealed.require_signed_economic_sponsors(crosswalk, fixture_only=True)
