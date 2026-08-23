"""Derive the event table shell's locked columns from the frozen registry.

`event_table_shell_v1.csv` mirrors `event_registry_v1.csv` in five columns and
leaves the rest blank for W5 to fill mechanically. Nothing previously kept the
mirror in sync, so the shell drifted: eight rows still carried
`pending_second_date_locator` after the registry gained their second locators,
and three of those still carried a `w5_fill_status` of
`BLOCKED_SOURCE_THEN_W5_FILL` that was blocked on exactly that pending source.

This script rewrites only the mirrored and derived columns. Every W5-fillable
column is preserved byte-for-byte, so running it can never fill in an estimate.
`--check` exits non-zero when the file on disk has drifted, which is what CI
should run.
"""

from __future__ import annotations

import argparse
import csv
import io
import pathlib
import sys


HERE = pathlib.Path(__file__).resolve().parent
REGISTRY = HERE / "event_registry_v1.csv"
SHELL = HERE / "event_table_shell_v1.csv"

# Mirrored straight from the registry.
LOCKED = {
    "api_effective_date": "api_effective_date",
    "registry_status": "analysis_status",
    "source_verification": "verification_status",
}


# The D1 design change (2026-08-18) demoted the stacked event study from the
# primary specification to secondary corroboration, renaming its columns. A
# botched migration appended the new table below the old one instead of
# replacing it, so both blocks live in the file. Dropping the stale block is
# only safe if every pre-D1 column is either blank throughout or carries values
# identical to the column that superseded it.
RENAMED_BY_D1 = {
    "primary_inclusion_rule": "secondary_inclusion_rule",
    "window_rule": "secondary_window_rule",
    "window_start": "secondary_window_start",
    "window_end": "secondary_window_end",
    "pre_months": "secondary_pre_months",
    "post_months": "secondary_post_months",
    "max_effective_weight_share": "secondary_max_effective_weight_share",
}


class SyncError(RuntimeError):
    pass


def w5_fill_status(registry_row: dict[str, str]) -> str:
    """The shell's W5 disposition, derived from registry state alone.

    A binding exclusion is never filled. A row whose second date locator is
    still outstanding is blocked on that source before W5 can reach it.
    Everything else awaits W5's mechanical fill.
    """

    if registry_row["analysis_status"] == "excluded_binding":
        return "NOT_APPLICABLE"
    if registry_row["verification_status"] != "verified":
        return "BLOCKED_SOURCE_THEN_W5_FILL"
    return "PENDING_W5_MECHANICAL_FILL"


def _blocks(text: str) -> list[list[str]]:
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("event_id,")]
    if not starts:
        raise SyncError("event table shell has no header row")
    return [
        lines[start : (starts[n + 1] if n + 1 < len(starts) else len(lines))]
        for n, start in enumerate(starts)
    ]


def read_shell(path: pathlib.Path = SHELL) -> tuple[list[str], dict[str, dict[str, str]]]:
    """Return the shell's fieldnames and rows, tolerating a duplicated block.

    A botched migration left the pre-D1 table above the post-D1 one in the same
    file. The widest block is the migrated one; a narrower block carries no
    column the wider one lacks, so it is dropped.
    """

    blocks = _blocks(path.read_text(encoding="utf-8"))
    parsed = [list(csv.DictReader(io.StringIO("\n".join(b)))) for b in blocks]
    widest = max(range(len(parsed)), key=lambda i: len(parsed[i][0]) if parsed[i] else 0)
    chosen = parsed[widest]
    if not chosen:
        raise SyncError("event table shell has no data rows")
    fieldnames = list(chosen[0])
    kept = {row["event_id"]: row for row in chosen}
    for other in (p for n, p in enumerate(parsed) if n != widest and p):
        for column in set(other[0]) - set(fieldnames):
            successor = RENAMED_BY_D1.get(column)
            if successor is None:
                raise SyncError(f"discarded shell block carries unknown column {column!r}")
            for row in other:
                stale = (row.get(column) or "").strip()
                if not stale:
                    continue
                current = (kept.get(row["event_id"], {}).get(successor) or "").strip()
                if stale != current:
                    raise SyncError(
                        f"{row['event_id']}: stale {column}={stale!r} would be lost; "
                        f"{successor}={current!r}"
                    )
    return fieldnames, kept


def build(registry_path: pathlib.Path = REGISTRY) -> tuple[list[str], list[dict[str, str]]]:
    with registry_path.open(newline="", encoding="utf-8") as handle:
        registry = list(csv.DictReader(handle))
    fieldnames, existing = read_shell()

    missing = {row["event_id"] for row in registry} - set(existing)
    if missing:
        raise SyncError(f"registry events absent from the shell: {sorted(missing)}")

    rows: list[dict[str, str]] = []
    for registry_row in registry:
        event_id = registry_row["event_id"]
        row = dict(existing[event_id])
        for shell_field, registry_field in LOCKED.items():
            row[shell_field] = registry_row[registry_field]
        row["w5_fill_status"] = w5_fill_status(registry_row)
        rows.append({name: row.get(name, "") for name in fieldnames})
    return fieldnames, rows


def render(fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if the shell has drifted")
    args = parser.parse_args(argv)

    rendered = render(*build())
    if args.check:
        if SHELL.read_text(encoding="utf-8") != rendered:
            print("event table shell has drifted from the registry", file=sys.stderr)
            return 1
        print("event table shell is in sync with the registry")
        return 0
    SHELL.write_text(rendered, encoding="utf-8")
    print(f"event table shell synced — {len(rendered.splitlines()) - 1} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
