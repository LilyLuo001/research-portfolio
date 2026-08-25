#!/usr/bin/env python3
"""REFR-R2 module 3 — leave-one-out basket response and the refraction lever.

Three objects, per C0-R:

  beta_b_full(wave)  = Σ_j w_j · beta_j                 over the wave's basket
  beta_b_loo(i)      = (beta_b_full − w_i·beta_i) / (1 − w_i)
  L_i                = beta_b_loo(i) − beta_i
                     = (1 − beta_i) + (beta_b_loo(i) − 1)
                     ≡ L_mkt_i      + L_tilt_i

The leave-one-out step is not cosmetic: without it, a stock's own beta sits on
both sides of the regression and the mechanical own-component manufactures the
correlation the design is trying to measure. Assert A9 re-derives beta_b_loo
from beta_b_full, w_i and beta_i on 50 sampled rows at 1e-10 — this module is
the thing A9 is checking, so it computes the identity the same way A9 inverts it.

F_tilt is the basket's NON-market announcement response: the basket's
announcement-day return orthogonalized to the market, then regressed on S_std.
It is the one component no market-compression story can generate, which is why
Gate-0's G4 reads it alongside D_b = |beta_b_loo − 1|.

Vendor-free: basket and market returns arrive as injected frames.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# A single holding at weight 1 leaves nothing to hold out; anything closer to 1
# than this makes the LOO denominator explode rather than inform.
MAX_LOO_WEIGHT = 0.99


def basket_full_betas(betas: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """beta_b_full per wave. Weights are PRE-period holding weights (A8 checks
    that they sum to ~1 per wave); this function does not renormalize them —
    silently rescaling a basket that does not sum to 1 would hide the very
    coverage gap A8 exists to surface."""
    m = weights.merge(betas[["permno", "wave", "beta_i"]], on=["permno", "wave"],
                      how="left")
    missing = m["beta_i"].isna()
    if missing.any():
        # UPSTREAM_ISSUE, never a fill: a basket member with no estimable beta
        # is dropped from beta_b_full and counted, per the R2 engineering rule.
        m = m[~missing]
    out = (m.assign(contrib=m["weight"] * m["beta_i"])
             .groupby("wave", as_index=False)
             .agg(beta_b_full=("contrib", "sum"),
                  basket_weight_sum=("weight", "sum"),
                  n_holdings=("permno", "size")))
    out["n_members_dropped_no_beta"] = int(missing.sum())
    return out


def leave_one_out(betas: pd.DataFrame, weights: pd.DataFrame,
                  basket: pd.DataFrame) -> pd.DataFrame:
    """Attach beta_b_loo to every (permno, wave).

    A stock outside its wave's basket has nothing to leave out, so its LOO
    response IS the full basket response — the control-group case, and the
    reason this is a left join rather than an inner one.
    """
    m = (betas.merge(weights[["permno", "wave", "weight"]], on=["permno", "wave"],
                     how="left")
              .merge(basket[["wave", "beta_b_full"]], on="wave", how="left"))
    w = m["weight"].fillna(0.0).to_numpy(float)
    bf = m["beta_b_full"].to_numpy(float)
    bi = m["beta_i"].to_numpy(float)

    too_heavy = w > MAX_LOO_WEIGHT
    with np.errstate(invalid="ignore", divide="ignore"):
        loo = np.where(w > 0, (bf - w * bi) / (1.0 - w), bf)
    loo = np.where(too_heavy, np.nan, loo)      # recorded as missing, never inf
    m["beta_b_loo"] = loo
    m["loo_undefined"] = too_heavy
    return m.drop(columns=["weight"])


def lever_decomposition(frame: pd.DataFrame) -> pd.DataFrame:
    """L and its two components. The identity L = L_mkt + L_tilt is algebraic,
    so A7 verifying it row-by-row is really checking that nothing downstream
    overwrote one of the three columns independently."""
    out = frame.copy()
    out["L_mkt"] = 1.0 - out["beta_i"]
    out["L_tilt"] = out["beta_b_loo"] - 1.0
    out["L"] = out["L_mkt"] + out["L_tilt"]
    return out


def factor_tilt(basket_returns: pd.DataFrame, market_returns: pd.DataFrame,
                surprises: pd.DataFrame, wave_effective: pd.Series) -> pd.DataFrame:
    """F_tilt per wave: sensitivity to S_std of the basket return orthogonalized
    to the market, estimated on PRE-period announcements only.

    basket_returns: wave | announcement_id | r_basket
    market_returns: announcement_id | r_mkt
    """
    s = surprises.dropna(subset=["S_std"])[["announcement_id", "date_ET", "S_std"]]
    df = (basket_returns.merge(market_returns, on="announcement_id", how="inner")
                        .merge(s, on="announcement_id", how="inner"))
    df["date_ET"] = pd.to_datetime(df["date_ET"])

    rows = []
    for wave, g in df.groupby("wave", sort=True):
        pre = g[g["date_ET"] < pd.Timestamp(wave_effective.loc[wave])]
        if len(pre) < 3:
            rows.append({"wave": wave, "F_tilt": np.nan, "F_tilt_se": np.nan,
                         "n_pre": len(pre)})
            continue
        rm = pre["r_mkt"].to_numpy(float)
        rb = pre["r_basket"].to_numpy(float)
        s_std = pre["S_std"].to_numpy(float)
        # step 1: strip the market component from the basket return
        Xm = np.column_stack([np.ones(len(rm)), rm])
        cm, *_ = np.linalg.lstsq(Xm, rb, rcond=None)
        resid = rb - Xm @ cm
        # step 2: what is left, against the surprise
        Xs = np.column_stack([np.ones(len(s_std)), s_std])
        cs, *_ = np.linalg.lstsq(Xs, resid, rcond=None)
        e = resid - Xs @ cs
        dof = len(s_std) - 2
        se = np.nan
        if dof > 0 and not np.allclose(s_std, s_std[0]):
            s2 = float(e @ e) / dof
            se = float(np.sqrt(s2 * np.linalg.inv(Xs.T @ Xs)[1, 1]))
        rows.append({"wave": wave, "F_tilt": float(cs[1]), "F_tilt_se": se,
                     "n_pre": len(pre)})
    return pd.DataFrame(rows)


def build_basket(betas: pd.DataFrame, weights: pd.DataFrame,
                 basket_returns: pd.DataFrame | None = None,
                 market_returns: pd.DataFrame | None = None,
                 surprises: pd.DataFrame | None = None,
                 wave_effective: pd.Series | None = None):
    """Module-3 entry point. Returns (betas_with_loo_and_lever, basket_frame)."""
    basket = basket_full_betas(betas, weights)
    enriched = lever_decomposition(leave_one_out(betas, weights, basket))
    if basket_returns is not None:
        tilt = factor_tilt(basket_returns, market_returns, surprises, wave_effective)
        basket = basket.merge(tilt, on="wave", how="left")
    return enriched, basket
