"""Guards on the owner-gate recheck resolution and on wave-id stability.

Three failure modes, all silent before 2026-08-27, all now loud:

  1. A verdict resting on a quote that is not in the filing. That is the
     hallucination case meta-rule 1 exists for, and the only defence is
     re-reading the quote out of the committed excerpt every time.
  2. A gated record vanishing from every output. 111 of them did.
  3. wave_id renumbering when an event is added, which re-points
     conv_exposure_free.parquet's per-cell wave_id at the wrong wave without
     raising anything.
"""
import csv
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ARB = ROOT / "p1" / "t1_arb"
sys.path.insert(0, str(ARB))


# --------------------------------------------------------------------------- #
# 1. every quote must still be in the filing                                   #
# --------------------------------------------------------------------------- #
def test_every_adjudication_quote_is_verbatim_in_the_committed_excerpt():
    """The load-bearing test. If this fails, a verdict has no evidence."""
    r = subprocess.run([sys.executable, str(ARB / "resolve_recheck.py"), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, (
        "resolve_recheck.py --check failed. A recorded quote is no longer present "
        "in the accession it cites, or the pool and the resolution file disagree "
        "about coverage.\n" + r.stdout + r.stderr)


def test_the_quote_check_actually_bites(tmp_path, monkeypatch):
    """A guard nobody has seen fail is not a guard."""
    import resolve_recheck as rr
    spec = json.loads((ARB / "recheck_resolution.json").read_text())
    victim = next(x for x in spec["resolutions"] if x["verdict"] == "event")
    doctored = dict(victim, quote=victim["quote"] + " AND THIS SENTENCE IS NOT IN THE FILING")
    spec["resolutions"] = [doctored if x is victim else x for x in spec["resolutions"]]
    p = tmp_path / "recheck_resolution.json"
    p.write_text(json.dumps(spec))
    monkeypatch.setattr(rr, "RESOLUTION", p)
    _, errors = rr.verify()
    assert any("QUOTE NOT FOUND" in e for e in errors)


def test_unresolved_rows_carry_a_reason_and_no_quote():
    """Meta-rule 4: don't know -> stop. An unresolved row must say why, and must
    not smuggle in evidence it does not have."""
    spec = json.loads((ARB / "recheck_resolution.json").read_text())
    for r in spec["resolutions"]:
        if r["verdict"] == "unresolved":
            assert r.get("reason"), f"{r['fund_name']}: unresolved with no reason"
            assert not r.get("quote"), f"{r['fund_name']}: unresolved but quotes evidence"


def test_every_gated_fund_group_has_exactly_one_resolution():
    from recheck_dossier import load_gated
    spec = json.loads((ARB / "recheck_resolution.json").read_text())
    pool = {(r["fund_name"], r["family"]) for r in load_gated()}
    resolved = [(r["fund_name"], r["family"]) for r in spec["resolutions"]]
    assert len(resolved) == len(set(resolved)), "a fund group is resolved twice"
    assert set(resolved) == pool, (
        f"coverage gap: {pool ^ set(resolved)}")


# --------------------------------------------------------------------------- #
# 2. the gate pool can never go silent again                                   #
# --------------------------------------------------------------------------- #
def test_assembly_report_accounts_for_every_gated_record():
    """Released + still-excluded must sum to the full pool, in the report."""
    from recheck_dossier import load_gated
    n_pool = len(load_gated())
    txt = (ARB / "arb_report.md").read_text()
    import re
    rel = int(re.search(r"adjudicated `event`\): \*\*(\d+)\*\* records", txt).group(1))
    exc = int(re.search(r"still excluded: \*\*(\d+)\*\* records", txt).group(1))
    assert rel + exc == n_pool, (
        f"report accounts for {rel}+{exc}={rel + exc} of {n_pool} gated records")


def test_assembly_is_reproducible():
    """assemble.py must reproduce the committed register byte for byte."""
    em = ROOT / "p1" / "events_merged.csv"
    before = em.read_bytes()
    r = subprocess.run([sys.executable, str(ARB / "assemble.py")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert em.read_bytes() == before, (
        "assemble.py did not reproduce the committed events_merged.csv — the "
        "register and its inputs have drifted apart")


# --------------------------------------------------------------------------- #
# 3. wave ids are append-only                                                  #
# --------------------------------------------------------------------------- #
def _waves():
    with open(ROOT / "p1" / "t2_wrds" / "waves.csv", newline="") as f:
        return list(csv.DictReader(f))


def test_the_dfa_anchor_wave_is_still_W002():
    """Every scenario table and the 92.8% concentration figure key on it."""
    w = {r["effective_date"]: r["wave_id"] for r in _waves()}
    assert w["2021-06-11"] == "W002"


def test_adding_an_earlier_event_does_not_renumber_existing_waves(tmp_path, monkeypatch):
    """The regression that would silently re-point conv_exposure_free.parquet.

    Insert a wave dated before every existing one and confirm every previously
    committed (date -> id) binding survives, with the newcomer taking a fresh id.
    """
    sys.path.insert(0, str(ROOT / "p1" / "t2_wrds"))
    import build_waves as bw
    before = {r["effective_date"]: r["wave_id"] for r in _waves()}

    events = tmp_path / "events_merged.csv"
    src = (ROOT / "p1" / "events_merged.csv").read_text()
    rows = list(csv.DictReader(src.splitlines()))
    early = dict(rows[0], fund_name="ZZ Synthetic Early Fund",
                 effective_date="2019-01-02", announce_date="2018-12-01")
    with events.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows + [early])

    monkeypatch.setattr(bw, "EVENTS", events)
    monkeypatch.setattr(bw, "WAVES", tmp_path / "waves.csv")
    monkeypatch.setattr(bw, "MEMBERS", tmp_path / "waves_members.csv")
    # seed the frozen registry with the committed one
    (tmp_path / "waves.csv").write_text(
        (ROOT / "p1" / "t2_wrds" / "waves.csv").read_text())
    bw.main()

    with (tmp_path / "waves.csv").open(newline="") as f:
        after = {r["effective_date"]: r["wave_id"] for r in csv.DictReader(f)}
    for date, wid in before.items():
        if date in after:
            assert after[date] == wid, (
                f"wave for {date} moved {wid} -> {after[date]}; every artifact "
                "keyed on wave_id is now pointing at the wrong wave")
    assert after["2019-01-02"] not in before.values()


def test_convexp_wave_ids_still_match_the_wave_registry():
    """conv_exposure carries wave_id per cell; it must agree with waves.csv.

    A mismatch is not automatically a bug — an event's effective date can move
    when a later-filed amendment states a new closing date, which is the frozen
    policy. But it means conv_exposure is stale for those cells and must be
    rebuilt, so the count is pinned here rather than left to be discovered.
    """
    pytest.importorskip("pandas")
    import pandas as pd
    ce = pd.read_parquet(ROOT / "p1" / "conv_exposure_free.parquet")
    reg = {r["wave_id"]: r["effective_date"] for r in _waves()}
    stale = ce[ce.wave_id.map(reg) != ce.effective_date]
    treated_stale = stale[stale.conv_exp >= 0.005]
    assert len(treated_stale) == 0, (
        f"{len(treated_stale)} TREATED cells carry a stale wave binding — the "
        "scenario tables would be wrong. Rebuild conv_exposure before using them.")
    assert len(stale) == 7, (
        f"expected 7 stale non-treated cells (Pabrai Wagons Fund, whose closing "
        f"date moved 2026-02-06 -> 2026-02-09 when its gated records were "
        f"released); found {len(stale)}. If this changed, re-audit rather than "
        "updating the number.")
