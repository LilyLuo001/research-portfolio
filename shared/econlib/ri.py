"""Randomization / permutation inference.

Distribution-free: instead of trusting an asymptotic reference distribution, it
re-draws the treatment assignment under the sharp null and reads the p-value off
the permutation distribution of the test statistic. Ideal for the small-N,
known-assignment-mechanism designs in this portfolio.
"""
import numpy as np


def randomization_inference(stat_fn, treat, n_perm=2000, seed=0, two_sided=True):
    """Permutation p-value for a treatment effect.

    stat_fn(treat_vector) -> scalar test statistic (e.g. a diff-in-means or an
    ATT). `treat` is the observed 0/1 assignment; permutations reshuffle it,
    holding the number treated fixed (the sharp null of no effect).
    """
    rng = np.random.default_rng(seed)
    treat = np.asarray(treat)
    obs = float(stat_fn(treat))
    ge = 0
    for _ in range(n_perm):
        perm = rng.permutation(treat)
        s = float(stat_fn(perm))
        if (abs(s) >= abs(obs)) if two_sided else (s >= obs):
            ge += 1
    p = (ge + 1) / (n_perm + 1)
    return {"stat_obs": obs, "p_value": float(p), "n_perm": n_perm}


def did_diff_in_means(pre, post):
    """Convenience statistic for a 2-period design: returns a function mapping a
    treatment vector to mean(Δ | treated) − mean(Δ | control), where Δ = post−pre.
    """
    pre = np.asarray(pre, float)
    post = np.asarray(post, float)
    delta = post - pre

    def stat(treat):
        treat = np.asarray(treat).astype(bool)
        if treat.sum() == 0 or (~treat).sum() == 0:
            return 0.0
        return delta[treat].mean() - delta[~treat].mean()

    return stat
