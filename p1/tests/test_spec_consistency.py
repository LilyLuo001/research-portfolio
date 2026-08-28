"""The implementation specs must agree with the frozen plan.

P1 has three documents an implementing agent actually follows — the plan, the
estimation blueprint, and the variable spec — and they have drifted apart once
already: after v2.1 froze signed `CAR^h` as the primary outcome and (sponsor,
stock) as the dependence structure, the blueprint still specified `wave x
industry` clustering, `|Surprise|`, wave-level bootstrap resampling, and "if the
three disagree, take the most conservative" — a rule the owner rejected twice as
outcome-dependent method selection.

None of that raises at runtime. It just gets implemented. So the agreements are
pinned here.

Each test allows the stale text to survive inside an explicitly marked
supersession note, because the repo's convention is to show the correction rather
than silently overwrite it. What it forbids is the stale text standing as a live
rule.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs" / "基金转换实验_博士研究计划.md"
BLUEPRINT = ROOT / "p1" / "t5_spec" / "估计蓝图.md"
VARSPEC = ROOT / "p1" / "t3_spec" / "变量规格书.md"


def _lines(p):
    return p.read_text().splitlines()


def _near(lines, i, radius=6):
    return "\n".join(lines[max(0, i - radius):i + radius])


SUPERSEDED = ("已删除", "已被取代", "已失效", "取代", "保留以显差异", "原文",
              "v2.1", "~~")


def _every_hit_is_marked_superseded(path, pattern, label):
    lines = _lines(path)
    for i, line in enumerate(lines):
        if not re.search(pattern, line):
            continue
        near = _near(lines, i)
        assert any(m in near for m in SUPERSEDED), (
            f"{path.name}: {label} appears as a live rule at line {i + 1}, not "
            f"inside a supersession note:\n  {line.strip()}")


# --------------------------------------------------------------------------- #
# 1. the outcome variable and the regressor are SIGNED                          #
# --------------------------------------------------------------------------- #
def test_blueprint_main_equation_uses_signed_car_and_sue():
    text = BLUEPRINT.read_text()
    assert "CAR^h_{i,e} = β_h · (SUE_{i,e} × Post_{e,w} × Exposure^pre_{i,w})" in text
    _every_hit_is_marked_superseded(
        BLUEPRINT, r"\|Surprise", "the absolute-value regressor |Surprise|")


def test_variable_spec_defines_the_primary_outcome_it_is_estimated_on():
    """The blueprint's main equation names CAR^h; a variable with no 口径 is a
    guess waiting to be made by whoever implements it."""
    text = VARSPEC.read_text()
    assert "### 0-0. `CAR^h`" in text, "CAR^h has no spec entry"
    assert "D-T3-15" in text and "D-T3-16" in text
    # and Speed must be labelled secondary wherever it is called the main result
    for i, line in enumerate(_lines(VARSPEC)):
        if "Speed^h`(v2.0 主结果)" in line:
            assert "v2.1" in _near(_lines(VARSPEC), i), (
                "Speed^h is still labelled the main result: " + line.strip())


# --------------------------------------------------------------------------- #
# 2. the dependence structure is (sponsor, stock)                               #
# --------------------------------------------------------------------------- #
def test_blueprint_does_not_still_cluster_on_industry():
    _every_hit_is_marked_superseded(
        BLUEPRINT, r"wave\s*[x×]\s*industry|`wave × industry`",
        "wave x industry clustering")


def test_blueprint_bootstrap_resamples_the_frozen_structure():
    text = BLUEPRINT.read_text()
    assert "(发起人, 股票) multiway" in text
    _every_hit_is_marked_superseded(
        BLUEPRINT, r"at the \*\*wave\*\* level", "wave-level bootstrap resampling")


# --------------------------------------------------------------------------- #
# 3. no outcome-dependent method selection, anywhere                            #
# --------------------------------------------------------------------------- #
def test_no_document_tells_the_reader_to_take_the_most_conservative():
    """Rejected twice by the owner: not knowing ex ante which procedure is most
    conservative makes 'take the most conservative' a choice made after seeing
    the results — the same error as 'take the most stars', pointed the other way.
    """
    for path in (PLAN, BLUEPRINT, VARSPEC):
        _every_hit_is_marked_superseded(
            path, r"最保守", "the 'take the most conservative' rule")


def test_no_document_permits_specification_search():
    """CLAUDE.md: never specification-search; report the first run."""
    for path in (PLAN, BLUEPRINT, VARSPEC):
        for i, line in enumerate(_lines(path)):
            if "若显著" in line and "则" in line:
                assert "禁止" in _near(_lines(path), i), (
                    f"{path.name}:{i + 1} reads as a conditional-on-significance "
                    f"rule: {line.strip()}")


# --------------------------------------------------------------------------- #
# 4. v2.1e — the inference procedure is named, the one open parameter is held   #
# --------------------------------------------------------------------------- #
BOOTCLUSTER = ROOT / "p1" / "t5_spec" / "BOOTCLUSTER-DECISION.md"


def test_the_bootstrap_implementation_family_is_named_everywhere_it_matters():
    """An unnamed 'established package' is how a one-way stand-in ships. Both
    the plan and the blueprint have to name boottest and both references."""
    for path in (PLAN, BLUEPRINT):
        t = path.read_text()
        assert "boottest" in t, path.name
        assert "Roodman" in t and "Cameron" in t, path.name
        assert "wildboottest" in t, (
            f"{path.name} must record WHY the Python package is not primary — "
            "otherwise someone reaches for it as the obvious choice")


def test_bootcluster_is_deferred_not_quietly_chosen():
    """The likely candidate must not be written into the spec as the decision.
    A pre-specification made before the facts exist is a guess with a date."""
    assert BOOTCLUSTER.exists()
    t = BOOTCLUSTER.read_text()
    assert "DEFERRED" in t
    # the record itself must still be blank
    for field in ("n_economic_sponsors", "n_treated_sponsors",
                  "bootcluster() choice", "headline run commit"):
        assert field in t, field
    filled = [l for l in t.splitlines()
              if l.startswith(("date  ", "bootcluster() choice"))
              and l.split(":", 1)[-1].strip()]
    assert not filled, (
        "the decision record has been filled in: " + "; ".join(filled) +
        " — if that is real, the headline-run commit must be later than this "
        "file's commit, and this guard should be replaced by that check")


def test_the_ordering_constraint_is_stated_not_just_the_choice():
    """The protection is the timestamp, not the reasoning. If the docs only say
    'justify the choice' without 'before observing the coefficients', the rule
    has no teeth."""
    for path in (PLAN, BLUEPRINT, BOOTCLUSTER):
        t = path.read_text().lower()
        assert ("before any headline" in t or "在看到 β_h 之前" in t), path.name


# --------------------------------------------------------------------------- #
# 5. CAR^h inherits the construction, and only the construction                 #
# --------------------------------------------------------------------------- #
def test_car_h_inherits_the_prespecified_benchmark_and_event_time():
    """CAR^h IS Speed^h's numerator, so it must not acquire a second set of
    choices. Each inherited element is named so a builder cannot re-decide it."""
    t = VARSPEC.read_text()
    block = t.split("### 0-0.")[1].split("### 0-1.")[0]
    for element, needle in [
        ("beta estimation window", "−250"),
        ("announcement timestamp", "anntims"),
        ("pre/intra/post session split", "D-T3-12"),
        ("midquote sampling", "D-T3-13"),
        ("calendar event clock", "D-T3-14"),
        ("+1d endpoint", "D-T3-10"),
        ("single primary benchmark rule", "D-T3-11"),
        ("intraday-DGTW prohibition", "D-T3-17"),
    ]:
        assert needle in block, f"0-0 does not pin the {element} ({needle})"


# --------------------------------------------------------------------------- #
# 6. v2.1f — exactly ONE primary benchmark, and DGTW is not it intraday         #
# --------------------------------------------------------------------------- #
def test_exactly_one_primary_car_benchmark_is_named():
    """'Both reported' does not settle which curve is the headline. If two
    benchmarks can each be called primary, the choice is still open when the
    results arrive — which is the thing being prevented."""
    block = VARSPEC.read_text().split("### 0-0.")[1].split("### 0-1.")[0]
    assert "主基准" in block
    assert "日内市场模型" in block
    # DGTW must be named as robustness, and confined to the frequency it is
    # actually built at — which excludes DAILY, not only intraday (D-T3-24)
    assert "稳健性" in block
    assert "日内禁用,日频同样禁用" in block, (
        "0-0 must say DGTW is unusable at DAILY resolution too — a monthly "
        "benchmark does not make a daily path characteristic-adjusted")
    _every_hit_is_marked_superseded(
        VARSPEC, r"两版并报.*(基准|市场模型)|市场模型.*两版并报",
        "the old 'report both benchmarks' answer")


def test_dgtw_is_refused_at_intraday_horizons_in_code_not_only_in_prose():
    """A daily benchmark subtracted from a 5-minute return does not raise; it
    returns a number, and AR comes out ~= the raw return while the table says
    'characteristic-adjusted'. The rule has to be executable."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "benchmark_policy", ROOT / "p1" / "pipeline" / "benchmark_policy.py")
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)

    # DGTW is monthly-constructed: refused at every horizon finer than monthly,
    # DAILY INCLUDED -- a daily path is not characteristic-adjusted by a monthly
    # benchmark.
    for h in bp.INTRADAY_HORIZONS + ("close", "+1d", "+120d"):
        with pytest.raises(bp.BenchmarkPolicyError):
            bp.assert_benchmark_allowed("dgtw_monthly", h)
    bp.assert_benchmark_allowed("dgtw_monthly", "+3m")        # its own frequency

    # a DAILY DGTW series is unverified, so its horizon set is empty and every
    # use raises with the verification requirement rather than a preference
    for h in ("close", "+1d", "+120d"):
        with pytest.raises(bp.BenchmarkPolicyError) as e:
            bp.assert_benchmark_allowed("dgtw_daily", h)
        assert "NEED_HUMAN" in str(e.value) and "ermport" in str(e.value)
    assert bp.BENCHMARK_HORIZONS["dgtw_daily"] == ()

    # one benchmark across the whole curve
    assert len({bp.primary_benchmark(h) for h in bp.HORIZONS}) == 1
    with pytest.raises(bp.BenchmarkPolicyError):
        bp.assert_curve_uses_one_benchmark(
            {"5m": bp.PRIMARY, "close": "beta_one_market_adjusted"})
    # robustness may not be reported as the headline
    for b in bp.ROBUSTNESS:
        with pytest.raises(bp.BenchmarkPolicyError):
            bp.assert_is_headline(b)


def test_the_primary_formula_has_no_intercept_and_does_not_vary_with_h():
    """A daily α̂ cannot be subtracted from a 5-minute return -- it is a
    per-trading-day drift, so it removes ~78x too much. Scaling it needs an
    intraday drift-allocation convention this project never pre-specified, and
    inventing one after the freeze is a new degree of freedom. Dropping it is
    the only choice that keeps ONE formula at every h."""
    block = VARSPEC.read_text().split("### 0-0.")[1].split("### 0-1.")[0]
    assert "不减 α" in block or "不含截距" in block
    assert "D-T3-22" in block
    varspec = VARSPEC.read_text()
    assert "D-T3-22" in varspec and "D-T3-23" in varspec
    # the scaled-alpha variant exists, as robustness applied uniformly
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "benchmark_policy", ROOT / "p1" / "pipeline" / "benchmark_policy.py")
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    assert "beta_adjusted_market_scaled_alpha" in bp.ROBUSTNESS
    with pytest.raises(bp.BenchmarkPolicyError):
        bp.assert_is_headline("beta_adjusted_market_scaled_alpha")


def test_the_plus1d_assert_compares_against_a_zero_alpha_spine_two():
    """Spine two keeps alpha (dimensionally right at daily), spine zero drops it,
    so CAR^{+1d} and spine two's CAR[0,+1] differ by ~alpha x one day. If the
    spec still claimed they must be equal, the cheapest way to 'fix' the failing
    assert would be to add alpha to spine zero -- putting the dimensional error
    back."""
    varspec = VARSPEC.read_text()
    assert "α 强制为 0" in varspec
    assert "D-T3-23" in varspec


def test_car_h_does_not_inherit_the_denominator_based_sample_filter():
    """Speed^h drops events whose DENOMINATOR is near zero. Applying that to
    CAR^h would import a treatment-correlated selection rule into the headline
    sample: after conversion the response is faster, so R_final's composition
    changes, so which events get dropped depends on treatment."""
    block = VARSPEC.read_text().split("### 0-0.")[1].split("### 0-1.")[0]
    assert "没有分母" in block
    assert "与处理状态相关" in block
    assert "全样本" in block
    assert "D-T3-16" in VARSPEC.read_text()



# --------------------------------------------------------------------------- #
# 7. v2.1h — one market proxy across both legs, frozen as a bundle              #
# --------------------------------------------------------------------------- #
def _bp():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "benchmark_policy", ROOT / "p1" / "pipeline" / "benchmark_policy.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_beta_and_market_leg_must_be_the_same_instrument():
    """The named failure: a CRSP value-weighted beta multiplied into an SPY
    intraday return is two different market portfolios in one formula. It
    produces a plausible number, not an error."""
    bp = _bp()
    bp.assert_proxy_coherent("SPY", "SPY")                    # coherent
    for beta, leg in (("crsp_vwretd", "SPY"), ("SPY", "crsp_vwretd"),
                      ("crsp_ewretd", "SPY")):
        with pytest.raises(bp.ProxyIncoherent) as e:
            bp.assert_proxy_coherent(beta, leg)
        assert "SAME economic proxy" in str(e.value)
    # coherent with itself but not the frozen instrument is still refused --
    # swapping the proxy is a spec change, not a runtime option
    with pytest.raises(bp.ProxyIncoherent):
        bp.assert_proxy_coherent("IVV", "IVV")


def test_the_proxy_bundle_is_frozen_together_not_piecemeal():
    """Instrument, quote convention, session clock and beta source are one
    decision. Freezing them separately is what lets an incoherent pair through."""
    bp = _bp()
    for key in ("instrument", "quote_convention", "session",
                "beta_estimation_instrument", "beta_estimation_window",
                "beta_estimation_return"):
        assert key in bp.MARKET_PROXY, key
    assert bp.MARKET_PROXY["instrument"] == \
        bp.MARKET_PROXY["beta_estimation_instrument"]
    assert bp.MARKET_PROXY["quote_convention"] == "midquote"   # matches D-T3-13
    assert bp.MARKET_PROXY["session"] == "RTH"
    with pytest.raises(bp.ProxyIncoherent):
        bp.assert_proxy_coherent("SPY", "SPY", quote_convention="last_trade")
    with pytest.raises(bp.ProxyIncoherent):
        bp.assert_proxy_coherent("SPY", "SPY", session="ETH")


def test_the_overnight_gap_is_excluded_from_both_legs_identically():
    """Including it in one leg only puts an unhedged overnight move into AR^h,
    and nothing raises."""
    bp = _bp()
    rule = bp.PROXY_OPEN_GAP_RULE
    assert "SAME timestamp" in rule and "neither" in rule
    assert "13:00" in rule                       # early-close sessions
    varspec = VARSPEC.read_text()
    assert "D-T3-27" in varspec and "半日市" in varspec


def test_the_paper_calls_it_beta_adjusted_not_a_market_model():
    """No intercept is subtracted, so 'market model' would imply to a reader
    that a daily alpha was removed intraday."""
    bp = _bp()
    assert bp.PRIMARY == "beta_adjusted_market"
    assert "market_model" not in bp.PRIMARY
    block = VARSPEC.read_text().split("### 0-0.")[1].split("### 0-1.")[0]
    assert "beta-adjusted market abnormal return" in block
    assert "不要写成" in block


# --------------------------------------------------------------------------- #
# 8. v2.1i — one return concept, and the opening gap is its own outcome         #
# --------------------------------------------------------------------------- #
def test_beta_is_estimated_on_price_returns_on_both_legs():
    """The event window is a midquote PRICE return -- a quote midpoint holds no
    dividend. A beta fitted on TOTAL returns carries a dividend-inclusive
    sensitivity into a dividend-free quantity, and `ret`/`retx` are equally
    plausible-looking daily returns, so nothing raises."""
    bp = _bp()
    assert bp.MARKET_PROXY["return_concept"] == "price_return"
    bp.assert_return_concept_coherent("retx", "retx")
    bp.assert_return_concept_coherent("DlyRetx", "DlyRetx")
    for stock, proxy in (("ret", "retx"), ("retx", "ret"), ("DlyRet", "DlyRetx")):
        with pytest.raises(bp.ProxyIncoherent) as e:
            bp.assert_return_concept_coherent(stock, proxy)
        assert "TOTAL return" in str(e.value)
    with pytest.raises(bp.ProxyIncoherent):                # unnamed field
        bp.assert_return_concept_coherent("daily_return", "retx")


def test_the_pull_asks_for_both_return_fields_and_says_they_differ():
    """`ret` is still needed by the daily spines. Pulling only one, or treating
    them as interchangeable, is the failure."""
    import yaml
    spec = yaml.safe_load((ROOT / "p1" / "wrds" / "tables.yaml").read_text())
    cols = spec["pulls"]["dsf"]["columns"]
    assert "ret" in cols and "price_return" in cols
    assert "retx" in cols["price_return"]["candidates"]
    assert "price_vs_total_return" in spec["pulls"]["dsf"]["asserts"]


def test_preopen_and_afterclose_car_is_labelled_post_open():
    """Excluding the gap does not make it disappear: for a pre-open
    announcement a real part of the response happened inside it."""
    bp = _bp()
    assert bp.car_label("pre_open") == bp.POST_OPEN_LABEL
    assert bp.car_label("after_close") == bp.POST_OPEN_LABEL
    assert bp.car_label("intraday") == "full_announcement_response"
    with pytest.raises(bp.BenchmarkPolicyError):
        bp.car_label("premarket")


def test_the_gap_is_a_separate_outcome_never_folded_into_car():
    bp = _bp()
    bp.assert_gap_excluded_from_car("CAR_5m", ["rth_5m"])
    with pytest.raises(bp.BenchmarkPolicyError) as e:
        bp.assert_gap_excluded_from_car("CAR_close",
                                        [bp.GAP_OUTCOME, "rth_to_close"])
    assert "SEPARATE outcome" in str(e.value)
    assert "D-T3-30" in VARSPEC.read_text()


def test_no_document_claims_a_direction_for_the_intraday_beta_bias():
    """'Epps biases intraday beta down' is a directional claim about this sample
    that nothing here has tested. The honest statement is narrower: a
    close-to-close daily beta is imposed on shorter RTH horizons, and beta=1 is
    a robustness check against that extrapolation -- not a correction toward a
    known sign."""
    for path in (PLAN, BLUEPRINT, VARSPEC,
                 ROOT / "docs" / "P1_实现更正_v2_1d.md",
                 ROOT / "p1" / "pipeline" / "benchmark_policy.py"):
        assert "Epps" not in path.read_text(), f"{path.name} still claims a bias direction"
    varspec = VARSPEC.read_text()
    assert "口径外推" in varspec
    assert "不得把 `β ≡ 1` 说成" in varspec
