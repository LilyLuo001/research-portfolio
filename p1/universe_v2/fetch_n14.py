"""Rebuild the N-14 discovery spine: quarterly indexes, SGML headers, MERGER rows.

The spine is filer-declared. An N-14 registers the securities issued in a fund
reorganization, and its SGML header carries a structured MERGER block naming the
acquiring and target series by SEC identifier. Nothing here reads prose or asks a
model to judge; a pair exists because a registrant declared it in a machine
field of its own filing.

Three stages, each cached so that a rerun costs nothing it has already paid for:

  1. quarterly form indexes, to enumerate every N-14-family accession
  2. the .hdr.sgml for each, which is ~2 KB and carries the whole block
  3. the parse, which is pure and rerun every time

The header is fetched rather than the filing. A complete submission text file can
be tens of megabytes of prospectus; the header is the part that carries the
declaration, and it is two kilobytes.
"""
import collections
import re
import sys

import pandas as pd

import fetchlib
from paths import CACHE, HEADERS, INDEX

YEARS = range(2019, 2027)
IDX = "https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/form.idx"
# every N-14 variant: plain, amendments, N-14MEF, and the closed-end 8C forms.
# The 8C rows are kept deliberately -- they are out of the frozen MF->ETF scope,
# but only a count of them can show that they were excluded rather than missed.
N14 = re.compile(r"^N-14")
TAG = re.compile(r"<([A-Z0-9-]+)>\s*(.*)")


def quarters():
    out = []
    for y in YEARS:
        for q in (1, 2, 3, 4):
            p = fetchlib.get(IDX.format(y=y, q=q), INDEX / f"form_{y}Q{q}.idx",
                             kind="edgar_form_index")
            if p:
                out.append((y, q, p))
    return out


def index_rows(paths):
    """N-14-family (form, cik, date, path) from the fixed-width form indexes."""
    rows = []
    for y, q, p in paths:
        with open(p, errors="replace") as fh:
            for line in fh:
                if not N14.match(line):
                    continue
                # form.idx column widths drift between years, but the last three
                # fields never contain a space and the company name may, so the
                # only stable parse is from the right
                parts = line.rstrip().rsplit(None, 3)
                if len(parts) != 4:
                    continue
                head, cik, date, fn = parts
                form = head[:12].strip()
                if not (cik.isdigit() and fn.endswith(".txt")):
                    continue
                acc = fn.rsplit("/", 1)[-1].replace(".txt", "")
                rows.append({"form": form, "cik": int(cik), "filed": date,
                             "accession": acc, "quarter": f"{y}Q{q}"})
    return pd.DataFrame(rows)


def parse_header(path, acc, form, filed):
    """MERGER blocks from one SGML header, one row per acquiring/target pair.

    A single N-14 can carry several MERGER blocks -- one proxy often reorganizes
    a whole slate -- so the parser walks the tag stream and closes a pair each
    time a new MERGER opens, rather than assuming one block per document.
    """
    txt = open(path, errors="replace").read()
    out, cur, side = [], None, None
    for line in txt.splitlines():
        m = TAG.match(line.strip())
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "MERGER":
            if cur:
                out.append(cur)
            cur, side = collections.defaultdict(list), None
        elif tag == "ACQUIRING-DATA":
            side = "acq"
        elif tag == "TARGET-DATA":
            side = "tgt"
        elif cur is not None and side:
            if tag == "CIK":
                cur[f"{side}_cik"] = val
            elif tag == "SERIES-ID":
                cur[f"{side}_series_id"] = val
            elif tag == "SERIES-NAME":
                cur[f"{side}_series_name"] = val
            elif tag == "CLASS-CONTRACT-ID":
                cur[f"{side}_class_ids"].append(val)
            elif tag == "CLASS-CONTRACT-TICKER-SYMBOL":
                cur[f"{side}_tickers"].append(val)
    if cur:
        out.append(cur)

    rows = []
    for c in out:
        r = {"accession": acc, "form": form, "filed": filed}
        for side in ("acq", "tgt"):
            for f in ("cik", "series_id", "series_name"):
                v = c.get(f"{side}_{f}")
                v = v[0] if isinstance(v, list) else v
                # headers zero-pad the CIK; downstream joins it against N-CEN,
                # which does not, so it is normalised at the point of parsing
                r[f"{side}_{f}"] = int(v) if f == "cik" and v else v
            for f in ("class_ids", "tickers"):
                v = c.get(f"{side}_{f}") or []
                r[f"{side}_{f}"] = ";".join(v) if isinstance(v, list) else v
        rows.append(r)
    return rows


def main():
    qs = quarters()
    idx = index_rows(qs).drop_duplicates("accession")
    idx.to_csv(CACHE / "n14_index.csv", index=False)
    print(f"quarterly indexes : {len(qs)}")
    print(f"N-14-family rows  : {len(idx):,d} unique accessions", flush=True)

    ok = fail = 0
    for n, r in enumerate(idx.itertuples(index=False), 1):
        dest = HEADERS / f"{r.accession}.hdr.sgml"
        url = (f"https://www.sec.gov/Archives/edgar/data/{r.cik}/"
               f"{r.accession.replace('-', '')}/{r.accession}.hdr.sgml")
        p = fetchlib.get(url, dest, accession=r.accession, kind="n14_header")
        ok, fail = ok + (p is not None), fail + (p is None)
        if n % 200 == 0:
            print(f"  headers {n}/{len(idx)}  ok={ok} fail={fail}", flush=True)

    rows, with_block = [], 0
    for r in idx.itertuples(index=False):
        p = HEADERS / f"{r.accession}.hdr.sgml"
        if not (p.exists() and p.stat().st_size):
            continue
        got = parse_header(p, r.accession, r.form, r.filed)
        if got:
            with_block += 1
            rows.extend(got)

    m = pd.DataFrame(rows)
    out = CACHE / "n14_mergers.csv"
    m.to_csv(out, index=False)
    fetchlib.record(out, kind="derived", parser="fetch_n14.py",
                    extra={"lineage": "n14_index.csv + n14_headers/*.hdr.sgml",
                           "headers_ok": ok, "headers_failed": fail,
                           "headers_with_merger_block": with_block})

    print(f"\nheaders fetched   : {ok}  failed: {fail}")
    print(f"with MERGER block : {with_block}")
    print(f"merger rows       : {len(m):,d}")
    print(f"  both series ids : "
          f"{int((m.acq_series_id.notna() & m.tgt_series_id.notna()).sum()):,d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
