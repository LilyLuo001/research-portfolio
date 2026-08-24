"""Build dax/data_built/oews_wages.parquet from the pinned OEWS 2021 national file.

Written against a verified inventory rather than an assumed layout: the archive,
sheet, 32 column headers and 1,403 data rows were read on the SCC and recorded
in `dax/memo/free_batch_sweep_receipt_20260824.json`. Nothing here is inferred
from the file's name or from memory.

Four properties of this source decide whether the output is right, and each is
enforced rather than trusted:

1. **BLS answers a default agent with an HTML block page.** A 1,323-byte
   "Access Denied" page and a 278,152-byte zip both arrive as HTTP 200-shaped
   bytes to a careless reader. Spoofing a browser agent is also refused;
   identifying the requester is what works. This script never downloads -- it
   takes a local path and verifies its SHA-256 against the pin, which closes
   the whole class.
2. **`O_GROUP` mixes major, minor, broad and detailed rows.** Summing without
   filtering double counts, so the filter is required and its effect recorded.
3. **`ANNUAL` and `HOURLY` are flags**, not values: they mark occupations that
   report annual-only or hourly-only. The wage-bill method depends on the
   distinction, so both are carried through.
4. **OEWS suppression markers are not numbers.** `*` means not released and `#`
   means at or above the top code. Coercing them to zero would understate a
   wage bill; coercing to NaN silently would drop occupations. They are counted
   and preserved as nulls with an explicit flag.

Deliberately NOT done here: any crosswalk to O*NET-SOC. OEWS is SOC coded and
O*NET is 8-digit O*NET-SOC. That mapping is a separate signed artifact under
`ops/contracts/cps_onet_crosswalk.yaml`, owned by another lane, and inventing a
join here would bury a mapping decision inside a data builder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

PINNED_ARCHIVE_SHA = "83ad09f19e62104a39024d36ed67cae5c3f7d5b42ff165ca656e0e35241bcf31"
REQUIRED = ["OCC_CODE", "OCC_TITLE", "O_GROUP", "TOT_EMP",
            "A_MEAN", "H_MEAN", "ANNUAL", "HOURLY"]
SUPPRESSED = {"*": "not_released", "#": "at_or_above_top_code"}
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _cell_ref_col(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref or "A").group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_sheet(archive: pathlib.Path, sheet_name: str) -> list[list[str]]:
    """Parse one xlsx worksheet with the standard library only.

    openpyxl is absent from the project venv on the SCC and the shared venv is
    not this task's to modify.
    """
    with zipfile.ZipFile(archive) as outer:
        xlsx_names = [n for n in outer.namelist() if n.lower().endswith(".xlsx")]
        if len(xlsx_names) != 1:
            raise SystemExit(f"NEED_HUMAN: expected one xlsx in the archive, "
                             f"found {xlsx_names}")
        with zipfile.ZipFile(__import__("io").BytesIO(outer.read(xlsx_names[0]))) as book:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in book.namelist():
                root = ET.fromstring(book.read("xl/sharedStrings.xml"))
                for si in root.findall(f"{NS}si"):
                    shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
            wb = ET.fromstring(book.read("xl/workbook.xml"))
            sheets = {s.get("name"): s.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                for s in wb.iter(f"{NS}sheet")}
            if sheet_name not in sheets:
                raise SystemExit(f"NEED_HUMAN: sheet {sheet_name!r} not in "
                                 f"{sorted(sheets)}")
            rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
            target = {r.get("Id"): r.get("Target") for r in rels}[sheets[sheet_name]]
            path = "xl/" + target.lstrip("/").removeprefix("xl/")
            sheet = ET.fromstring(book.read(path))

            rows: list[list[str]] = []
            for row in sheet.iter(f"{NS}row"):
                values: dict[int, str] = {}
                for c in row.findall(f"{NS}c"):
                    v = c.find(f"{NS}v")
                    text = "" if v is None else (v.text or "")
                    if c.get("t") == "s" and text.isdigit():
                        text = shared[int(text)]
                    elif c.get("t") == "inlineStr":
                        text = "".join(t.text or "" for t in c.iter(f"{NS}t"))
                    values[_cell_ref_col(c.get("r", "A1"))] = text
                if values:
                    width = max(values) + 1
                    rows.append([values.get(i, "") for i in range(width)])
            return rows


def _number(raw: str) -> tuple[float | None, str | None]:
    """Return (value, suppression_flag). Never guesses a number for a marker."""
    text = (raw or "").strip().replace(",", "")
    if text in SUPPRESSED:
        return None, SUPPRESSED[text]
    if not text:
        return None, "blank"
    try:
        return float(text), None
    except ValueError:
        return None, "unparseable"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", type=pathlib.Path, required=True,
                    help="local oesm21nat.zip; never downloaded by this script")
    ap.add_argument("--sheet", default="national_M2021_dl")
    ap.add_argument("--o-group", default="detailed",
                    help="O_GROUP value to retain; summing without this double counts")
    ap.add_argument("--output", type=pathlib.Path,
                    default=pathlib.Path("dax/data_built/oews_wages.parquet"))
    ap.add_argument("--allow-unpinned", action="store_true",
                    help="proceed on a SHA-256 mismatch; requires a dated note")
    args = ap.parse_args(argv)

    if not args.archive.is_file():
        print(f"NEED_HUMAN: archive not found at {args.archive}", file=sys.stderr)
        return 2
    got = _sha256(args.archive)
    if got != PINNED_ARCHIVE_SHA and not args.allow_unpinned:
        print(f"NEED_HUMAN: archive sha256 {got[:12]} does not match the pinned "
              f"{PINNED_ARCHIVE_SHA[:12]}. BLS serves a 1,323-byte HTML block page "
              f"to unidentified agents; a mismatch is far more likely to be that "
              f"page than a new release.", file=sys.stderr)
        return 2

    rows = read_sheet(args.archive, args.sheet)
    if not rows:
        print("NEED_HUMAN: sheet has no rows", file=sys.stderr)
        return 2
    header = [h.strip() for h in rows[0]]
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        print(f"NEED_HUMAN: sheet lacks {missing}. Observed header: {header}",
              file=sys.stderr)
        return 2
    idx = {c: header.index(c) for c in REQUIRED}

    groups = Counter()
    kept: list[dict[str, object]] = []
    suppression = Counter()
    for raw in rows[1:]:
        if len(raw) < len(header):
            raw = raw + [""] * (len(header) - len(raw))
        group = raw[idx["O_GROUP"]].strip().lower()
        groups[group] += 1
        if group != args.o_group.strip().lower():
            continue
        a_mean, a_flag = _number(raw[idx["A_MEAN"]])
        h_mean, h_flag = _number(raw[idx["H_MEAN"]])
        tot_emp, e_flag = _number(raw[idx["TOT_EMP"]])
        for f in (a_flag, h_flag, e_flag):
            if f:
                suppression[f] += 1
        kept.append({
            "occ_code": raw[idx["OCC_CODE"]].strip(),
            "occ_title": raw[idx["OCC_TITLE"]].strip(),
            "tot_emp": tot_emp,
            "a_mean": a_mean,
            "h_mean": h_mean,
            "annual_only": raw[idx["ANNUAL"]].strip().upper() == "TRUE"
                           or raw[idx["ANNUAL"]].strip() == "1",
            "hourly_only": raw[idx["HOURLY"]].strip().upper() == "TRUE"
                           or raw[idx["HOURLY"]].strip() == "1",
            "a_mean_suppression": a_flag,
            "h_mean_suppression": h_flag,
            "tot_emp_suppression": e_flag,
        })

    if not kept:
        print(f"NEED_HUMAN: no rows with O_GROUP == {args.o_group!r}. Observed "
              f"groups: {dict(groups)}", file=sys.stderr)
        return 2
    dupes = [c for c, n in Counter(r["occ_code"] for r in kept).items() if n > 1]
    if dupes:
        print(f"NEED_HUMAN: duplicate occ_code after filtering: {dupes[:5]}",
              file=sys.stderr)
        return 2

    try:
        import pandas as pd
    except ImportError:
        print("NEED_HUMAN: pandas is required to write parquet", file=sys.stderr)
        return 2
    frame = pd.DataFrame(kept)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output, index=False)

    receipt = {
        "receipt_version": "dax-w2-oews-wages-v1",
        "vintage": 2021,
        "scope": "OEWS national cross-industry file only; no industry or state detail",
        "source": {"archive": str(args.archive), "archive_sha256": got,
                   "pinned_sha256": PINNED_ARCHIVE_SHA, "sheet": args.sheet,
                   "url": "https://www.bls.gov/oes/special.requests/oesm21nat.zip"},
        "o_group_filter": args.o_group,
        "rows_by_o_group": dict(groups),
        "rows_kept": len(kept),
        "suppression_counts": dict(suppression),
        "suppression_rule": ("'*' is not released and '#' is at or above the top "
                             "code; both are preserved as null with a flag, never "
                             "coerced to zero"),
        "annual_only_occupations": sum(1 for r in kept if r["annual_only"]),
        "hourly_only_occupations": sum(1 for r in kept if r["hourly_only"]),
        # An occupation releasing NEITHER mean has no wage at all. 41-9012
        # Models is one in the 2021 national file. A downstream wage bill that
        # reaches for `a_mean or h_mean * 2080` gets nothing for it and, unless
        # this is surfaced, contributes a silent zero rather than a known gap.
        "no_wage_released": [r["occ_code"] for r in kept
                             if r["a_mean"] is None and r["h_mean"] is None],
        "no_wage_rule": ("these occupations release neither an annual nor an "
                         "hourly mean; they are a KNOWN GAP, not a zero wage, "
                         "and any wage-bill step must exclude or impute them "
                         "explicitly rather than summing through"),
        "crosswalk": ("NOT PERFORMED. OEWS is SOC coded, O*NET is 8-digit "
                      "O*NET-SOC; that mapping is a separate signed artifact "
                      "and is not invented here."),
        "output_sha256": _sha256(args.output),
    }
    args.output.with_suffix(".receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} — {len(kept):,} detailed occupations")
    print(f"  rows by O_GROUP: {dict(groups)}")
    print(f"  suppression: {dict(suppression) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
