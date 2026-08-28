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
