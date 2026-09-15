#!/usr/bin/env python3
"""Outcome-blind clock interpretation sensitivity for fixed W021 release keys."""

import argparse
import hashlib
import json
from datetime import timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def interpret(display_dt: pd.Timestamp, scenario: str) -> pd.Timestamp:
    value = display_dt.to_pydatetime()
    if scenario == "DISPLAY_AS_AMERICA_NEW_YORK":
        return pd.Timestamp(value.replace(tzinfo=ZoneInfo("America/New_York")))
    if scenario == "DISPLAY_AS_FIXED_UTC_MINUS_05":
        fixed = value.replace(tzinfo=timezone(timedelta(hours=-5)))
        return pd.Timestamp(fixed.astimezone(ZoneInfo("America/New_York")))
    if scenario == "DISPLAY_AS_UTC":
        utc = value.replace(tzinfo=timezone.utc)
        return pd.Timestamp(utc.astimezone(ZoneInfo("America/New_York")))
    raise ValueError(scenario)


def classify(local_dt: pd.Timestamp, calendar: dict) -> str:
    day = local_dt.strftime("%Y-%m-%d")
    if day not in calendar:
        return "NON_SESSION_LOCAL_DATE"
    entry = calendar[day]
    open_dt = pd.Timestamp(f"{day} {entry['open_local']}", tz="America/New_York")
    close_dt = pd.Timestamp(f"{day} {entry['close_local']}", tz="America/New_York")
    cutoff = close_dt - pd.Timedelta(minutes=60)
    if local_dt < open_dt:
        return "PRE_OPEN"
    if local_dt <= cutoff:
        return "RTH60_NOMINAL"
    if local_dt < close_dt:
        return "RTH_LATE"
    return "AFTER_CLOSE"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--analyst", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)

    meta = pd.read_csv(
        args.metadata,
        usecols=[
            "candidate_id",
            "provisional_tier",
            "event_side",
            "anndats",
            "anntims",
            "accounting_period_date_key",
        ],
        dtype=str,
    ).drop_duplicates()
    meta = meta.rename(columns={"accounting_period_date_key": "event_key"})
    meta["display_dt"] = pd.to_datetime(
        meta["anndats"] + " " + meta["anntims"], errors="coerce"
    )
    if meta["display_dt"].isna().any():
        raise ValueError("UNPARSEABLE_DISPLAY_CLOCK")

    analyst = pd.read_csv(
        args.analyst,
        usecols=["event_key", "scope", "family", "rule", "coverage_class"],
        dtype=str,
    )
    analyst = analyst.loc[
        analyst["scope"].eq("W021")
        & analyst["family"].eq("DIRECT")
        & analyst["rule"].eq("EPS_BASE"),
        ["event_key", "coverage_class"],
    ].drop_duplicates()
    meta = meta.merge(analyst, on="event_key", how="left", validate="one_to_one")
    meta["analyst_min2"] = meta["coverage_class"].eq(
        "OBSERVED_AT_LEAST_2_LOWER_BOUND"
    )

    cal = pd.read_csv(
        args.calendar,
        usecols=["session_date", "calendar_timezone", "open_local", "close_local"],
        dtype=str,
    )
    if set(cal["calendar_timezone"]) != {"America/New_York"}:
        raise ValueError("CALENDAR_TIMEZONE")
    calendar = cal.set_index("session_date")[["open_local", "close_local"]].to_dict("index")

    scenarios = [
        "DISPLAY_AS_AMERICA_NEW_YORK",
        "DISPLAY_AS_FIXED_UTC_MINUS_05",
        "DISPLAY_AS_UTC",
    ]
    rows = []
    for scenario in scenarios:
        part = meta.copy()
        part["local_dt"] = part["display_dt"].map(lambda x: interpret(x, scenario))
        part["clock_class"] = part["local_dt"].map(lambda x: classify(x, calendar))
        part["scenario"] = scenario
        rows.append(part)

    # Separate sensitivity: if Eastern display time is a receipt delayed by an
    # unknown 0--60 minutes, require the entire possible public-time interval to
    # remain inside RTH60. This is illustrative, not a certified delay bound.
    lag = meta.copy()
    lag["local_upper"] = lag["display_dt"].map(
        lambda x: interpret(x, "DISPLAY_AS_AMERICA_NEW_YORK")
    )
    lag["local_lower"] = lag["local_upper"] - pd.Timedelta(minutes=60)
    lag["clock_class"] = [
        "RTH60_ROBUST_TO_0_60M_RECEIPT_LAG"
        if classify(lo, calendar) == "RTH60_NOMINAL"
        and classify(hi, calendar) == "RTH60_NOMINAL"
        else "NOT_ROBUST_RTH60_UNDER_0_60M_LAG"
        for lo, hi in zip(lag["local_lower"], lag["local_upper"])
    ]
    lag["scenario"] = "EASTERN_WITH_PUBLIC_TIME_IN_RECEIPT_MINUS_0_60M"
    rows.append(lag)
    result = pd.concat(rows, ignore_index=True)

    args.out.mkdir(parents=True)
    aggregate = (
        result.groupby(
            ["scenario", "provisional_tier", "event_side", "clock_class"],
            dropna=False,
        )
        .agg(
            release_keys=("event_key", "nunique"),
            stocks=("candidate_id", "nunique"),
            analyst_min2_keys=("analyst_min2", "sum"),
        )
        .reset_index()
    )
    aggregate.to_csv(args.out / "clock_sensitivity_aggregate.csv", index=False)

    eligible_labels = {
        "DISPLAY_AS_AMERICA_NEW_YORK": "RTH60_NOMINAL",
        "DISPLAY_AS_FIXED_UTC_MINUS_05": "RTH60_NOMINAL",
        "DISPLAY_AS_UTC": "RTH60_NOMINAL",
        "EASTERN_WITH_PUBLIC_TIME_IN_RECEIPT_MINUS_0_60M": "RTH60_ROBUST_TO_0_60M_RECEIPT_LAG",
    }
    support_rows = []
    for scenario, label in eligible_labels.items():
        part = result.loc[
            result["scenario"].eq(scenario)
            & result["clock_class"].eq(label)
            & result["analyst_min2"]
            & result["event_side"].isin(["PRE", "POST"])
            & result["provisional_tier"].isin(["high", "low"])
        ]
        counts = (
            part.groupby(["provisional_tier", "candidate_id", "event_side"])
            .agg(release_keys=("event_key", "nunique"))
            .reset_index()
        )
        pivot = counts.pivot_table(
            index=["provisional_tier", "candidate_id"],
            columns="event_side",
            values="release_keys",
            fill_value=0,
        ).reset_index()
        for col in ["PRE", "POST"]:
            if col not in pivot:
                pivot[col] = 0
        for tier in ["high", "low"]:
            t = pivot.loc[pivot["provisional_tier"].eq(tier)]
            support_rows.append(
                {
                    "scenario": scenario,
                    "tier": tier,
                    "stocks_with_at_least_1_pre_and_1_post": int(
                        ((t["PRE"] >= 1) & (t["POST"] >= 1)).sum()
                    ),
                    "stocks_with_at_least_8_pre_and_4_post": int(
                        ((t["PRE"] >= 8) & (t["POST"] >= 4)).sum()
                    ),
                    "stage_a_at_least_2_stocks_each_tier": "ASSESSED_AFTER_BOTH_TIERS",
                    "stage_a_3_stocks_each_tier": "ASSESSED_AFTER_BOTH_TIERS",
                }
            )
    support = pd.DataFrame(support_rows)
    for scenario, group in support.groupby("scenario"):
        minimum = group["stocks_with_at_least_1_pre_and_1_post"].min()
        support.loc[group.index, "stage_a_at_least_2_stocks_each_tier"] = (
            "PASS_NECESSARY_ONLY" if minimum >= 2 else "FAIL"
        )
        support.loc[group.index, "stage_a_3_stocks_each_tier"] = (
            "PASS_NECESSARY_ONLY" if minimum >= 3 else "FAIL"
        )
    support.to_csv(args.out / "necessary_support_by_clock_scenario.csv", index=False)

    receipt = {
        "status": "COMPLETE_HYPOTHETICAL_NOT_CERTIFIED",
        "release_keys": int(meta["event_key"].nunique()),
        "code_sha256": sha256(Path(__file__)),
        "metadata_sha256": sha256(args.metadata),
        "analyst_sha256": sha256(args.analyst),
        "calendar_sha256": sha256(args.calendar),
        "aggregate_sha256": sha256(args.out / "clock_sensitivity_aggregate.csv"),
        "support_sha256": sha256(args.out / "necessary_support_by_clock_scenario.csv"),
        "scenarios_are_not_source_certification": True,
        "receipt_lag_0_60m_is_illustrative_not_empirically_bounded": True,
        "prices_returns_financial_values_outcomes_read": False,
        "row_level_output_exported": False,
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
