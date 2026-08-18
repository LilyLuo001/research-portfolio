"""Build dax/data_built/cps_onet_crosswalk.csv — employment-weighted, many-to-many.

Reassigned from seat A on 2026-08-18 by PI instruction; see
`ops/briefs/ASSIGNMENTS-2026-08-14.md`.

WHAT THIS PRODUCES
------------------
For each CPS occupation code `c`, the set of O*NET-SOC codes `o` it covers and
a weight `w(c, o)` summing to one across `o`. The DAX index is constructed at
O*NET task level, so dose reaches a CPS respondent as
`DAX_c = sum_o w(c, o) * DAX_o`. The crosswalk is therefore not bookkeeping —
it is the operator that turns the index into treatment, and its dispersion is
measurement error in the regressor.

THE CHAIN AND ITS ONE ASSUMPTION
--------------------------------
    CPS occ --(Census)--> SOC --(O*NET taxonomy)--> O*NET-SOC
    weights: OEWS national employment

OEWS publishes employment at SOC, not at O*NET-SOC detail. When one SOC maps to
several O*NET-SOC codes there is no published basis for splitting it, so this
build splits SOC employment **equally** among its O*NET-SOC children and
records `split_rule` on every row. That is an assumption, not a measurement.
It is surfaced rather than buried because it directly inflates or deflates
`max_crosswalk_weight`, which drives the Decision 12 low-quality flag.

DECISION 12 DIAGNOSTICS
-----------------------
`max_crosswalk_weight` is computable from the crosswalk alone and is emitted
here. `dose_sd_within_cps` needs doses, which do not exist until W3 mappings
land, so it ships blank and `attach_dose_dispersion` fills it later. The column
exists from the start so downstream code never has to reshape the file.

    python dax/w2/crosswalk/build_crosswalk.py --fetch     # needs egress
    python dax/w2/crosswalk/build_crosswalk.py             # build from cache
"""

from __future__ import annotations

import argparse
import collections
import csv
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "ops" / "runner"))

import sources                                      # noqa: E402
from lineage import write_lineage                   # noqa: E402

OUTPUT = REPO / "dax" / "data_built" / "cps_onet_crosswalk.csv"
COVERAGE = REPO / "dax" / "data_built" / "crosswalk_coverage_report.md"

FIELDS = [
    "cps_occ", "onet_soc", "soc", "weight", "employment",
    "n_targets", "max_crosswalk_weight", "dose_sd_within_cps",
    "split_rule", "coverage_status",
]

EQUAL_SPLIT = "soc_employment_split_equally_across_onet_children"


def build_edges(
    census_edges: list[tuple[str, str]],
    onet_edges: list[tuple[str, str]],
    soc_employment: dict[str, float],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Pure crosswalk construction. No I/O, so it is testable without the files.

    census_edges: (cps_occ, soc)      onet_edges: (soc, onet_soc)
    """
    onet_children: dict[str, list[str]] = collections.defaultdict(list)
    for soc, onet_soc in onet_edges:
        if onet_soc not in onet_children[soc]:
            onet_children[soc].append(onet_soc)

    # Agency spreadsheets repeat rows (one census code appears once per SOC
    # detail line, and vintages carry duplicate header blocks). Left as-is, a
    # repeated edge emits a duplicate primary key AND counts that SOC's
    # employment twice, which silently distorts every weight in the code.
    seen: set[tuple[str, str]] = set()
    census_edges = [edge for edge in census_edges
                    if not (edge in seen or seen.add(edge))]

    by_cps: dict[str, list[dict[str, object]]] = collections.defaultdict(list)
    unmapped_soc: set[str] = set()
    soc_without_employment: set[str] = set()

    for cps_occ, soc in census_edges:
        children = onet_children.get(soc)
        if not children:
            unmapped_soc.add(soc)
            continue
        employment = soc_employment.get(soc)
        if employment is None:
            soc_without_employment.add(soc)
            employment = 0.0
        share = float(employment) / len(children)
        for onet_soc in children:
            by_cps[cps_occ].append({
                "cps_occ": cps_occ, "onet_soc": onet_soc, "soc": soc,
                "employment": round(share, 4),
            })

    rows: list[dict[str, object]] = []
    zero_employment_cps: list[str] = []
    for cps_occ in sorted(by_cps):
        targets = by_cps[cps_occ]
        total = sum(float(t["employment"]) for t in targets)
        if total > 0:
            for target in targets:
                target["weight"] = float(target["employment"]) / total
            status = "ok"
        else:
            # Every target has zero or missing employment. Falling back to
            # equal weights keeps the occupation in the panel instead of
            # silently dropping it, but the row says so.
            for target in targets:
                target["weight"] = 1.0 / len(targets)
            status = "equal_weight_fallback_no_employment"
            zero_employment_cps.append(cps_occ)

        max_weight = max(float(t["weight"]) for t in targets)
        for target in targets:
            rows.append({
                **target,
                "weight": round(float(target["weight"]), 8),
                "n_targets": len(targets),
                "max_crosswalk_weight": round(max_weight, 8),
                "dose_sd_within_cps": "",       # needs W3 doses
                "split_rule": EQUAL_SPLIT,
                "coverage_status": status,
            })

    diagnostics = {
        "cps_codes": len(by_cps),
        "rows": len(rows),
        "soc_with_no_onet_child": sorted(unmapped_soc),
        "soc_with_no_employment": sorted(soc_without_employment),
        "cps_with_equal_weight_fallback": sorted(zero_employment_cps),
        "cps_flagged_low_max_weight": sorted(
            {str(r["cps_occ"]) for r in rows
             if float(r["max_crosswalk_weight"]) < 0.50}),
    }
    return rows, diagnostics


def attach_dose_dispersion(
    rows: list[dict[str, object]], onet_dose: dict[str, float]
) -> int:
    """Fill Decision 12's `dose_sd_within_cps` once W3 doses exist.

    The weighted standard deviation of O*NET dose within each CPS code. Paired
    with `max_crosswalk_weight`, it drives the low-quality flag (SD > 0.10 or
    max weight < 0.50) without anyone re-deriving it downstream.
    """
    grouped: dict[str, list[tuple[float, float]]] = collections.defaultdict(list)
    for row in rows:
        dose = onet_dose.get(str(row["onet_soc"]))
        if dose is not None:
            grouped[str(row["cps_occ"])].append((float(row["weight"]), dose))

    dispersion: dict[str, str] = {}
    for cps_occ, pairs in grouped.items():
        total = sum(weight for weight, _ in pairs)
        if total <= 0 or len(pairs) < 2:
            dispersion[cps_occ] = ""
            continue
        mean = sum(weight * dose for weight, dose in pairs) / total
        variance = sum(weight * (dose - mean) ** 2 for weight, dose in pairs) / total
        dispersion[cps_occ] = f"{statistics.sqrt(variance):.8f}"

    filled = 0
    for row in rows:
        value = dispersion.get(str(row["cps_occ"]), "")
        if value:
            row["dose_sd_within_cps"] = value
            filled += 1
    return filled


# --- parsers ---------------------------------------------------------------
# Kept thin and separate so the pure logic above is testable without the real
# files, which are large agency spreadsheets that cannot be fetched here.

def parse_census_crosswalk(path: pathlib.Path) -> list[tuple[str, str]]:
    import pandas as pd
    frame = pd.read_excel(path, dtype=str).fillna("")
    columns = {c.lower().strip(): c for c in frame.columns}
    occ_col = next((columns[c] for c in columns if "census" in c and "code" in c), None)
    soc_col = next((columns[c] for c in columns if "soc" in c and "code" in c), None)
    if occ_col is None or soc_col is None:
        raise SystemExit(
            "NEED_HUMAN: could not identify the census-occ and SOC columns in "
            f"{path.name}. Columns present: {list(frame.columns)}. The Census "
            "layout changes between vintages; map it explicitly rather than "
            "guessing, and record the mapping here."
        )
    edges = []
    for _, record in frame.iterrows():
        occ, soc = str(record[occ_col]).strip(), str(record[soc_col]).strip()
        if occ and soc and not occ.lower().startswith("census"):
            edges.append((occ, soc))
    return edges


def parse_onet_taxonomy(path: pathlib.Path) -> list[tuple[str, str]]:
    edges = []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for record in csv.DictReader(handle):
            key = next((k for k in record if k and "o*net-soc" in k.lower()
                        and "code" in k.lower()), None)
            if key is None:
                raise SystemExit(
                    "NEED_HUMAN: no O*NET-SOC code column in "
                    f"{path.name}; found {list(record)}")
            onet_soc = (record[key] or "").strip()
            if onet_soc:
                edges.append((onet_soc.split(".")[0], onet_soc))
    return edges


def parse_oews(path: pathlib.Path) -> dict[str, float]:
    import io
    import zipfile

    import pandas as pd

    with zipfile.ZipFile(path) as archive:
        name = next((n for n in archive.namelist()
                     if n.lower().endswith((".xlsx", ".xls"))), None)
        if name is None:
            raise SystemExit(f"NEED_HUMAN: no spreadsheet inside {path.name}")
        frame = pd.read_excel(io.BytesIO(archive.read(name)), dtype=str)
    columns = {c.lower().strip(): c for c in frame.columns}
    soc_col = columns.get("occ_code")
    emp_col = columns.get("tot_emp")
    if soc_col is None or emp_col is None:
        raise SystemExit(
            f"NEED_HUMAN: OEWS layout changed; columns are {list(frame.columns)}")
    employment: dict[str, float] = {}
    for _, record in frame.iterrows():
        soc = str(record[soc_col]).strip()
        raw = str(record[emp_col]).replace(",", "").strip()
        try:
            value = float(raw)
        except ValueError:
            continue          # '**' and '*' mark suppressed cells; skip, never zero-fill
        if soc:
            employment[soc] = value
    return employment


def write_coverage(diagnostics: dict[str, object], receipt: dict[str, object] | None) -> None:
    lines = [
        "# CPS to O*NET-SOC crosswalk — coverage",
        "",
        f"CPS occupation codes mapped: **{diagnostics['cps_codes']}** "
        f"across **{diagnostics['rows']}** edges.",
        "",
        "## Decision 12 inputs",
        "",
        f"- CPS codes with `max_crosswalk_weight` below 0.50: "
        f"**{len(diagnostics['cps_flagged_low_max_weight'])}** — these are "
        "already low-quality on the mapping-concentration criterion before any "
        "dose is computed.",
        "- `dose_sd_within_cps` is blank until W3 mappings produce doses; "
        "`attach_dose_dispersion` fills it without reshaping the file.",
        "",
        "## Gaps, reported rather than filled",
        "",
        f"- SOC codes with no O*NET-SOC child: {len(diagnostics['soc_with_no_onet_child'])}",
        f"- SOC codes with no OEWS employment (suppressed or absent): "
        f"{len(diagnostics['soc_with_no_employment'])}",
        f"- CPS codes falling back to equal weights: "
        f"{len(diagnostics['cps_with_equal_weight_fallback'])}",
        "",
        "Suppressed OEWS cells are skipped, never zero-filled. A CPS code whose "
        "targets all lack employment keeps equal weights and is labelled "
        "`equal_weight_fallback_no_employment` on every row, so downstream code "
        "can exclude it rather than inheriting a fabricated weighting.",
        "",
        "## The split assumption",
        "",
        "OEWS publishes employment at SOC, not O*NET-SOC. Where one SOC has "
        "several O*NET-SOC children its employment is split **equally**; there "
        "is no published basis for any other split. Every row carries "
        f"`split_rule = {EQUAL_SPLIT}`. This assumption moves "
        "`max_crosswalk_weight` directly and therefore moves the Decision 12 "
        "flag, so it is a first-class caveat, not a footnote.",
        "",
        "## Source provenance",
        "",
    ]
    if receipt:
        for key, entry in receipt["files"].items():
            lines.append(f"- `{key}` — {entry['agency']}, {entry['vintage']}, "
                         f"sha256 `{entry['sha256'][:16]}…`")
    else:
        lines.append("- **no fetch receipt** — built from an unverified cache.")
    COVERAGE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true",
                        help="download the three public sources first (needs egress)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.fetch:
        sources.fetch_all(REPO, force=args.force)

    problems = sources.verify_cache(REPO)
    if problems:
        print("cannot build — source cache is not verified:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("\nRun with --fetch on a host with egress to www2.census.gov, "
              "www.onetcenter.org and www.bls.gov.", file=sys.stderr)
        return 1

    receipt = sources.load_receipt(REPO)
    raw = sources.raw_dir(REPO)
    census_edges = parse_census_crosswalk(raw / "census_2018_occ_crosswalk.xlsx")
    onet_edges = parse_onet_taxonomy(raw / "onet_2019_occupations.csv")
    employment = parse_oews(raw / "oesm21nat.zip")

    rows, diagnostics = build_edges(census_edges, onet_edges, employment)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    write_coverage(diagnostics, receipt)
    write_lineage(str(OUTPUT), [], extra={
        "sources": receipt["files"] if receipt else None,
        "diagnostics": {k: (len(v) if isinstance(v, list) else v)
                        for k, v in diagnostics.items()},
        "note": "no language model is involved in producing any value in this file",
    })
    print(f"wrote {OUTPUT.relative_to(REPO)} — {len(rows)} edges over "
          f"{diagnostics['cps_codes']} CPS codes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
