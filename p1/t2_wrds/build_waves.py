#!/usr/bin/env python3
"""P1-T2 — build the conversion WAVE table from events_merged.csv.

A wave is the set of conversions sharing one effective_date (Project_1.md §52-53);
DFA's 2021-06-11 wave is the anchor. This step is data-source agnostic (pure
grouping of T1 output) so it is shared by both the WRDS path and the free
EDGAR path. No paid data, no network.

Only rows with a REAL ISO effective_date enter a wave. Held-back rows (effective
_date == 'NA', carrying only effective_date_approx) are logged and excluded — we
never assign a treated stock to an approximate date (Project_1.md §113: no
interpolation of missing holding periods; same discipline applies to timing).

  python p1/t2_wrds/build_waves.py
Output: p1/t2_wrds/waves.csv  (wave_id | effective_date | n_funds | is_anchor)
        p1/t2_wrds/waves_members.csv  (wave_id | fund_name | source_accession ...)
        p1/t2_wrds/build_waves.log
"""
import csv
import logging
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "t2_wrds"
EVENTS = ROOT / "p1" / "events_merged.csv"
WAVES = HERE / "waves.csv"
MEMBERS = HERE / "waves_members.csv"
ANCHOR = "2021-06-11"  # DFA six-fund conversion — anchor wave


def _frozen_wave_ids():
    """(effective_date -> wave_id) already committed, so ids never renumber.

    Reads the existing waves.csv. Absent (a from-scratch build) returns {} and
    numbering falls back to plain date order.
    """
    if not WAVES.exists():
        return {}
    with open(WAVES, newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["effective_date"]: r["wave_id"]
            for r in rows if r.get("effective_date") and r.get("wave_id")}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

LOGFILE = HERE / "build_waves.log"
log = logging.getLogger("build_waves")
# The run log is committed, and FileHandler(mode="w") rewrites it with fresh
# timestamps on every invocation — so the test that re-runs this script points
# BUILD_WAVES_LOG at a tmp file instead of dirtying the working tree each time
# anyone runs pytest.
LOGFILE = pathlib.Path(os.environ.get("BUILD_WAVES_LOG")
                       or (HERE / "build_waves.log"))
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(LOGFILE, mode="w")])


def _setup_run():
    """Create the output dir and attach the run log — from main(), not at import.
    The FileHandler opens build_waves.log mode="w" and that log is committed, so
    merely importing this module must not truncate it (same rule as
    p1/t2_free/build_nport_convexp.py)."""
    HERE.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(LOGFILE, mode="w")])


def main():
    _setup_run()
    if not EVENTS.exists():
        log.error("MISSING input %s — run T1 first", EVENTS)
        sys.exit(2)
    with open(EVENTS, newline="") as f:
        rows = list(csv.DictReader(f))
    log.info("read %d rows from %s", len(rows), EVENTS.name)

    dated, held = [], []
    for r in rows:
        eff = (r.get("effective_date") or "").strip()
        if ISO.match(eff):
            dated.append(r)
        else:
            held.append(r)
            log.debug("HELD (no ISO date): %s eff=%r approx=%r",
                      r.get("fund_name"), eff, r.get("effective_date_approx"))
    log.info("%d rows with ISO effective_date, %d held-back excluded",
             len(dated), len(held))

    # group by effective_date -> wave
    waves = {}
    for r in dated:
        waves.setdefault(r["effective_date"], []).append(r)
    log.info("%d distinct waves", len(waves))

    # wave_id assignment is APPEND-ONLY, and that is load-bearing.
    #
    # It used to be a plain rank over sorted dates. That is fine exactly once:
    # the moment a new event with an earlier date is added, every wave after it
    # shifts by one, and every artifact already keyed on wave_id — above all
    # p1/conv_exposure_free.parquet, which carries wave_id per cell — is
    # silently re-pointed at the wrong wave. Nothing raises. On 2026-08-27,
    # releasing the owner-gate pool added 18 waves and would have moved 36
    # existing ids.
    #
    # So: any (effective_date -> wave_id) binding already committed in waves.csv
    # is FROZEN and reused. Genuinely new dates get ids after the current max,
    # in date order. Rebuilding from scratch (no waves.csv) reproduces the
    # original numbering, so this is not a one-way door.
    ordered = sorted(waves)
    frozen = _frozen_wave_ids()
    wid = {d: frozen[d] for d in ordered if d in frozen}
    used = {int(v[1:]) for v in wid.values()}
    nxt = max(used) + 1 if used else 1
    for d in ordered:
        if d not in wid:
            while nxt in used:
                nxt += 1
            wid[d] = "W{:03d}".format(nxt)
            used.add(nxt)
    new_ids = [d for d in ordered if d not in frozen]
    if frozen:
        log.info("wave ids: %d reused from waves.csv, %d newly assigned",
                 len(ordered) - len(new_ids), len(new_ids))
        dropped = sorted(set(frozen) - set(ordered))
        if dropped:
            log.warning("%d previously-committed wave date(s) are no longer in "
                        "events_merged.csv: %s — their ids are retired, not reused",
                        len(dropped), ", ".join(dropped))
    if ANCHOR not in waves:
        log.warning("ANCHOR date %s not present as a wave — check T1 coverage",
                    ANCHOR)
    else:
        log.info("anchor wave %s = %s (%d funds)",
                 ANCHOR, wid[ANCHOR], len(waves[ANCHOR]))

    with open(WAVES, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["wave_id", "effective_date", "n_funds", "is_anchor"])
        for d in ordered:
            w.writerow([wid[d], d, len(waves[d]), int(d == ANCHOR)])

    with open(MEMBERS, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["wave_id", "effective_date", "fund_name", "family",
                    "mutual_fund_ticker", "etf_ticker", "source_accession",
                    "source_url"])
        for d in ordered:
            for r in waves[d]:
                w.writerow([wid[d], d, r.get("fund_name", ""),
                            r.get("family", ""), r.get("mutual_fund_ticker", ""),
                            r.get("etf_ticker", ""), r.get("source_accession", ""),
                            r.get("source_url", "")])

    log.info("wrote %s (%d waves) and %s (%d members)",
             WAVES.name, len(ordered), MEMBERS.name, len(dated))
    # sanity asserts (Project_1.md §112)
    assert len(ordered) == len(set(ordered)), "duplicate wave dates"
    total_members = sum(len(v) for v in waves.values())
    assert total_members == len(dated), "member count mismatch"
    log.info("OK: waves=%d funds_in_waves=%d held_back=%d",
             len(ordered), total_members, len(held))


if __name__ == "__main__":
    main()
