#!/usr/bin/env python3
"""p1/wrds/schema.py — the gate between "a name we hope is right" and a query.

CLAUDE.md meta-rule 1 says a table or column name from model memory is a
hallucination. WRDS makes that failure mode especially nasty: a wrong column
name usually does not raise, it silently returns a different number. So nothing
in this package builds SQL from a name until that exact name has been seen in
the live server's own inventory.

Three states per logical field:

  UNRESOLVED   no `resolved:` in tables.yaml -> every query touching it refuses
  RESOLVED     `resolved:` set AND present in discovered_schema.json -> usable
  STALE        `resolved:` set but NOT in the discovered inventory -> refuses,
               loudly, because that is precisely the hallucination case

`candidates:` never confers usability. It is a search list for the resolver and
nothing else — the hints in tables.yaml were scraped from this repo's own
history, which was itself written without a live connection.

Offline (no `wrds` package, no network) everything here still works except
discovery; that is what makes the pull scripts testable before the sprint.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

import yaml

HERE = pathlib.Path(__file__).resolve().parent
TABLES = HERE / "tables.yaml"
DISCOVERED = HERE / "discovered_schema.json"


class SchemaRefusal(RuntimeError):
    """Raised instead of running a query built on an unconfirmed name."""


@dataclass
class Inventory:
    """What the server actually has. Empty until `pull.py discover` has run."""
    tables: dict[str, list[str]] = field(default_factory=dict)   # "lib.table" -> [column, ...]

    @classmethod
    def load(cls, path: pathlib.Path = DISCOVERED) -> "Inventory":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text())
        return cls(tables={k: list(v) for k, v in raw.get("tables", {}).items()})

    @property
    def empty(self) -> bool:
        return not self.tables

    def has_table(self, name: str) -> bool:
        return name in self.tables

    def has_column(self, table: str, column: str) -> bool:
        return column in self.tables.get(table, [])


def load_spec(path: pathlib.Path = TABLES) -> dict:
    return yaml.safe_load(path.read_text())


def _refuse(lines: list[str]) -> None:
    raise SchemaRefusal("\n".join(lines))


class Resolver:
    """Answers 'what is the real name for this logical field?' — or refuses."""

    def __init__(self, spec: dict | None = None, inventory: Inventory | None = None):
        self.spec = spec if spec is not None else load_spec()
        self.inv = inventory if inventory is not None else Inventory.load()

    # ---- the two lookups every query goes through -------------------------
    def table(self, pull: str, logical: str) -> str:
        entry = self.spec["pulls"][pull]["tables"][logical]
        name = entry.get("resolved")
        if not name:
            _refuse([
                f"NEED_HUMAN: table '{logical}' of pull '{pull}' is unresolved.",
                f"  what we need: {entry.get('want', '').strip()}",
                f"  unverified hints: {entry.get('candidates')}",
                "  run `python p1/wrds/pull.py discover` on a connected node, then",
                "  `python p1/wrds/pull.py resolve`. Never fill this in from memory.",
            ])
        if self.inv.empty:
            _refuse([
                f"NEED_HUMAN: '{pull}.{logical}' claims to resolve to '{name}', but no",
                "  discovered inventory exists to confirm it against.",
                f"  run `python p1/wrds/pull.py discover` first ({DISCOVERED} is missing).",
            ])
        if not self.inv.has_table(name):
            _refuse([
                f"STALE SCHEMA: '{pull}.{logical}' resolves to '{name}', which is NOT in the",
                "  inventory read off the server. This is the hallucination case — the name",
                "  looks plausible and does not exist. Re-run resolve; do not 'fix' it by hand",
                "  unless you copied the name out of the WRDS web query tool.",
            ])
        return name

    def column(self, pull: str, logical: str, *, of_table: str) -> str:
        entry = self.spec["pulls"][pull]["columns"][logical]
        name = entry.get("resolved")
        if not name:
            _refuse([
                f"NEED_HUMAN: column '{logical}' of pull '{pull}' is unresolved.",
                f"  what we need: {entry.get('want', '').strip()}",
                f"  unverified hints: {entry.get('candidates')}",
                "  run discover + resolve. A wrong column name here returns wrong numbers",
                "  silently — that is why this refuses rather than guessing.",
            ])
        if self.inv.empty:
            _refuse([f"NEED_HUMAN: no discovered inventory to confirm '{pull}.{logical}' -> "
                     f"'{name}'. Run `python p1/wrds/pull.py discover`."])
        if not self.inv.has_column(of_table, name):
            _refuse([
                f"STALE SCHEMA: '{pull}.{logical}' resolves to column '{name}', which the",
                f"  server's inventory does not list on table '{of_table}'.",
                f"  columns actually present: {sorted(self.inv.tables.get(of_table, []))[:20]}",
            ])
        return name

    # ---- reporting --------------------------------------------------------
    def status(self) -> dict[str, dict[str, list[str]]]:
        """Per pull: which logical names are resolved, unresolved, or stale."""
        out: dict[str, dict[str, list[str]]] = {}
        for pull, cfg in self.spec["pulls"].items():
            buckets: dict[str, list[str]] = {"resolved": [], "unresolved": [], "stale": []}
            for logical, entry in cfg.get("tables", {}).items():
                name = entry.get("resolved")
                key = ("unresolved" if not name
                       else "resolved" if self.inv.has_table(name) else "stale")
                buckets[key].append(f"table:{logical}" + (f" -> {name}" if name else ""))
            tbl_names = [e.get("resolved") for e in cfg.get("tables", {}).values()
                         if e.get("resolved")]
            for logical, entry in cfg.get("columns", {}).items():
                name = entry.get("resolved")
                if not name:
                    buckets["unresolved"].append(f"column:{logical}")
                elif any(self.inv.has_column(t, name) for t in tbl_names):
                    buckets["resolved"].append(f"column:{logical} -> {name}")
                else:
                    buckets["stale"].append(f"column:{logical} -> {name}")
            out[pull] = buckets
        return out

    def ready(self, pull: str) -> bool:
        b = self.status()[pull]
        return not b["unresolved"] and not b["stale"]

    def outstanding_asserts(self, pull: str) -> dict[str, str]:
        """Semantic questions tables.yaml flags as NEED_HUMAN (units, conventions).

        These are NOT resolved by discovery — no amount of column listing tells
        you whether shrout is in thousands, or which effective-spread convention
        a field implements. They need the owner or the documentation.
        """
        return dict(self.spec["pulls"][pull].get("asserts", {}) or {})


def format_status(resolver: Resolver) -> str:
    lines = []
    inv = resolver.inv
    lines.append(f"discovered inventory: "
                 + (f"{len(inv.tables)} tables" if not inv.empty
                    else "MISSING — run `pull.py discover` on a connected node"))
    for pull, b in resolver.status().items():
        state = ("READY" if not b["unresolved"] and not b["stale"]
                 else "STALE" if b["stale"] else "BLOCKED")
        lines.append(f"\n[{state}] {pull}  "
                     f"({len(b['resolved'])} resolved, {len(b['unresolved'])} unresolved,"
                     f" {len(b['stale'])} stale)")
        for k in ("stale", "unresolved"):
            for item in b[k]:
                lines.append(f"    {k:10s} {item}")
        for name, text in resolver.outstanding_asserts(pull).items():
            lines.append(f"    NEED_HUMAN {name}: {' '.join(text.split())[:150]}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_status(Resolver()))
