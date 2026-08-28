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
        ("market-model estimation window", "[−250, −21]"),
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
    # DGTW must be named as robustness, and confined to daily-or-longer
    assert "稳健性" in block and "日内期限禁止" in block
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

    for h in bp.INTRADAY_HORIZONS:
        with pytest.raises(bp.BenchmarkPolicyError):
            bp.assert_benchmark_allowed("dgtw", h)
    for h in ("close", "+1d", "+120d"):
        bp.assert_benchmark_allowed("dgtw", h)          # allowed daily+

    # one benchmark across the whole curve
    assert len({bp.primary_benchmark(h) for h in bp.HORIZONS}) == 1
    with pytest.raises(bp.BenchmarkPolicyError):
        bp.assert_curve_uses_one_benchmark({"5m": bp.PRIMARY, "close": "dgtw"})
    # robustness may not be reported as the headline
    for b in bp.ROBUSTNESS:
        with pytest.raises(bp.BenchmarkPolicyError):
            bp.assert_is_headline(b)


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
