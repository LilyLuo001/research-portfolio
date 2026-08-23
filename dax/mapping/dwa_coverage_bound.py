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


class LayoutError(RuntimeError):
    """A source table did not parse into the shape its header describes."""


def _read_delimited(name: str, raw: bytes) -> list[dict[str, str]]:
    """Parse an O*NET table, refusing any parse that collapses the header.

    The delimiter is decided from the header line, never from a byte sample.
    O*NET headers contain no commas, but prose columns do -- Occupation Data's
    Description column alone carries more commas than the sample has tabs -- so
    a whole-sample tab-vs-comma count picks comma and folds the entire header
    into one column named "O*NET-SOC Code\tTitle\tDescription".

    That failure is silent and dangerous rather than loud: the folded name
    still contains every substring a caller searches for, so column lookup
    "succeeds" and returns the same key for different fields. Zero occupation
    titles then match, and the script reports a confident coverage bound of
    0.0 -- a false negative that looks exactly like a real finding.

    A correctly parsed header never contains the delimiter inside a column
    name, so that is asserted here and the whole class is closed.
    """

    text = raw.decode("utf-8-sig", errors="replace")
    header = text.split("\n", 1)[0].rstrip("\r")
    delimiter = "\t" if "\t" in header else ","
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
    if rows:
        folded = [c for c in rows[0] if c is not None and ("\t" in c or "\r" in c)]
        if folded:
            raise LayoutError(
                f"{name}: header did not split -- column name still contains a "
                f"delimiter: {folded[0]!r}"
            )
    return rows


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


def _select(
    tables: dict[str, list[dict[str, str]]],
    *,
    required: set[str],
    forbidden: set[str] = frozenset(),
    unique: str | None = None,
) -> tuple[str, list[dict[str, str]], list[str]]:
    """Pick the table whose columns EXACTLY contain `required` and none of `forbidden`.

    Substring matching is too loose to identify an O*NET table. Searching for
    a column merely *containing* "title" selects Sample of Reported Titles.txt
    -- whose "Reported Job Title" is a colloquial incumbent-reported title --
    ahead of Occupation Data.txt, because both offer a distinct column per
    requirement and the sample file comes first in archive order. None of the
    44 canonical GDPval labels then match, which the zero-match guard correctly
    refuses, but the cause is table selection rather than parsing.

    Exact names disambiguate: Occupation Data has a column named exactly
    "Title"; the reported-titles sample does not. Ties are broken by sorted
    name so the choice never depends on archive order, and every alternative
    is returned for the receipt.
    """

    hits = []
    for name in sorted(tables):
        rows = tables[name]
        if not rows:
            continue
        cols = {c.lower().strip() for c in rows[0] if c is not None}
        if not (required <= cols) or (forbidden & cols):
            continue
        if unique is not None:
            # A universe table has one row per key. Task Ratings.txt satisfies
            # every column requirement Task Statements.txt does, but its grain
            # is task x scale x category, so its Task ID repeats. Grain is the
            # thing that actually distinguishes them, so test grain.
            key = next(c for c in rows[0] if c is not None and c.lower().strip() == unique)
            values = [r[key] for r in rows]
            if len(values) != len(set(values)):
                continue
        hits.append(name)
    if not hits:
        raise LayoutError(
            f"no table has exactly the columns {sorted(required)}"
            + (f" while lacking {sorted(forbidden)}" if forbidden else "")
            + (f" with one row per {unique!r}" if unique else "")
        )
    return hits[0], tables[hits[0]], hits[1:]


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
    ap.add_argument("--expect-audit", type=pathlib.Path,
                    default=pathlib.Path(__file__).resolve().parent / "mapA_input_audit_receipt.json",
                    help="pinned input audit to reconcile the derived task "
                         "universe against; pass /dev/null to skip")
    ap.add_argument("--task-weights", type=pathlib.Path,
                    help="optional CSV with task_id and a weight column, for "
                         "wage-bill-weighted coverage")
    args = ap.parse_args(argv)

    raw = _members(args.onet)
    try:
        tables = {name: _read_delimited(name, blob) for name, blob in raw.items()}
    except LayoutError as error:
        print(f"NEED_HUMAN: {error}", file=sys.stderr)
        return 2

    # Exact column sets, so selection cannot drift onto a lookalike table.
    # Task Statements and Tasks-to-DWAs both carry O*NET-SOC Code and Task ID;
    # the DWA id is what separates them.
    try:
        task_dwa_name, task_dwa_rows, task_dwa_alts = _select(
            tables, required={"task id", "dwa id"})
        stmt_name, stmt_rows, stmt_alts = _select(
            tables, required={"o*net-soc code", "task id", "task"},
            forbidden={"dwa id"}, unique="task id")
        occ_name, occ_rows, occ_alts = _select(
            tables, required={"o*net-soc code", "title"})
    except LayoutError as error:
        print(f"NEED_HUMAN: {error}. Tables seen:", file=sys.stderr)
        for name in sorted(tables):
            cols = list(tables[name][0]) if tables[name] else []
            print(f"  {name}: {cols[:8]}", file=sys.stderr)
        return 2

    selection = {
        "task_to_dwa": task_dwa_name, "task_statements": stmt_name,
        "occupations": occ_name,
        "alternatives_not_chosen": {
            "task_to_dwa": task_dwa_alts, "task_statements": stmt_alts,
            "occupations": occ_alts,
        },
    }

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
    soc_key = _col(occ_rows[0], "o*net-soc code")
    title_key = _col(occ_rows[0], "title")
    if soc_key == title_key:
        print(f"NEED_HUMAN: occupation table {occ_name} resolved code and title "
              f"to the same column {soc_key!r} -- it did not parse", file=sys.stderr)
        return 2
    by_title: dict[str, list[str]] = defaultdict(list)
    for row in occ_rows:
        by_title[_norm(row[title_key])].append(row[soc_key])

    if not by_title:
        print("NEED_HUMAN: occupation table yielded no titles", file=sys.stderr)
        return 2

    matched_socs: set[str] = set()
    unmatched: list[str] = []
    for occ in gdp_occupations:
        hits = by_title.get(_norm(occ), [])
        if hits:
            matched_socs.update(hits)
        else:
            unmatched.append(occ)

    # A total miss is far more likely to be a parse fault than a real finding:
    # GDPval occupations are drawn from O*NET titles by construction.
    if not matched_socs:
        print(f"NEED_HUMAN: none of the {len(gdp_occupations)} GDPval occupation "
              f"labels matched an O*NET title. That is a parse, vintage, or "
              f"table-selection fault, not a coverage result -- refusing to "
              f"report 0.0.\n  occupation table used: {occ_name} "
              f"(columns {list(occ_rows[0])})\n  alternatives not chosen: "
              f"{occ_alts}\n  first 3 GDPval labels: {gdp_occupations[:3]}",
              file=sys.stderr)
        return 2

    # --- task -> soc, task -> dwa
    st_task = _col(stmt_rows[0], "task", "id")
    st_soc = _col(stmt_rows[0], "o*net-soc code")
    task_soc = {r[st_task]: r[st_soc] for r in stmt_rows}

    td_rows = task_dwa_rows
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

    # The repo already pins what the task universe must look like. Three
    # rounds of table-selection faults each produced a plausible number on a
    # wrong universe; reconciling against the pin catches that whole class
    # rather than one lookalike table at a time.
    expected = None
    if args.expect_audit and args.expect_audit.exists() and args.expect_audit.name != "null":
        try:
            audit = json.loads(args.expect_audit.read_text(encoding="utf-8"))
            expected = audit.get("onet", {})
        except (json.JSONDecodeError, OSError):
            expected = None
    if expected:
        want_tasks = expected.get("n_unique_task_ids")
        want_socs = expected.get("n_unique_onet_socs")
        got_socs = len({s for s in task_soc.values()})
        problems = []
        if want_tasks is not None and len(all_tasks) != want_tasks:
            problems.append(f"tasks {len(all_tasks)} != pinned {want_tasks}")
        if want_socs is not None and got_socs != want_socs:
            problems.append(f"O*NET-SOCs {got_socs} != pinned {want_socs}")
        if problems:
            print(f"NEED_HUMAN: derived task universe does not reconcile with "
                  f"{args.expect_audit.name}: {'; '.join(problems)}.\n"
                  f"  task_statements table used: {stmt_name} "
                  f"(columns {list(stmt_rows[0])})\n"
                  f"  alternatives not chosen: {stmt_alts}\n"
                  f"  A coverage share computed on the wrong denominator is not "
                  f"a finding -- refusing to write a receipt.", file=sys.stderr)
            return 2

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
            "onet_tables_used": selection,
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
        "universe_reconciliation": {
            "pinned_audit": str(args.expect_audit),
            "pinned_n_unique_task_ids": (expected or {}).get("n_unique_task_ids"),
            "pinned_n_unique_onet_socs": (expected or {}).get("n_unique_onet_socs"),
            "derived_n_tasks": len(all_tasks),
            "derived_n_onet_socs": len({s for s in task_soc.values()}),
            "reconciled": bool(expected),
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
