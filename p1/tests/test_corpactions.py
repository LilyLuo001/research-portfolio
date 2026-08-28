"""The portfolio's ONE corporate-action convention (p1/t2_wrds/corpactions.py).

P1 and refraction both compare share counts across a date boundary. These tests fix the
implementation; the module's docstring fixes the field semantics. A second, independent
reading of cfacshr elsewhere in the portfolio is the failure this pair exists to prevent.
"""
import pandas as pd
import pytest

import corpactions as ca


def probe(direction="divide"):
    """Names with a KNOWN split and NO trading between the two dates, so correctly adjusted
    counts must be equal. 2-for-1 and 3-for-1."""
    if direction == "divide":
        return pd.DataFrame([{"shares_pre": 100, "cfacshr_pre": 1.0,
                              "shares_post": 200, "cfacshr_post": 2.0},
                             {"shares_pre": 300, "cfacshr_pre": 1.0,
                              "shares_post": 900, "cfacshr_post": 3.0}])
    return pd.DataFrame([{"shares_pre": 100, "cfacshr_pre": 1.0,
                          "shares_post": 200, "cfacshr_post": 0.5},
                         {"shares_pre": 300, "cfacshr_pre": 1.0,
                          "shares_post": 900, "cfacshr_post": 1 / 3.0}])


def test_the_direction_is_read_off_the_probe_in_both_encodings():
    """Either CRSP encoding is plausible from memory; only the probe settles it."""
    assert ca.verify_direction(probe("divide"))["direction"] == "divide"
    assert ca.verify_direction(probe("multiply"))["direction"] == "multiply"


def test_a_probe_with_no_corporate_action_identifies_nothing():
    flat = pd.DataFrame([{"shares_pre": 100, "cfacshr_pre": 1.0,
                          "shares_post": 100, "cfacshr_post": 1.0}])
    v = ca.verify_direction(flat)
    assert v["status"] == "UNVERIFIED" and v["direction"] is None
    assert "NEED_HUMAN" in v["reason"]


def test_the_module_ships_unverified_like_the_p1_schema():
    assert ca.CORPACTION_SCHEMA["status"] == "UNVERIFIED"
    assert ca.CORPACTION_SCHEMA["share_factor"] == "cfacshr"
    assert ca.CORPACTION_SCHEMA["price_factor"] == "cfacpr"


def test_adjusted_shares_refuses_an_unverified_convention():
    with pytest.raises(ca.ConventionError) as e:
        ca.adjusted_shares(pd.Series([100.0]), pd.Series([2.0]), {"status": "UNVERIFIED"})
    assert "NEED_HUMAN" in str(e.value)


def test_a_convention_verified_on_the_price_factor_is_refused():
    """cfacpr and cfacshr differ whenever a distribution moves price without moving share
    count. Substituting one for the other is silent and wrong."""
    conv = dict(ca.verify_direction(probe()), field="cfacpr")
    with pytest.raises(ca.ConventionError) as e:
        ca.adjusted_shares(pd.Series([100.0]), pd.Series([2.0]), conv)
    assert "not interchangeable" in str(e.value)


def test_a_split_adjusts_to_the_same_count():
    conv = ca.verify_direction(probe())
    a = ca.adjusted_shares(pd.Series([100.0]), pd.Series([1.0]), conv)
    b = ca.adjusted_shares(pd.Series([200.0]), pd.Series([2.0]), conv)
    assert float(a.iloc[0]) == pytest.approx(float(b.iloc[0]))


def test_real_trading_survives_the_adjustment():
    """The adjustment must not launder actual portfolio change into zero."""
    conv = ca.verify_direction(probe())
    a = ca.adjusted_shares(pd.Series([100.0]), pd.Series([1.0]), conv)
    b = ca.adjusted_shares(pd.Series([150.0]), pd.Series([1.0]), conv)
    assert float(b.iloc[0]) > float(a.iloc[0])


# --------------------------------------------------------------------------- #
# as-of dates                                                                  #
# --------------------------------------------------------------------------- #

def test_a_filing_date_is_refused_where_an_as_of_date_belongs():
    """Filing lag is 30-60+ days: a pre-conversion portfolio filed after the conversion
    would read as post-conversion, inverting the comparison."""
    for col in ("filing_date", "acceptance_date", "date_filed", "FILED_DATE"):
        with pytest.raises(ca.ConventionError) as e:
            ca.assert_as_of_not_filing_date(["permno", col, "shares"])
        assert "FILING date" in str(e.value)
        assert ca.HOLDINGS_AS_OF_FIELD in str(e.value)


def test_the_report_date_passes():
    ca.assert_as_of_not_filing_date(["permno", ca.HOLDINGS_AS_OF_FIELD, "as_of", "shares"])


def test_pre_and_post_are_split_at_the_effective_date_with_the_p1_rule():
    """P1's rule reused verbatim: strictly before is PRE; the effective date itself is
    already POST, because that snapshot reflects the conversion."""
    assert ca.classify_as_of("2023-02-14", "2023-02-15") == "pre"
    assert ca.classify_as_of("2023-02-15", "2023-02-15") == "post"
    assert ca.classify_as_of("2023-02-16", "2023-02-15") == "post"
    assert ca.classify_as_of(None, "2023-02-15") == "unknown"
