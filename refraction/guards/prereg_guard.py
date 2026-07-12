#!/usr/bin/env python3
"""
prereg_guard.py — the two Refraction project iron rules as program invariants
(执行手册 §0.2 rules 4–5; Meta-QA items ⑥–⑧). Imported, never bypassed:

  1. Prereg-before-outcomes: any script that touches post-period outcome data
     (R6 and later) calls assert_prereg_ok() at startup. It refuses to run
     unless frozen_config.yaml carries a valid OSF timestamp that lies in the
     past, and refuses while beta.w_shrink is still null (config not frozen).
  2. Lookahead ban: beta/lever/weight construction calls assert_no_lookahead()
     with the max data date actually used per (permno, wave); it raises if any
     estimation input is on/after the wave's effective date (assert A4
     semantics — machine check, not discipline).

CLI (used by runner briefs and the R14 Meta-QA checklist):
  python prereg_guard.py check <path/to/frozen_config.yaml>
      exit 0 = post-outcome estimation is legal now; exit 1 = blocked (reason printed)
  python prereg_guard.py status <path/to/frozen_config.yaml>
      never fails; prints a one-line status for the digest
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


class PreregError(RuntimeError):
    """Raised when post-period outcome estimation is attempted illegally."""


class LookaheadError(RuntimeError):
    """Raised when pre-period constructions use data at/after a wave effective date."""


@dataclass
class PreregStatus:
    ok: bool
    reason: str
    osf_timestamp: datetime | None = None


def load_config(config_path: str | Path) -> dict:
    p = Path(config_path)
    if not p.exists():
        raise PreregError(f"frozen_config not found: {p}")
    cfg = yaml.safe_load(p.read_text())
    if not isinstance(cfg, dict):
        raise PreregError(f"frozen_config is not a mapping: {p}")
    return cfg


def _parse_ts(raw) -> datetime:
    if isinstance(raw, datetime):
        ts = raw
    else:
        try:
            ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError as e:
            raise PreregError(f"prereg.osf_timestamp is not RFC3339/ISO8601: {raw!r}") from e
    if ts.tzinfo is None:
        # An unzoned timestamp is ambiguous evidence; reject rather than guess.
        raise PreregError(f"prereg.osf_timestamp must carry a timezone: {raw!r}")
    return ts


def prereg_status(config_path: str | Path, now: datetime | None = None) -> PreregStatus:
    """Evaluate whether post-period outcome estimation is legal right now."""
    try:
        cfg = load_config(config_path)
    except PreregError as e:
        return PreregStatus(False, str(e))
    prereg = cfg.get("prereg") or {}
    raw_ts = prereg.get("osf_timestamp")
    if raw_ts in (None, "", "null"):
        return PreregStatus(False, "prereg.osf_timestamp is empty — OSF registration "
                                   "not committed (REFR-GATE-OSF has not passed)")
    try:
        ts = _parse_ts(raw_ts)
    except PreregError as e:
        return PreregStatus(False, str(e))
    if not prereg.get("osf_url"):
        return PreregStatus(False, "prereg.osf_url is empty — timestamp without the "
                                   "registration URL is not acceptable evidence", ts)
    beta = cfg.get("beta") or {}
    if beta.get("w_shrink") is None:
        return PreregStatus(False, "beta.w_shrink is null — config was not frozen at "
                                   "GATE-PREREG; R6 must not run on an unfrozen config", ts)
    now = now or datetime.now(timezone.utc)
    if now <= ts:
        return PreregStatus(False, f"system time {now.isoformat()} is not after the OSF "
                                   f"timestamp {ts.isoformat()}", ts)
    return PreregStatus(True, "ok", ts)


def assert_prereg_ok(config_path: str | Path, now: datetime | None = None) -> PreregStatus:
    """Hard gate for R6/R7-post/R8/R10-stage2: raise PreregError if illegal."""
    st = prereg_status(config_path, now=now)
    if not st.ok:
        raise PreregError(f"prereg-before-outcomes violated: {st.reason}")
    return st


def assert_no_lookahead(max_data_date, wave_effective_date, *, what: str = "estimation input",
                        permno=None, wave=None) -> None:
    """A4 semantics: the latest date used to build a pre-period quantity must be
    STRICTLY before the wave effective date. Dates may be datetime/date/ISO strings."""
    def _d(x):
        if hasattr(x, "date") and not isinstance(x, str):
            x = x.date() if isinstance(x, datetime) else x
        if isinstance(x, str):
            x = datetime.fromisoformat(x).date()
        return x
    mx, eff = _d(max_data_date), _d(wave_effective_date)
    if mx >= eff:
        ctx = f" permno={permno}" if permno is not None else ""
        ctx += f" wave={wave}" if wave is not None else ""
        raise LookaheadError(
            f"lookahead ban violated:{ctx} {what} uses data dated {mx} "
            f">= wave effective date {eff}")


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"check", "status"}:
        print(__doc__)
        return 2
    cmd, path = argv[1], argv[2]
    st = prereg_status(path)
    line = f"{'PASS' if st.ok else 'BLOCKED'}: {st.reason}"
    print(line)
    if cmd == "check":
        return 0 if st.ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
