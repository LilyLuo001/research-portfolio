#!/usr/bin/env python3
"""
stage0_discover.py — the first program this module runs on the SCC.

Its whole job is to REPLACE assumption with observation. It reads the archive's
own manifest, resolves the files this bounded task actually needs, and reports
each file's real Parquet schema and row count. It never loads a data row, never
concatenates anything, and never asserts a column exists — it discovers which
columns exist and writes that down.

That distinction is the point. The data-usage manual is an inventory
orientation, not a guarantee of any field; CLAUDE.md meta-rule 1 says a number
that did not come from code run on real data is a hallucination. So no later
stage of this module may name a column that stage 0 did not observe.

  python stage0_discover.py --out <dir> [--archive <root>] [--config <path>]

Outputs (both with a lineage JSON beside them):
  <out>/source_catalog.tsv   one row per (logical_family, file) actually found
  <out>/stage0_report.json   run summary, migration-verification status, and the
                             capability flags that gate stages 1-5

Exit codes:  0 ok · 2 usage/config error · 3 NEED_HUMAN (archive unreachable)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops" / "runner"))
from lineage import write_lineage  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.yaml"

# Columns whose presence decides whether a later stage is runnable at all. Each
# maps to the stage that consumes it, so a missing one reads as a named blocker
# rather than a mystery. Checked case-insensitively against observed schemas.
#
# `mode` matters: "any" means the columns are alternatives that would each serve
# (a value-weighted market return is a value-weighted market return whether it
# carries distributions or not), "all" means every one is separately required
# (an effective-dated link without `score` cannot be quality-filtered).
CAPABILITY_COLUMNS = {
    "crsp_dsi": {
        "columns": ["vwretd", "vwretx"], "mode": "any",
        "gates": "3A original-style Hou-Moskowitz benchmark"},
    "crsp_holdings": {
        "columns": ["percent_tna"], "mode": "all",
        "gates": "2 portfolio weights"},
    "ibes_actuals": {
        "columns": ["anntims"], "mode": "all",
        "gates": "1 earnings session classification (timezone still UNVERIFIED)"},
    "crsp_ibes_link": {
        "columns": ["sdate", "edate", "score"], "mode": "all",
        "gates": "1 effective-dated CRSP-I/B/E/S link"},
}


# --------------------------------------------------------------------------
# preflight
# --------------------------------------------------------------------------
def preflight_write(outdir: pathlib.Path) -> None:
    """Prove the output filesystem accepts a write before any computation.

    The instruction asks for this explicitly: discovering at the end of a long
    scan that the output directory is read-only wastes the scan.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    probe = outdir / ".write_probe"
    token = f"stage0 {datetime.now(timezone.utc).isoformat()}"
    probe.write_text(token)
    if probe.read_text() != token:
        raise OSError(f"write probe did not read back intact at {probe}")
    probe.unlink()


def resolve_archive(cfg: dict, override: str | None) -> dict:
    arch = cfg["archive"]
    root = pathlib.Path(override or arch["root"]).expanduser()
    return {
        "root": root,
        "project": root / arch["project_subdir"],
        "meta": root / arch["migration_meta_subdir"],
        "manifest": root / arch["migration_meta_subdir"] / arch["manifest"],
        "verify_reports": arch.get("verify_reports", []),
    }


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------
def read_manifest(path: pathlib.Path) -> list[tuple[int, str]]:
    """Parse `<byte_size><TAB><relative_path>`, tolerating blanks and stray CR.

    A malformed line is skipped rather than guessed at, and the count of skipped
    lines is reported so a badly parsed manifest cannot pass as a clean one.
    """
    rows, skipped = [], 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2 or not parts[0].strip().isdigit():
                skipped += 1
                continue
            rows.append((int(parts[0].strip()), "\t".join(parts[1:]).strip()))
    read_manifest.skipped = skipped  # type: ignore[attr-defined]
    return rows


def resolve_rel(rel: str, bases: list[pathlib.Path]) -> tuple[pathlib.Path | None, str | None]:
    """Find which base a manifest-relative path actually hangs off.

    The manifest records relative paths without stating their base, so rather
    than assume one, try each candidate and record which resolved. A path that
    resolves under none is reported unresolved, never silently dropped.
    """
    rel_clean = rel.lstrip("./")
    for base in bases:
        cand = base / rel_clean
        if cand.exists():
            return cand, str(base)
    return None, None


def read_verify_reports(meta: pathlib.Path, names: list[str]) -> dict:
    """Read, do not re-run, the migration verification the archive already did.

    Restarting a whole-archive checksum exercise is out of scope for this task;
    reporting that it was never finished is not.
    """
    keys = ("PATH_SIZE_CHECK", "PARQUET_COUNT_CHECK",
            "CHECKSUM_CHECK", "SAFE_TO_DELETE_WRDS")
    out = {}
    for name in names:
        p = meta / name
        rec: dict = {"present": p.exists()}
        if p.exists():
            text = p.read_text(errors="replace")
            rec["bytes"] = p.stat().st_size
            rec["statuses"] = {
                k: (m.group(1).strip() if (m := re.search(rf"{k}\s*=\s*(\S+)", text)) else None)
                for k in keys
            }
            rec["head"] = text[:1200]
        out[name] = rec
    return out


# --------------------------------------------------------------------------
# family matching
# --------------------------------------------------------------------------
def match_families(manifest: list[tuple[int, str]], families: dict) -> list[dict]:
    """One manifest pass; a file matching two families yields two rows.

    Deliberately not de-duplicated to a single "best" family: a file that looks
    like both a legacy and a CIZ daily file is exactly the overlap the archive
    warns about, and hiding it behind a winner-takes-all rule would erase the
    signal that a human needs to adjudicate.
    """
    compiled = {}
    for fam, spec in families.items():
        pats = [re.compile(p, re.I) for p in spec.get("patterns", [])]
        excl = [re.compile(p, re.I) for p in spec.get("exclude", [])]
        compiled[fam] = (pats, excl, spec.get("needed_for", ""))

    hits = []
    for nbytes, rel in manifest:
        for fam, (pats, excl, why) in compiled.items():
            if any(p.search(rel) for p in pats) and not any(e.search(rel) for e in excl):
                hits.append({"logical_family": fam, "manifest_path": rel,
                             "bytes": nbytes, "needed_for": why})
    return hits


def stage_of(rel: str) -> str:
    """Which download stage a file came from — provenance the manual requires."""
    for stage in ("rescue_remaining", "rescue", "maximal", "meta"):
        if f"/{stage}/" in rel or rel.startswith(f"{stage}/"):
            return stage
    return "raw_or_other"


def partition_hint(rel: str) -> str:
    """A STORAGE hint only. Never an economic date (manual §44)."""
    name = pathlib.PurePosixPath(rel).name
    if m := re.search(r"_(\d{4})_(\d{2})\.parquet$", name):
        return f"month:{m.group(1)}-{m.group(2)}"
    if m := re.search(r"_b(\d{4})", name):
        return f"portfolio_batch:{m.group(1)}"
    if m := re.search(r"part_(\d+)\.parquet$", name):
        return f"part:{int(m.group(1))}"
    if m := re.search(r"_(\d{4})\.parquet$", name):
        return f"year:{m.group(1)}"
    return "none"


# --------------------------------------------------------------------------
# parquet metadata (footer only — no data rows are read)
# --------------------------------------------------------------------------
def parquet_metadata(path: pathlib.Path) -> dict:
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    md, schema = pf.metadata, pf.schema_arrow
    cols = list(schema.names)
    sig = "|".join(f"{n}:{schema.field(n).type}" for n in cols)
    return {
        "n_rows": md.num_rows,
        "n_columns": len(cols),
        "n_row_groups": md.num_row_groups,
        "columns": cols,
        "schema_sha1": hashlib.sha1(sig.encode()).hexdigest()[:12],
    }


def build_catalog(hits: list[dict], bases: list[pathlib.Path],
                  progress_every: int = 200) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    counts = {"resolved": 0, "unresolved": 0, "parquet_read": 0, "parquet_error": 0}
    t0 = time.time()

    for i, hit in enumerate(hits, 1):
        rel = hit["manifest_path"]
        abspath, base = resolve_rel(rel, bases)
        row = dict(hit)
        row.update({
            "resolved": bool(abspath),
            "resolved_base": base or "",
            "source_download_stage": stage_of(rel),
            "partition_hint": partition_hint(rel),
            "n_rows": "", "n_columns": "", "n_row_groups": "",
            "schema_sha1": "", "columns_csv": "", "read_error": "",
        })
        if abspath:
            counts["resolved"] += 1
            if abspath.suffix == ".parquet":
                try:
                    meta = parquet_metadata(abspath)
                    row.update({
                        "n_rows": meta["n_rows"],
                        "n_columns": meta["n_columns"],
                        "n_row_groups": meta["n_row_groups"],
                        "schema_sha1": meta["schema_sha1"],
                        "columns_csv": ",".join(meta["columns"]),
                    })
                    counts["parquet_read"] += 1
                except Exception as e:  # a corrupt footer is a finding, not a crash
                    row["read_error"] = f"{type(e).__name__}: {e}"[:200]
                    counts["parquet_error"] += 1
        else:
            counts["unresolved"] += 1

        rows.append(row)
        if progress_every and i % progress_every == 0:
            print(f"  ... {i}/{len(hits)} files inspected "
                  f"({time.time() - t0:.0f}s)", flush=True)

    counts["elapsed_s"] = round(time.time() - t0, 1)
    return rows, counts


# --------------------------------------------------------------------------
# roll-up
# --------------------------------------------------------------------------
def summarise(rows: list[dict], families: dict) -> dict:
    """Per-family totals plus the capability flags that gate stages 1-5."""
    out = {}
    for fam in families:
        frows = [r for r in rows if r["logical_family"] == fam]
        found = [r for r in frows if r["resolved"]]
        observed: set[str] = set()
        for r in found:
            if r["columns_csv"]:
                observed |= {c.strip().lower() for c in r["columns_csv"].split(",")}
        n_rows_total = sum(int(r["n_rows"]) for r in found if r["n_rows"] != "")

        rec = {
            "n_manifest_hits": len(frows),
            "n_resolved": len(found),
            "n_parquet_with_metadata": sum(1 for r in found if r["n_rows"] != ""),
            "n_rows_total": n_rows_total,
            "schema_variants": sorted({r["schema_sha1"] for r in found if r["schema_sha1"]}),
            "download_stages": sorted({r["source_download_stage"] for r in found}),
            "needed_for": families[fam].get("needed_for", ""),
        }
        if fam in CAPABILITY_COLUMNS:
            spec = CAPABILITY_COLUMNS[fam]
            wanted, mode = spec["columns"], spec["mode"]
            present = [c for c in wanted if c in observed]
            rec["capability"] = {
                "gates": spec["gates"],
                "columns_wanted": wanted,
                "match_mode": mode,
                "columns_observed": present,
                "columns_missing": [c for c in wanted if c not in observed],
                # Absence here is a real blocker to name, not a reason to
                # substitute a convenient column with a similar meaning.
                "satisfied": bool(found) and (bool(present) if mode == "any"
                                              else len(present) == len(wanted)),
            }
        out[fam] = rec
    return out


def write_tsv(path: pathlib.Path, rows: list[dict], cols: list[str]) -> None:
    def cell(v):
        return str(v).replace("\t", " ").replace("\n", " ")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(cell(r.get(c, "")) for c in cols) + "\n")


CATALOG_COLUMNS = [
    "logical_family", "manifest_path", "resolved", "resolved_base",
    "source_download_stage", "partition_hint", "bytes",
    "n_rows", "n_columns", "n_row_groups", "schema_sha1",
    "columns_csv", "read_error", "needed_for",
]


# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="output directory (write-tested first)")
    ap.add_argument("--archive", default=None,
                    help="override the archive root (else $P1_WRDS_ARCHIVE, else config)")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--progress-every", type=int, default=200)
    args = ap.parse_args(argv)

    cfg_path = pathlib.Path(args.config)
    if not cfg_path.exists():
        print(f"UNKNOWN: no config at {cfg_path}", file=sys.stderr)
        return 2
    cfg = yaml.safe_load(cfg_path.read_text())

    import os
    arch = resolve_archive(cfg, args.archive or os.environ.get("P1_WRDS_ARCHIVE"))
    outdir = pathlib.Path(args.out)

    preflight_write(outdir)
    print(f"write probe OK -> {outdir}")

    if not arch["manifest"].exists():
        # CLAUDE.md meta-rule 4: don't know -> stop. Never fabricate a catalog.
        print(f"NEED_HUMAN: manifest not readable at {arch['manifest']}. "
              f"Archive root tried: {arch['root']}. This session cannot see the "
              f"WRDS mirror; nothing downstream may proceed.", file=sys.stderr)
        return 3

    manifest = read_manifest(arch["manifest"])
    skipped = getattr(read_manifest, "skipped", 0)
    print(f"manifest: {len(manifest)} entries ({skipped} unparseable lines skipped)")

    verify = read_verify_reports(arch["meta"], arch["verify_reports"])
    for name, rec in verify.items():
        print(f"verify report {name}: "
              + ("absent" if not rec["present"] else str(rec.get("statuses"))))

    families = cfg["families"]
    hits = match_families(manifest, families)
    print(f"family matches: {len(hits)} (one manifest pass, "
          f"{len(families)} families)")

    bases = [arch["root"], arch["project"]]
    rows, counts = build_catalog(hits, bases, args.progress_every)
    print(f"resolved {counts['resolved']}/{len(hits)}; "
          f"parquet footers read {counts['parquet_read']}, "
          f"errors {counts['parquet_error']}, {counts['elapsed_s']}s")

    catalog_path = outdir / "source_catalog.tsv"
    write_tsv(catalog_path, rows, CATALOG_COLUMNS)

    report = {
        "stage": "stage0_discover",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "archive_root": str(arch["root"]),
        "manifest_path": str(arch["manifest"]),
        "manifest_entries": len(manifest),
        "manifest_unparseable_lines": skipped,
        "migration_verification": verify,
        "counts": counts,
        "families": summarise(rows, families),
        # Stage 0 observes; it does not decide. The purchase recommendation is
        # made at stage 5 on empirical output, never from an inventory scan.
        "purchase_recommendation": None,
    }
    report_path = outdir / "stage0_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    for p in (catalog_path, report_path):
        write_lineage(str(p), [str(arch["manifest"]), str(cfg_path)])

    print("\ncapability gates observed from real schemas:")
    for fam, rec in report["families"].items():
        if "capability" in rec:
            cap = rec["capability"]
            detail = (f"observed={cap['columns_observed']}" if cap["satisfied"]
                      else f"missing={cap['columns_missing']} "
                           f"({cap['match_mode']}-of {cap['columns_wanted']})")
            print(f"  {fam:16s} {'OK     ' if cap['satisfied'] else 'BLOCKED'} "
                  f"{detail}  (gates §{cap['gates']})")

    print(f"\nwrote {catalog_path}\nwrote {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
