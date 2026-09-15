"""Pure guards for the outcome-blind event-date/session census."""
from datetime import datetime

def valid_at(link_start, link_end, announcement_date):
    """Inclusive historical-ID interval; no score selection occurs here."""
    if not announcement_date or not link_start:
        return False
    a=datetime.fromisoformat(str(announcement_date)[:10]).date()
    s=datetime.fromisoformat(str(link_start)[:10]).date()
    e=datetime.fromisoformat(str(link_end)[:10]).date() if link_end else None
    return s <= a and (e is None or a <= e)

def envelope_status(valid_link_count, parseable_date, parseable_time, timezone_known):
    if not parseable_date: return 'INVALID_ANNOUNCEMENT_DATE'
    if valid_link_count == 0: return 'MISSING_PIT_LINK'
    if valid_link_count > 1: return 'AMBIGUOUS_PIT_LINK'
    if not parseable_time: return 'TIME_UNPARSEABLE'
    if not timezone_known: return 'TIMEZONE_UNVERIFIED'
    return 'SESSION_INPUT_READY'

def session_status(envelope, calendar_open, calendar_close, exchange_timezone):
    """Fail closed: a clock string never creates an RTH/non-RTH label alone."""
    if envelope != 'SESSION_INPUT_READY': return 'NOT_CLASSIFIED_' + envelope
    if not (calendar_open and calendar_close and exchange_timezone): return 'NOT_RUN_CALENDAR_INTERVAL_UNAVAILABLE'
    return 'READY_FOR_SIGNED_SESSION_RULE'
