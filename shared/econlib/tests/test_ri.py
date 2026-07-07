"""Randomization inference: small p under a real effect, large p under the null."""
from econlib.ri import randomization_inference, did_diff_in_means
from toydata import two_period


def test_ri_detects_effect():
    pre, post, treat = two_period(n=40, tau=3.0, seed=0)
    stat = did_diff_in_means(pre, post)
    res = randomization_inference(stat, treat, n_perm=1000, seed=0)
    assert res["p_value"] < 0.05
    assert res["stat_obs"] > 2


def test_ri_null():
    pre, post, treat = two_period(n=40, tau=0.0, seed=1)
    stat = did_diff_in_means(pre, post)
    res = randomization_inference(stat, treat, n_perm=1000, seed=0)
    assert res["p_value"] > 0.10
