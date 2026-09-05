"""Frozen formulas for the ETF weight-shape gate audit.

These helpers are intentionally outcome-free.  Names preserve the economic
meaning required by the September 2026 gate protocol.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd


GATE1_MAX_R2 = 0.70
GATE1_MIN_RESIDUAL_SD_RATIO = 0.30
GATE2_MIN_P90_IMPACT_BPS = 3.0
GATE2_MIN_CAPACITY_MDE_RATIO = 2.0
PRIMARY_MAX_STALENESS_DAYS = 120
FLOW_SCENARIO_BPS = (1, 5, 10, 25, 50, 100)
RANDOM_SEED = 20260905


def latest_prior_snapshot(
    observations: pd.DataFrame,
    target_date: pd.Timestamp,
    *,
    date_col: str,
    id_col: str,
    max_staleness_days: int = PRIMARY_MAX_STALENESS_DAYS,
    strict: bool = False,
) -> pd.DataFrame:
    """Return one latest point-in-time observation per ID without look-ahead."""
    target = pd.Timestamp(target_date)
    dates = pd.to_datetime(observations[date_col], errors="coerce")
    allowed = dates.lt(target) if strict else dates.le(target)
    work = observations.loc[allowed].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col, id_col])
    work = work.loc[(target - work[date_col]).dt.days.le(max_staleness_days)]
    if work.empty:
        return work
    idx = work.groupby(id_col, sort=False)[date_col].idxmax()
    out = work.loc[idx].copy()
    out["snapshot_staleness_days"] = (target - out[date_col]).dt.days
    return out


def align_portfolio_aum(
    observations: pd.DataFrame,
    target_date: pd.Timestamp,
    *,
    portfolio_col: str = "crsp_portno",
    share_class_col: str = "crsp_fundno",
    date_col: str = "aum_date",
    value_col: str = "aum_million",
    max_staleness_days: int = PRIMARY_MAX_STALENESS_DAYS,
) -> pd.DataFrame:
    """Align each share class separately, then sum point-in-time portfolio AUM."""
    selected = latest_prior_snapshot(
        observations,
        target_date,
        date_col=date_col,
        id_col=share_class_col,
        max_staleness_days=max_staleness_days,
    )
    if selected.empty:
        return pd.DataFrame(
            columns=[
                portfolio_col,
                "aum_million",
                "aum_date",
                "aum_date_gap_days",
                "aum_share_class_count",
            ]
        )
    selected[value_col] = pd.to_numeric(selected[value_col], errors="coerce")
    selected = selected.dropna(subset=[portfolio_col, value_col])
    target = pd.Timestamp(target_date)
    out = (
        selected.groupby(portfolio_col, as_index=False)
        .agg(
            aum_million=(value_col, "sum"),
            aum_date=(date_col, "min"),
            aum_share_class_count=(share_class_col, "nunique"),
        )
    )
    out["aum_date_gap_days"] = (target - out.aum_date).dt.days
    return out


def same_and_next_trading_day_mappings(
    announcement_dates: pd.Series, trading_dates: pd.Series
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """Return date-only reaction mappings without assuming time-zone semantics.

    A trading-day announcement maps to that day and the following trading day.
    A weekend/holiday announcement maps to the next available trading day under
    both rules because there is no distinct same-day trading session to shift.
    """
    calendar = np.array(
        sorted(pd.to_datetime(trading_dates).dropna().unique()),
        dtype="datetime64[ns]",
    )
    announced = pd.to_datetime(announcement_dates).to_numpy(dtype="datetime64[ns]")
    pos = np.searchsorted(calendar, announced, side="left")
    in_range = pos < len(calendar)
    clipped = np.minimum(pos, max(len(calendar) - 1, 0))
    same = np.full(len(announced), np.datetime64("NaT"), dtype="datetime64[ns]")
    if len(calendar):
        same[in_range] = calendar[clipped[in_range]]
    exact = np.zeros(len(announced), dtype=bool)
    if len(calendar):
        exact[in_range] = calendar[clipped[in_range]] == announced[in_range]
    next_pos = pos + exact.astype(int)
    next_in_range = next_pos < len(calendar)
    nxt = np.full(len(announced), np.datetime64("NaT"), dtype="datetime64[ns]")
    if len(calendar):
        nxt[next_in_range] = calendar[next_pos[next_in_range]]
    return pd.DatetimeIndex(same), pd.DatetimeIndex(nxt)


def actual_weight(position_value: pd.Series, fund_net_assets_dollars: pd.Series) -> pd.Series:
    """Position value divided by total fund net assets; never renormalized."""
    denom = pd.to_numeric(fund_net_assets_dollars, errors="coerce")
    numer = pd.to_numeric(position_value, errors="coerce")
    return numer.div(denom.where(denom.gt(0)))


def equity_sleeve_weight(position_value: pd.Series, group: pd.Series) -> pd.Series:
    """Diagnostic weight within observed domestic-common-equity positions."""
    values = pd.to_numeric(position_value, errors="coerce")
    denom = values.groupby(group).transform("sum")
    return values.div(denom.where(denom.gt(0)))


def classify_weight_style(beta: float, r_squared: float, benchmark_verified: bool = False) -> tuple[str, str]:
    """Return mutually exclusive category and transparent detail label."""
    if not np.isfinite(beta) or not np.isfinite(r_squared):
        return "OTHER_WEIGHTED", "INSUFFICIENT_REGRESSION"
    if -0.15 <= beta <= 0.15:
        return "EQUAL_WEIGHTED", "EQUAL_LIKE"
    if 0.85 <= beta <= 1.15:
        if r_squared >= 0.80:
            return "CAP_HIGH_FIT", "CAP_LIKE_HIGH_FIT"
        if benchmark_verified:
            return "CAP_SAMPLED", "CAP_SAMPLED_VERIFIED"
        return "OTHER_WEIGHTED", "CAP_LIKE_LOW_FIT"
    return "OTHER_WEIGHTED", "OTHER_WEIGHTED"


def nav_shock_notional(aum_dollars: float, source_weight: float, source_return: float) -> float:
    """Descriptive NAV-shock loading; never a flow or trade measure."""
    return float(aum_dollars) * abs(float(source_weight) * float(source_return))


def routed_notional(flow_dollars: float, absolute_weight_wedge: float) -> float:
    """Route an explicitly supplied flow/ceiling/scenario through a weight wedge."""
    return abs(float(flow_dollars)) * abs(float(absolute_weight_wedge))


def impact_linear_bps(routed_dollars: float, peer_adv_dollars: float) -> float:
    """Frozen 10 bps per 1% ADV linear capacity calibration."""
    if not np.isfinite(peer_adv_dollars) or peer_adv_dollars <= 0:
        return math.nan
    share = abs(float(routed_dollars)) / float(peer_adv_dollars)
    return 10.0 * (share / 0.01)


def impact_sqrt_bps(routed_dollars: float, peer_adv_dollars: float) -> float:
    """Frozen 10 bps per sqrt(1% ADV) square-root capacity calibration."""
    if not np.isfinite(peer_adv_dollars) or peer_adv_dollars <= 0:
        return math.nan
    share = abs(float(routed_dollars)) / float(peer_adv_dollars)
    return 10.0 * math.sqrt(share / 0.01)


def inverse_hhi(weights: Iterable[float]) -> float:
    """Effective count based on nonnegative contribution shares."""
    x = np.asarray(list(weights), dtype=float)
    x = x[np.isfinite(x) & (x >= 0)]
    if not len(x) or x.sum() <= 0:
        return math.nan
    shares = x / x.sum()
    return float(1.0 / np.square(shares).sum())


def required_flow_share_of_aum(
    target_impact_bps: float,
    peer_adv_dollars: float,
    aum_weight_wedge_sum: float,
    *,
    model: str,
) -> float:
    """AUM share needed to reach a target impact under a frozen calibration.

    ``aum_weight_wedge_sum`` is sum(AUM_f * abs(wedge_jf)) over shared ETFs.
    The return is a fraction of the same ETFs' AUM only when callers divide the
    routed coefficient by their explicitly reported total shared AUM.
    """
    if peer_adv_dollars <= 0 or aum_weight_wedge_sum <= 0:
        return math.nan
    if model == "linear":
        required_trade_share_adv = (target_impact_bps / 10.0) * 0.01
    elif model == "sqrt":
        required_trade_share_adv = (target_impact_bps / 10.0) ** 2 * 0.01
    else:
        raise ValueError("model must be 'linear' or 'sqrt'")
    return required_trade_share_adv * peer_adv_dollars / aum_weight_wedge_sum
