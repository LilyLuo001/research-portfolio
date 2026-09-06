#!/usr/bin/env python3
"""Build and validate the V3 source-text locator registry for G02.

This program resolves every unique ``source_ref`` in the immutable requirement
seed to an exact source-file line span when the supplied document supports that
locator.  Synthetic or unavailable locator systems are retained as explicit
unresolved records rather than reconstructed from subject-matter similarity.

The registry is a provenance layer only.  It does not establish that every
numbered and unnumbered request in the source documents has been atomized.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
V3_ROOT = HERE.parent
INPUTS = V3_ROOT / "revision_inputs"
SEED = INPUTS / "requirements_seed.json"
CROSSWALK = V3_ROOT / "ACCEPTANCE_CHECK_CROSSWALK.csv"

EXPECTED_SEED_SHA256 = (
    "38de2d5b80e72c85f3dd06086a862cea63c521d511a5baacb7f6390f66eeeb59"
)

REGISTRY_JSON = HERE / "SOURCE_LOCATOR_REGISTRY.json"
REGISTRY_CSV = HERE / "SOURCE_LOCATOR_REGISTRY.csv"
VALIDATION_JSON = HERE / "G02_SOURCE_PROVENANCE_VALIDATION.json"
VALIDATION_MD = HERE / "G02_SOURCE_PROVENANCE_REPORT.md"


DOCUMENTS = {
    "A": "referee_A_major_revision.md",
    "B": "referee_B_rejection.md",
    "C": "ASSISTANT_AUDIT_AND_FAILURE_MODES.md",
    "P0": "previous_execution_prompt.md",
    "EARLIER": "earlier_uploaded_referee.md",
    "V3": "EXECUTION_PROMPT_V3.md",
}


def resolved(
    document_id: str,
    start_line: int,
    end_line: int,
    method: str,
    anchor: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "resolution_status": "RESOLVED",
        "resolution_method": method,
        "start_line": start_line,
        "end_line": end_line,
        "anchor": anchor,
        "note": note,
    }


def unresolved(document_id: str, reason: str, note: str = "") -> dict[str, Any]:
    return {
        "document_id": document_id,
        "resolution_status": "UNRESOLVED",
        "resolution_method": reason,
        "start_line": None,
        "end_line": None,
        "anchor": None,
        "note": note,
    }


LOCATORS: dict[str, dict[str, Any]] = {
    # Referee A: literal section, subsection, and numbered-list locators.
    "A:all": resolved("A", 1, 157, "whole_document"),
    "A:overall": resolved(
        "A", 17, 32, "semantic_heading_span", "## 2. Overall assessment"
    ),
    "A:3.1": resolved("A", 35, 44, "literal_heading_span", "### 3.1 "),
    "A:3.2": resolved("A", 45, 58, "literal_heading_span", "### 3.2 "),
    "A:3.3": resolved("A", 59, 64, "literal_heading_span", "### 3.3 "),
    "A:3.4": resolved("A", 65, 76, "literal_heading_span", "### 3.4 "),
    "A:3.5": resolved("A", 77, 85, "literal_heading_span", "### 3.5 "),
    "A:3.6": resolved("A", 86, 91, "literal_heading_span", "### 3.6 "),
    "A:3.7": resolved("A", 92, 97, "literal_heading_span", "### 3.7 "),
    "A:3.8": resolved("A", 98, 103, "literal_heading_span", "### 3.8 "),
    "A:3.9": resolved("A", 104, 109, "literal_heading_span", "### 3.9 "),
    "A:3.10": resolved("A", 110, 115, "literal_heading_span", "### 3.10 "),
    "A:3.11": resolved("A", 116, 122, "literal_heading_span", "### 3.11 "),
    "A:3.11 ACS": resolved("A", 118, 118, "literal_labeled_list_item", "- **ACS.**"),
    "A:3.11 adoption": resolved(
        "A", 119, 119, "literal_labeled_list_item", "- **Adoption measures.**"
    ),
    "A:minor1": resolved("A", 125, 125, "literal_numbered_list_item", "1. **Numerical inconsistency.**"),
    "A:minor2": resolved("A", 126, 126, "literal_numbered_list_item", "2. **\"Chapter.\"**"),
    "A:minor3": resolved("A", 127, 127, "literal_numbered_list_item", "3. The stratified industry baseline"),
    "A:minor4": resolved("A", 128, 128, "literal_numbered_list_item", "4. Appendix Figure 1"),
    "A:minor5": resolved("A", 129, 129, "literal_numbered_list_item", "5. The manuscript reports"),
    "A:minor6": resolved("A", 130, 130, "literal_numbered_list_item", "6. The MDE80 statistics"),
    "A:minor7": resolved("A", 131, 131, "literal_numbered_list_item", "7. Prose density."),
    "A:minor8": resolved("A", 132, 132, "literal_numbered_list_item", "8. Missing references"),
    "A:minor9": resolved("A", 133, 133, "literal_numbered_list_item", "9. The abstract states"),
    "A:minor10": resolved("A", 134, 134, "literal_numbered_list_item", "10. Appendix I.3"),
    "A:minor front matter inherited": unresolved(
        "A",
        "synthetic_inherited_locator_not_present",
        "The supplied A report contains front-matter metadata at lines 3-7 but no "
        "request labeled 'minor front matter inherited'; assigning those metadata lines "
        "to this requirement would invent a source request.",
    ),

    # Referee B: literal numbered sections and bold presentation comments.
    "B:all": resolved("B", 1, 138, "whole_document"),
    "B:1": resolved("B", 22, 33, "literal_heading_span", "### 1. "),
    "B:2": resolved("B", 34, 53, "literal_heading_span", "### 2. "),
    "B:3": resolved("B", 54, 67, "literal_heading_span", "### 3. "),
    "B:4": resolved("B", 68, 87, "literal_heading_span", "### 4. "),
    "B:5": resolved("B", 88, 103, "literal_heading_span", "### 5. "),
    "B:6": resolved("B", 104, 121, "literal_heading_span", "### 6. "),
    "B:specific dependent variable": resolved(
        "B", 124, 124, "literal_bold_comment", "**Clarify the model’s dependent variable.**"
    ),
    "B:specific exposure reconstruction": resolved(
        "B", 126, 126, "semantic_alias_to_literal_bold_comment",
        "**Make exposure-group reconstruction explicit",
    ),
    "B:specific reconstruction": resolved(
        "B", 126, 126, "semantic_alias_to_literal_bold_comment",
        "**Make exposure-group reconstruction explicit",
    ),
    "B:specific prose": resolved(
        "B", 128, 128, "semantic_alias_to_literal_bold_comment",
        "**Reduce repeated qualifications and implementation history.**",
    ),
    "B:reproducibility": resolved(
        "B", 130, 130, "semantic_alias_to_literal_bold_comment",
        "**Separate reproducibility claims from verified replication.**",
    ),
    "B:conclusion": resolved("B", 132, 138, "literal_heading_span", "## Concluding assessment"),

    # C is explicitly a non-verbatim summary. Only literal headings/semantic aliases
    # with a uniquely corresponding supplied span are resolved. Its numbered locator
    # system is absent and must not be reverse-engineered from topical similarity.
    "C:all": resolved("C", 1, 48, "whole_document"),
    "C:execution audit": resolved(
        "C", 25, 31, "semantic_heading_span", "## Observable failure patterns versus unknown causes"
    ),
    "C:root-cause diagnosis": resolved(
        "C", 25, 31, "semantic_heading_span", "## Observable failure patterns versus unknown causes"
    ),
    "C:failure prevention": resolved(
        "C", 25, 31, "semantic_heading_span", "## Observable failure patterns versus unknown causes"
    ),
    "C:new source verification": resolved(
        "C", 44, 48, "semantic_heading_span", "## Concrete source verification"
    ),
    "New methodological audit": resolved(
        "C", 33, 42, "synthetic_alias_to_literal_heading",
        "## New methodological safeguards introduced in V3",
        "The seed uses an unprefixed synthetic alias; the supplied C document has a "
        "single uniquely matching section.",
    ),

    # Earlier referee: literal numbered locations.
    "Earlier referee:3.8": resolved(
        "EARLIER", 113, 121, "literal_heading_span", "### 3.8 "
    ),
    "Earlier referee:4.1": resolved(
        "EARLIER", 141, 142, "literal_bold_numbered_comment", "**4.1 "
    ),
    "Earlier referee:4.7": resolved(
        "EARLIER", 153, 154, "literal_bold_numbered_comment", "**4.7 "
    ),

    # P0: literal numbered sections.
    "P0:all": resolved("P0", 1, 281, "whole_document"),
    "P0:1": resolved("P0", 3, 21, "literal_heading_span", "## 1. "),
    "P0:2": resolved("P0", 22, 41, "literal_heading_span", "## 2. "),
    "P0:3": resolved("P0", 42, 58, "literal_heading_span", "## 3. "),
    "P0:4": resolved("P0", 59, 76, "literal_heading_span", "## 4. "),
    "P0:5": resolved("P0", 77, 107, "literal_heading_span", "## 5. "),
    "P0:6": resolved("P0", 108, 127, "literal_heading_span", "## 6. "),
    "P0:7": resolved("P0", 128, 158, "literal_heading_span", "## 7. "),
    "P0:8": resolved("P0", 159, 176, "literal_heading_span", "## 8. "),
    "P0:9": resolved("P0", 177, 192, "literal_heading_span", "## 9. "),
    "P0:10": resolved("P0", 193, 206, "literal_heading_span", "## 10. "),
    "P0:11": resolved("P0", 207, 226, "literal_heading_span", "## 11. "),
    "P0:12": resolved("P0", 227, 256, "literal_heading_span", "## 12. "),
    "P0:13": resolved("P0", 257, 264, "literal_heading_span", "## 13. "),
    "P0:14": resolved("P0", 265, 281, "literal_heading_span", "## 14. "),

    # V3 is a registered controlling source even though no seed row uses V3:*.
    "V3:all": resolved(
        "V3", 1, 542, "whole_document", note="Registered by explicit handoff instruction."
    ),
}


for missing_c_ref in (
    "C:1", "C:2.1", "C:2.2", "C:3.1", "C:3.2", "C:3.3",
    "C:3.4", "C:4", "C:4.1", "C:4.2", "C:4.3", "C:5", "C:6",
):
    LOCATORS[missing_c_ref] = unresolved(
        "C",
        "numbered_locator_system_absent_from_supplied_summary",
        "The supplied C file states that it is a non-verbatim working summary and has "
        "no section or paragraph marker matching this source_ref. Topical matching "
        "would not establish the requested provenance.",
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_lines(path: Path) -> list[bytes]:
    return path.read_bytes().splitlines(keepends=True)


def source_refs_from_seed() -> set[str]:
    payload = json.loads(SEED.read_text(encoding="utf-8"))
    return {
        ref
        for requirement in payload["requirements"]
        for ref in requirement["source_refs"]
    }


def acceptance_crosslinks() -> tuple[dict[str, list[str]], str]:
    links: dict[str, list[str]] = {}
    with CROSSWALK.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            atomic_id = row["atomic_id"]
            for ref in filter(None, row["source_refs"].split(";")):
                links.setdefault(ref, []).append(atomic_id)
    for ref in links:
        links[ref] = sorted(set(links[ref]))
    return links, sha256_file(CROSSWALK)


def build_registry() -> dict[str, Any]:
    if sha256_file(SEED) != EXPECTED_SEED_SHA256:
        raise RuntimeError("immutable requirements seed hash changed")

    seed_refs = source_refs_from_seed()
    mapped_seed_refs = set(LOCATORS) - {"V3:all"}
    if seed_refs != mapped_seed_refs:
        raise RuntimeError(
            "locator map and seed source_refs differ: "
            f"missing={sorted(seed_refs - mapped_seed_refs)}, "
            f"extra={sorted(mapped_seed_refs - seed_refs)}"
        )

    crosslinks, crosswalk_sha256 = acceptance_crosslinks()
    if set(crosslinks) != seed_refs:
        raise RuntimeError(
            "acceptance crosswalk and seed source_refs differ: "
            f"missing={sorted(seed_refs - set(crosslinks))}, "
            f"extra={sorted(set(crosslinks) - seed_refs)}"
        )

    documents: dict[str, dict[str, Any]] = {}
    line_cache: dict[str, list[bytes]] = {}
    for document_id, filename in DOCUMENTS.items():
        path = INPUTS / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        lines = exact_lines(path)
        line_cache[document_id] = lines
        documents[document_id] = {
            "document_id": document_id,
            "path": f"revision_inputs/{filename}",
            "sha256": sha256_file(path),
            "byte_length": path.stat().st_size,
            "physical_lines": len(lines),
        }

    rows: list[dict[str, Any]] = []
    for source_ref in sorted(LOCATORS):
        row = dict(LOCATORS[source_ref])
        row["source_ref"] = source_ref
        row["in_requirements_seed"] = source_ref in seed_refs
        row["acceptance_atomic_ids"] = crosslinks.get(source_ref, [])
        row["acceptance_atomic_count"] = len(row["acceptance_atomic_ids"])
        if row["resolution_status"] == "RESOLVED":
            lines = line_cache[row["document_id"]]
            start = row["start_line"]
            end = row["end_line"]
            if not isinstance(start, int) or not isinstance(end, int):
                raise RuntimeError(f"{source_ref}: resolved locator has no integer span")
            if start < 1 or end < start or end > len(lines):
                raise RuntimeError(f"{source_ref}: invalid line span {start}-{end}")
            span = b"".join(lines[start - 1 : end])
            if row.get("anchor") and row["anchor"].encode("utf-8") not in span:
                raise RuntimeError(
                    f"{source_ref}: expected anchor absent from lines {start}-{end}"
                )
            row["span_sha256"] = sha256_bytes(span)
            row["span_byte_length"] = len(span)
            row["hash_definition"] = (
                "sha256 of exact source bytes for inclusive physical lines; original "
                "line endings retained"
            )
        else:
            row["span_sha256"] = None
            row["span_byte_length"] = None
            row["hash_definition"] = None
        rows.append(row)

    return {
        "schema_version": "yax.source_locator_registry.v1",
        "purpose": "G02 source-text provenance layer",
        "completion_scope": (
            "Resolves unique seed source_refs only; does not establish exhaustive "
            "atomization of all requests in the source prose."
        ),
        "requirements_seed": {
            "path": "revision_inputs/requirements_seed.json",
            "sha256": EXPECTED_SEED_SHA256,
            "unique_source_refs": len(seed_refs),
        },
        "acceptance_check_crosswalk": {
            "path": "ACCEPTANCE_CHECK_CROSSWALK.csv",
            "sha256": crosswalk_sha256,
        },
        "documents": [documents[key] for key in sorted(documents)],
        "locators": rows,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(registry: dict[str, Any]) -> None:
    fields = [
        "source_ref", "in_requirements_seed", "document_id", "resolution_status",
        "resolution_method", "start_line", "end_line", "span_sha256",
        "span_byte_length", "acceptance_atomic_count", "acceptance_atomic_ids",
        "anchor", "note",
    ]
    with REGISTRY_CSV.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for source in registry["locators"]:
            row = {key: source.get(key) for key in fields}
            row["acceptance_atomic_ids"] = ";".join(source["acceptance_atomic_ids"])
            writer.writerow(row)


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(condition), "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    seed_refs = source_refs_from_seed()
    check(
        "immutable_seed_hash",
        sha256_file(SEED) == EXPECTED_SEED_SHA256,
        sha256_file(SEED),
    )
    check(
        "acceptance_crosswalk_hash",
        sha256_file(CROSSWALK)
        == registry["acceptance_check_crosswalk"]["sha256"],
        sha256_file(CROSSWALK),
    )

    document_map = {row["document_id"]: row for row in registry["documents"]}
    for document_id, document in document_map.items():
        path = V3_ROOT / document["path"]
        check(
            f"document_hash:{document_id}",
            path.is_file() and sha256_file(path) == document["sha256"],
            document["path"],
        )

    locator_map = {row["source_ref"]: row for row in registry["locators"]}
    check(
        "all_seed_source_refs_registered_once",
        set(locator_map) - {"V3:all"} == seed_refs
        and len(registry["locators"]) == len(locator_map),
        f"seed={len(seed_refs)} registry_seed_refs={len(set(locator_map) - {'V3:all'})}",
    )
    check(
        "v3_prompt_registered",
        "V3:all" in locator_map and locator_map["V3:all"]["resolution_status"] == "RESOLVED",
        "V3:all",
    )

    exact_hash_failures: list[str] = []
    unresolved_format_failures: list[str] = []
    missing_crosslinks: list[str] = []
    for source_ref, row in locator_map.items():
        if source_ref in seed_refs and not row["acceptance_atomic_ids"]:
            missing_crosslinks.append(source_ref)
        if row["resolution_status"] == "RESOLVED":
            document = document_map[row["document_id"]]
            lines = exact_lines(V3_ROOT / document["path"])
            start, end = row["start_line"], row["end_line"]
            if not isinstance(start, int) or not isinstance(end, int):
                exact_hash_failures.append(source_ref)
                continue
            span = b"".join(lines[start - 1 : end])
            if sha256_bytes(span) != row["span_sha256"]:
                exact_hash_failures.append(source_ref)
            if row.get("anchor") and row["anchor"].encode("utf-8") not in span:
                exact_hash_failures.append(source_ref + ":anchor")
        elif not (
            row["start_line"] is None
            and row["end_line"] is None
            and row["span_sha256"] is None
            and row["resolution_method"]
            and row["note"]
        ):
            unresolved_format_failures.append(source_ref)

    check(
        "resolved_span_hashes_recompute",
        not exact_hash_failures,
        ",".join(exact_hash_failures) or "all resolved spans authenticate",
    )
    check(
        "unresolved_locators_are_explicit",
        not unresolved_format_failures,
        ",".join(unresolved_format_failures) or "all unresolved rows carry reasons",
    )
    check(
        "seed_refs_crosslinked_to_acceptance_rows",
        not missing_crosslinks,
        ",".join(missing_crosslinks) or "all seed refs have acceptance atomic IDs",
    )

    resolved_count = sum(
        row["resolution_status"] == "RESOLVED" and row["in_requirements_seed"]
        for row in locator_map.values()
    )
    unresolved_refs = sorted(
        row["source_ref"]
        for row in locator_map.values()
        if row["resolution_status"] == "UNRESOLVED" and row["in_requirements_seed"]
    )
    return {
        "schema_version": "yax.source_provenance_validation.v1",
        "status": "PASS" if not failures else "FAIL",
        "scope": "source_ref provenance integrity, not exhaustive request extraction",
        "g02_requirement_status_recommendation": "NOT_VERIFIED",
        "g02_completion_claim": False,
        "seed_unique_source_refs": len(seed_refs),
        "resolved_seed_source_refs": resolved_count,
        "unresolved_seed_source_refs": len(unresolved_refs),
        "unresolved_refs": unresolved_refs,
        "registered_documents": len(document_map),
        "checks": checks,
        "failures": failures,
        "limitations": [
            "The acceptance crosswalk atomizes the seed's acceptance checks; it does not "
            "prove that every request sentence in A, B, C, P0, or the earlier referee "
            "has been independently extracted.",
            "The supplied C document is explicitly a non-verbatim summary and lacks the "
            "numbered C locator system used by the seed.",
            "A:minor front matter inherited is a synthetic inherited label with no matching "
            "request in the supplied A report.",
            "No unresolved locator was assigned by topical similarity.",
        ],
    }


def write_markdown(registry: dict[str, Any], validation: dict[str, Any]) -> None:
    unresolved_rows = [
        row
        for row in registry["locators"]
        if row["in_requirements_seed"] and row["resolution_status"] == "UNRESOLVED"
    ]
    lines = [
        "# G02 source-provenance report",
        "",
        f"Validation status: **{validation['status']}** for the provenance layer.",
        "",
        "This is not a G02 completion certificate. It authenticates the source files, "
        "maps every unique source reference already present in the immutable seed, and "
        "cross-links those references to `ACCEPTANCE_CHECK_CROSSWALK.csv`. G02 still "
        "requires an exhaustive extraction of every numbered and unnumbered source request.",
        "",
        "## Coverage",
        "",
        f"- Registered source documents: {validation['registered_documents']}",
        f"- Unique source references in the seed: {validation['seed_unique_source_refs']}",
        f"- Resolved to authenticated text spans: {validation['resolved_seed_source_refs']}",
        f"- Explicitly unresolved: {validation['unresolved_seed_source_refs']}",
        f"- Immutable seed SHA-256: `{EXPECTED_SEED_SHA256}`",
        f"- Acceptance crosswalk SHA-256: "
        f"`{registry['acceptance_check_crosswalk']['sha256']}`",
        "",
        "For resolved locators, `span_sha256` hashes the exact source bytes for the "
        "inclusive physical line range, retaining original line endings.",
        "",
        "## Unresolved or synthetic provenance",
        "",
        "| source ref | reason |",
        "|---|---|",
    ]
    for row in unresolved_rows:
        reason = f"{row['resolution_method']}: {row['note']}".replace("|", "\\|")
        lines.append(f"| `{row['source_ref']}` | {reason} |")
    lines.extend([
        "",
        "The numbered `C:*` locators cannot be reconstructed from the supplied C file: "
        "that document identifies itself as a non-verbatim summary and contains no matching "
        "numbering. They are therefore preserved as unresolved rather than mapped by topic.",
        "",
        "## Validation boundary",
        "",
        "The machine checks authenticate documents and resolved spans, preserve unresolved "
        "provenance, confirm exact coverage of the seed's unique source references, confirm "
        "cross-links to the current acceptance-check crosswalk, and verify that the seed hash "
        "is unchanged. They do not determine whether the source prose has been exhaustively "
        "atomized or whether any scientific request has been completed.",
        "",
    ])
    VALIDATION_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    registry = build_registry()
    write_json(REGISTRY_JSON, registry)
    write_csv(registry)
    # Validate the serialized authoritative JSON, not only the in-memory object.
    persisted_registry = json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
    validation = validate_registry(persisted_registry)
    write_json(VALIDATION_JSON, validation)
    write_markdown(persisted_registry, validation)
    print(json.dumps({
        "status": validation["status"],
        "seed_unique_source_refs": validation["seed_unique_source_refs"],
        "resolved": validation["resolved_seed_source_refs"],
        "unresolved": validation["unresolved_seed_source_refs"],
        "g02_completion_claim": validation["g02_completion_claim"],
    }, indent=2))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
