"""Upper bound on DWA-transport coverage, computed before any annotation.

The question this answers, cheaply and with no LLM call:

    If GDPval performance is transported to O*NET tasks through O*NET's own
    Detailed Work Activities rather than by direct task-to-task matching, what
    share of O*NET task mass could it possibly reach?

Direct matching produced 0 accepted pairs and 0.19% coverage because a 14-word
O*NET activity and a 276-word GDPval assignment are not the same kind of
object. The literature does not attempt that mapping: Brynjolfsson, Mitchell
and Rock (2018) score ~2,059 DWAs and aggregate to ~18,112 tasks precisely
because tasks *share DWAs across occupations*; Eloundou et al. apply their
rubric at the DWA level; Tolan et al. (JAIR 2021) use an intermediate layer
explicitly so that tasks without a matching benchmark can still be reached.

This script computes the ceiling that approach could have here. It is a bound,
not a mapping: it assumes every DWA touched by a GDPval occupation is
transportable, which is optimistic. If the bound is low, no annotation budget
can rescue the approach and that is worth knowing in an afternoon.

Emits counts only -- no task text, no prompts -- so the receipt is safe to
commit under the GDPval licence condition.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import re
import sys
import zipfile
from collections import defaultdict


def _norm(text: str) -> str:
    """Normalise an occupation title for exact comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text)


def _read_delimited(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8-sig", errors="replace")
    sample = text[:8192]
    delimiter = "\t" if sample.count("\t") >= sample.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def _members(source: pathlib.Path) -> dict[str, bytes]:
    """Return {member name: bytes} for a zip or a directory of O*NET files."""
    if source.is_dir():
        return {
            p.name: p.read_bytes()
            for p in source.rglob("*")
            if p.is_file() and p.suffix.lower() in {".txt", ".csv", ".tsv"}
        }
    with zipfile.ZipFile(source) as zf:
        return {
            pathlib.PurePath(n).name: zf.read(n)
            for n in zf.namelist()
            if pathlib.PurePath(n).suffix.lower() in {".txt", ".csv", ".tsv"}
        }


def _find(tables: dict[str, list[dict[str, str]]], *required: str) -> tuple[str, list[dict[str, str]]] | None:
    """Find the first table whose columns cover every required substring.

    O*NET release file names are not assumed. Discovery is by column content so
    a renamed or re-versioned release still works, and a miss is reported with
    the full member list rather than guessed at.
    """
    for name, rows in tables.items():
        if not rows:
            continue
        cols = [c.lower() for c in rows[0]]
        if all(any(req in c for c in cols) for req in required):
            return name, rows
    return None


def _col(row: dict[str, str], *substrings: str) -> str:
    for key in row:
        low = key.lower()
        if all(s in low for s in substrings):
            return key
    raise KeyError(f"no column matching {substrings} in {list(row)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--onet", type=pathlib.Path, required=True,
                    help="O*NET release .zip or an extracted directory")
    ap.add_argument("--gdpval-parquet", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--task-weights", type=pathlib.Path,
                    help="optional CSV with task_id and a weight column, for "
                         "wage-bill-weighted coverage")
    args = ap.parse_args(argv)

    raw = _members(args.onet)
    tables = {name: _read_delimited(blob) for name, blob in raw.items()}

    task_dwa = _find(tables, "task", "dwa")
    task_stmt = _find(tables, "task id", "o*net-soc code")
    if task_stmt is None:
        task_stmt = _find(tables, "task", "soc")
    occupations = _find(tables, "o*net-soc code", "title")

    if task_dwa is None or task_stmt is None or occupations is None:
        print("NEED_HUMAN: could not locate the required O*NET tables by column "
              "content. Members seen:", file=sys.stderr)
        for name, rows in sorted(tables.items()):
            cols = list(rows[0]) if rows else []
            print(f"  {name}: {cols[:8]}", file=sys.stderr)
        return 2

    # --- GDPval: occupations, and a schema dump to settle whether OpenAI
    # released any O*NET linkage per task (the released card lists only
    # task_id/sector/occupation/prompt/reference_files*, but verify locally).
    try:
        import pandas as pd
    except ImportError:
        print("NEED_HUMAN: pandas is required to read the GDPval parquet", file=sys.stderr)
        return 2
    gdp = pd.read_parquet(args.gdpval_parquet)
    gdp_schema = list(gdp.columns)
    onet_linkage_fields = [c for c in gdp_schema
                           if any(k in c.lower() for k in ("onet", "o*net", "dwa", "soc", "activity"))]
    gdp_occupations = sorted({str(v).strip() for v in gdp["occupation"].tolist()})

    # --- occupation title -> O*NET-SOC, exact on normalised title only.
    # Fuzzy matching here would silently inflate the bound; unmatched titles are
    # reported for human resolution instead (meta-rule 4).
    occ_rows = occupations[1]
    soc_key = _col(occ_rows[0], "o*net-soc code")
    title_key = _col(occ_rows[0], "title")
    by_title: dict[str, list[str]] = defaultdict(list)
    for row in occ_rows:
        by_title[_norm(row[title_key])].append(row[soc_key])

    matched_socs: set[str] = set()
    unmatched: list[str] = []
    for occ in gdp_occupations:
        hits = by_title.get(_norm(occ), [])
        if hits:
            matched_socs.update(hits)
        else:
            unmatched.append(occ)

    # --- task -> soc, task -> dwa
    stmt_rows = task_stmt[1]
    st_task = _col(stmt_rows[0], "task", "id")
    st_soc = _col(stmt_rows[0], "o*net-soc code")
    task_soc = {r[st_task]: r[st_soc] for r in stmt_rows}

    td_rows = task_dwa[1]
    td_task = _col(td_rows[0], "task", "id")
    td_dwa = _col(td_rows[0], "dwa", "id")
    task_dwas: dict[str, set[str]] = defaultdict(set)
    for r in td_rows:
        task_dwas[r[td_task]].add(r[td_dwa])

    # --- S: every DWA touched by a task in a GDPval occupation
    reachable_dwas: set[str] = set()
    for task_id, soc in task_soc.items():
        if soc in matched_socs:
            reachable_dwas |= task_dwas.get(task_id, set())

    all_tasks = list(task_soc)
    covered = [t for t in all_tasks if task_dwas.get(t, set()) & reachable_dwas]
    tasks_with_any_dwa = [t for t in all_tasks if task_dwas.get(t)]

    weighted = None
    if args.task_weights and args.task_weights.exists():
        with args.task_weights.open(newline="", encoding="utf-8") as fh:
            wrows = list(csv.DictReader(fh))
        if wrows:
            wk_task = _col(wrows[0], "task", "id")
            wk_val = next(k for k in wrows[0] if k != wk_task)
            weights = {r[wk_task]: float(r[wk_val] or 0) for r in wrows}
            total = sum(weights.values())
            if total > 0:
                hit = sum(weights.get(t, 0.0) for t in covered)
                weighted = hit / total

    receipt = {
        "receipt_version": "dax-w3-dwa-coverage-bound-v1",
        "interpretation": "UPPER BOUND on DWA-transport coverage; assumes every "
                          "DWA touched by a GDPval occupation is transportable",
        "sources": {
            "onet": str(args.onet),
            "onet_tables_used": {
                "task_to_dwa": task_dwa[0],
                "task_statements": task_stmt[0],
                "occupations": occupations[0],
            },
            "gdpval_parquet": str(args.gdpval_parquet),
        },
        "gdpval": {
            "schema": gdp_schema,
            "rows": int(len(gdp)),
            "onet_linkage_fields_present": onet_linkage_fields,
            "n_occupation_labels": len(gdp_occupations),
            "n_occupation_labels_matched_to_soc": len(gdp_occupations) - len(unmatched),
            "unmatched_occupation_labels": unmatched,
            "n_matched_onet_socs": len(matched_socs),
        },
        "onet": {
            "n_tasks": len(all_tasks),
            "n_tasks_with_any_dwa": len(tasks_with_any_dwa),
            "n_distinct_dwas": len({d for s in task_dwas.values() for d in s}),
            "n_reachable_dwas": len(reachable_dwas),
        },
        "coverage_bound": {
            "tasks_covered": len(covered),
            "share_of_all_tasks": len(covered) / len(all_tasks) if all_tasks else 0.0,
            "share_of_tasks_with_any_dwa": (
                len(covered) / len(tasks_with_any_dwa) if tasks_with_any_dwa else 0.0
            ),
            "wage_bill_weighted_share": weighted,
        },
        "baseline_for_comparison": {
            "mapping_a_direct_match_task_coverage": 0.00192118,
            "note": "from dax/mapping/PROTOCOL_mapA_gdpval.md section 9",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    cov = receipt["coverage_bound"]
    print(f"DWA-transport coverage bound: {cov['share_of_all_tasks']:.4f} of "
          f"{len(all_tasks)} O*NET tasks "
          f"({cov['tasks_covered']} tasks, {len(reachable_dwas)} reachable DWAs)")
    print(f"direct-match baseline was 0.00192118")
    if unmatched:
        print(f"NOTE: {len(unmatched)} GDPval occupation labels did not match an "
              f"O*NET title exactly and were EXCLUDED (bound is conservative "
              f"by that much): {unmatched}")
    if onet_linkage_fields:
        print(f"NOTE: GDPval parquet carries possible O*NET linkage fields: "
              f"{onet_linkage_fields} — inspect before annotating")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
