#!/usr/bin/env python3
"""Build a versioned XNYS core-session projection; no research data are read."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from zoneinfo import ZoneInfo
import exchange_calendars as xc
import pandas as pd
import tzdata

START = pd.Timestamp("2019-01-01")
END_EXCLUSIVE = pd.Timestamp("2026-09-01")
EXPECTED_XC_VERSION = "4.13.2"
EXPECTED_TZDATA_VERSION = "2026.4"
CALENDAR_ID = "XNYS_CORE_exchange_calendars_4.13.2_tzdata_2026.4"
ZONE = ZoneInfo("America/New_York")

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    if xc.__version__ != EXPECTED_XC_VERSION or tzdata.__version__ != EXPECTED_TZDATA_VERSION:
        raise RuntimeError("calendar dependency version mismatch")
    cal = xc.get_calendar("XNYS")
    if cal.first_session > START or cal.last_session < END_EXCLUSIVE - pd.Timedelta(days=1):
        raise RuntimeError("requested interval outside library-supported history")
    schedule = cal.schedule.loc[START:END_EXCLUSIVE - pd.Timedelta(days=1), ["open", "close"]].copy()
    opened = schedule["open"].dt.tz_convert(ZONE)
    closed = schedule["close"].dt.tz_convert(ZONE)
    out = pd.DataFrame({
        "calendar_id": CALENDAR_ID,
        "session_date": schedule.index.strftime("%Y-%m-%d"),
        "calendar_timezone": "America/New_York",
        "open_local": opened.dt.strftime("%H:%M:%S"),
        "close_local": closed.dt.strftime("%H:%M:%S"),
        "open_utc": schedule["open"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "close_utc": schedule["close"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_type": closed.dt.strftime("%H:%M:%S").eq("16:00:00").map({True:"REGULAR_CORE", False:"EARLY_CLOSE_CORE"}),
        "library_name": "exchange_calendars",
        "library_version": EXPECTED_XC_VERSION,
        "tzdata_version": EXPECTED_TZDATA_VERSION,
    })
    target = Path(__file__).with_name("xnys_sessions_2019_2026-08-31.csv")
    out.to_csv(target, index=False, lineterminator="\n")
    receipt = {
        "status": "XNYS_EXCHANGE_SESSION_CALENDAR_COMPLETE",
        "calendar_id": CALENDAR_ID,
        "date_interval": "[2019-01-01,2026-09-01)",
        "library_supported_interval": [str(cal.first_session.date()), str(cal.last_session.date())],
        "session_rows": int(len(out)),
        "regular_core_sessions": int(out.session_type.eq("REGULAR_CORE").sum()),
        "early_close_core_sessions": int(out.session_type.eq("EARLY_CLOSE_CORE").sum()),
        "first_session": out.session_date.iloc[0],
        "last_session": out.session_date.iloc[-1],
        "calendar_csv_sha256": sha256(target),
        "code_sha256": sha256(Path(__file__)),
        "library": {"exchange_calendars": EXPECTED_XC_VERSION, "tzdata": EXPECTED_TZDATA_VERSION},
        "official_primary_sources": [
            "https://www.nyse.com/trade/hours-calendars",
            "https://www.nyse.com/publicdocs/ICE_NYSE_2024_Yearly_Trading_Calendar.pdf",
            "https://www.nyse.com/publicdocs/nyse/regulation/nyse/NYSE_Rules.pdf"
        ],
        "certifies_exchange_calendar_only": True,
        "certifies_ibes_timezone_or_first_public_release": False,
        "earnings_or_market_values_read": False,
        "backend_telemetry": "NOT_OBSERVED"
    }
    Path(__file__).with_name("CALENDAR_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")

if __name__ == "__main__": main()
