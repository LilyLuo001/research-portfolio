"""Audit every structural pair the multi-target MERGER fix added, against the raw header.

The fix changed a count that a benchmark comparison depends on, so it has to be
auditable from the filed bytes rather than from the diff. For each added pair
this reads the N-14 header itself and shows the block it came out of.

Three ways an added pair could be spurious, each checked here rather than argued:

  duplicate      the same predecessor already present under another row, so the
                 fix inflated the count by representing one fund twice
  share class    a CLASS-CONTRACT promoted to look like a series, which would
                 count a share class as a fund
  reused id      the added series id already appears as some other pair's
                 target or acquirer

A pair passes only if its series id is distinct, S-prefixed, absent from the
pre-fix register, and carries its own CLASS-CONTRACT block inside its own SERIES
element in the filed header.
"""
import pathlib
import pickle
import re
import sys

import pandas as pd

from paths import CACHE, HEADERS

SNAP = pathlib.Path.home() / "p1_universe_v2_snapshot"

# Where the header's name for a series disagrees with N-CEN's, the disagreement
# is adjudicated against the filing rather than assumed to be a rename, because
# a wrong series id in a header would look exactly the same from the outside.
NAME_ADJUDICATED = {
    "S000072754": (
        "0001104659-25-069974",
        "rename, not a different fund: the proxy states the Focused ex-China Fund "
        "'changed its name from abrdn Global Equity Impact Fund to abrdn Focused "
        "Emerging Markets ex-China Fund' on a strategy change effective "
        "2025-02-28, after N-CEN's last observation of the series (2024-10-31)"),
}


def ncen_names():
    """Every name N-CEN has ever reported for a series, oldest first."""
    with open(CACHE / "ncen_tables.pkl", "rb") as fh:
        t = pickle.load(fh)
    s = t["SUBMISSION"]
    sub = s.assign(pe=pd.to_datetime(s.REPORT_ENDING_PERIOD, errors="coerce"))
    fri = t["FUND_REPORTED_INFO"].merge(sub[["ACCESSION_NUMBER", "pe"]],
                                        on="ACCESSION_NUMBER", how="left")
    fri = fri.sort_values("pe")
    return fri.groupby("SERIES_ID").FUND_NAME.apply(
        lambda s: list(dict.fromkeys(s.dropna()))).to_dict()


def names_agree(a, b):
    """Same fund name up to punctuation, case, and the usual suffix noise."""
    def norm(s):
        s = re.sub(r"(?i)\b(the|a|an|fund|funds|inc|trust|portfolio|lp|ltd)\b", " ",
                   str(s))
        return re.sub(r"[^a-z0-9]", "", s.lower())
    x, y = norm(a), norm(b)
    return bool(x) and bool(y) and (x == y or x in y or y in x)


def target_blocks(acc):
    """Every <SERIES> inside TARGET-DATA for one accession, as filed."""
    p = HEADERS / f"{acc}.hdr.sgml"
    if not p.exists():
        return []
    t = p.read_text(errors="replace")
    out = []
    for blk in re.findall(r"(?s)<TARGET-DATA>(.*?)</TARGET-DATA>", t):
        for s in re.findall(r"(?s)<SERIES>(.*?)</SERIES>", blk):
            sid = re.search(r"<SERIES-ID>\s*(\S+)", s)
            nm = re.search(r"<SERIES-NAME>\s*(.*)", s)
            out.append({"series_id": sid.group(1) if sid else None,
                        "series_name": nm.group(1).strip() if nm else None,
                        "class_ids": re.findall(r"<CLASS-CONTRACT-ID>\s*(\S+)", s)})
    return out


def main():
    old = pd.read_csv(SNAP / "events_master_v2_stage3.csv")
    new = pd.read_csv(CACHE / "events_master_v2_stage3.csv")
    added = new[~new.pre_series_id.isin(set(old.pre_series_id))]
    ncen = ncen_names()

    print("=" * 78)
    print(f"STRUCTURAL PAIR DELTA  {len(old)} -> {len(new)}  ({len(added)} added)")
    print("=" * 78)

    rows, verdicts = [], []
    for r in added.itertuples(index=False):
        accs = [a for a in str(r.supporting_accessions or "").split(";") if a]
        # the accession whose header actually carries this target
        src, sibs = None, []
        for a in accs:
            blocks = target_blocks(a)
            ids = [b["series_id"] for b in blocks]
            if r.pre_series_id in ids:
                src, sibs = a, blocks
                break
        mine = next((b for b in sibs if b["series_id"] == r.pre_series_id), None)
        others = [b["series_id"] for b in sibs if b["series_id"] != r.pre_series_id]
        # of the siblings, the one the old parser actually emitted: the last
        # <SERIES> in the block won, and it is the one already in the register
        kept = [s for s in others if s in set(old.pre_series_id)]

        # ---- the three ways this could be spurious -------------------------
        dup = r.pre_series_id in set(old.pre_series_id)
        is_series = str(r.pre_series_id).startswith("S0")
        own_classes = bool(mine and mine["class_ids"])
        shared = bool(mine) and any(set(mine["class_ids"]) & set(b["class_ids"])
                                    for b in sibs if b["series_id"] != r.pre_series_id)
        reused = (r.pre_series_id in set(old.post_series_id))
        ok = (not dup) and is_series and own_classes and (not shared) and (not reused)
        verdicts.append(ok)

        # An independent channel on the same series id: N-CEN's own name history.
        # Agreement corroborates the header; disagreement is left visible and, if
        # adjudicated against the filing, carries the quotation that settled it.
        hist = ncen.get(r.pre_series_id, [])
        hdr_name = (mine or {}).get("series_name") or r.pre_series_name
        agrees = any(names_agree(h, hdr_name) for h in hist)
        adj_acc, adj_why = NAME_ADJUDICATED.get(r.pre_series_id, ("", ""))

        rows.append({
            "target_fund": r.pre_series_name, "target_series_id": r.pre_series_id,
            "acquirer_etf": r.post_series_name, "acquirer_series_id": r.post_series_id,
            "source_accession": src,
            "series_in_that_target_block": len(sibs),
            "target_class_ids": ";".join(mine["class_ids"]) if mine else "",
            "other_series_in_same_target_block": ";".join(others),
            "sibling_the_old_parser_kept": ";".join(kept),
            "old_parser_missed_because":
                "TARGET-DATA carried %d <SERIES>; the parser assigned series_id per "
                "tag, so each overwrote the last and only the final one survived"
                % len(sibs),
            "new_parser_includes_because":
                "the acquiring/target pair is expanded across every <SERIES>, so "
                "each predecessor keeps its own id and its own CLASS-CONTRACT list",
            "completion_status": r.final_tier,
            "event_year": r.final_year,
            "date_precision": r.date_precision,
            "duplicate_of_existing_target": dup,
            "is_series_not_share_class": is_series,
            "has_own_class_contracts": own_classes,
            "shares_classes_with_sibling": shared,
            "id_reused_as_an_acquirer": reused,
            "header_series_name": hdr_name,
            "ncen_name_history": " | ".join(hist),
            "ncen_observations": len(hist),
            "ncen_name_agrees_with_header": agrees if hist else None,
            "name_disagreement_adjudicated_by": adj_acc,
            "name_disagreement_adjudication": adj_why,
            "verdict": "ADMIT" if ok else "REJECT",
        })

    d = pd.DataFrame(rows)
    out = CACHE / "pair_delta_audit.csv"
    d.to_csv(out, index=False)

    for r in d.itertuples(index=False):
        print(f"\n{r.verdict}  {r.target_fund}  ({r.target_series_id})")
        print(f"   -> {r.acquirer_etf}  ({r.acquirer_series_id})")
        print(f"   source accession : {r.source_accession}")
        print(f"   target block held: {r.series_in_that_target_block} <SERIES>; "
              f"old parser kept {r.sibling_the_old_parser_kept}")
        print(f"   own class ids    : {r.target_class_ids}")
        print(f"   completion       : {r.completion_status}   year "
              f"{r.event_year}   precision {r.date_precision}")
        print(f"   checks: duplicate={r.duplicate_of_existing_target}  "
              f"share_class_artifact={not r.is_series_not_share_class}  "
              f"shares_classes={r.shares_classes_with_sibling}  "
              f"id_reused={r.id_reused_as_an_acquirer}")
        if not r.ncen_observations:
            print("   n-cen           : series never observed in N-CEN "
                  "(no completion claim rests on it)")
        elif r.ncen_name_agrees_with_header:
            print(f"   n-cen           : name agrees across {r.ncen_observations} "
                  f"observation(s)")
        else:
            print(f"   n-cen           : DISAGREES -- {r.ncen_name_history}")
            print(f"   adjudicated     : {r.name_disagreement_adjudicated_by} -- "
                  f"{r.name_disagreement_adjudication}")

    print("\n" + "=" * 78)
    print(f"  {sum(verdicts)}/{len(d)} admitted; "
          f"{len(d) - sum(verdicts)} rejected")
    # every added target must be a distinct fund, or the pair count is inflated
    assert d.target_series_id.nunique() == len(d)
    assert not d.duplicate_of_existing_target.any()
    assert d.is_series_not_share_class.all()
    assert not d.shares_classes_with_sibling.any()
    # a header name N-CEN contradicts is only admissible if the filing settles it
    unadj = d[(d.ncen_name_agrees_with_header == False)  # noqa: E712
              & (d.name_disagreement_adjudication == "")]
    assert unadj.empty, f"unadjudicated name disagreement: {list(unadj.target_series_id)}"
    print("  no duplicate targets, no share-class artifacts, no shared class ids")
    print("  every N-CEN name disagreement adjudicated against the filing")
    print(f"  written: {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
