# Versioned XNYS core-session calendar

This directory contains a calendar-only projection for `[2019-01-01, 2026-09-01)`. It was generated with `exchange_calendars==4.13.2` and `tzdata==2026.4`; the installed library supports 2006-09-15 through 2027-09-15, so no dates outside supported history were invented.

The CSV has one row per XNYS session with `calendar_id,session_date,calendar_timezone,open_local,close_local`, UTC bounds, session type and dependency versions. Core hours are 09:30–16:00 America/New_York except library-defined early closes at 13:00. Validation covers winter/summer UTC conversion, both DST transitions, weekends, recurring holidays, the 2021/2022 Juneteenth transition and early closes.

Primary documentation: the [NYSE hours and holiday calendar](https://www.nyse.com/trade/hours-calendars) documents core hours and current holidays/early closes; the official [2024 NYSE trading calendar](https://www.nyse.com/publicdocs/ICE_NYSE_2024_Yearly_Trading_Calendar.pdf) supplies an in-range historical holiday/13:00-close cross-check; [NYSE Rules](https://www.nyse.com/publicdocs/nyse/regulation/nyse/NYSE_Rules.pdf) document exchange hours/holiday authority. The library remains the versioned schedule generator; these sources are targeted controls, not a claim that a current webpage alone enumerates every historical exception.

This artifact certifies only the XNYS calendar projection. It does not certify that an IBES clock is Eastern time, a first-public release, precise to a minute, or eligible for RTH/RTH-60. No earnings, forecast, quote, price, return or response data were read. The next clock step still requires a versioned source-timezone and uncertainty interval before joining release metadata to this calendar.
