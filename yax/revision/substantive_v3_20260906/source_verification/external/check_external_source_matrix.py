#!/usr/bin/env python3
"""Mechanical integrity checks for the external source/claim matrix.

This check intentionally requires the full ten-journal search to remain marked
incomplete. A PASS means the bounded verification record is internally sound;
it is not a novelty-gate pass and does not convert unresolved searches into
completed work.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


MATRIX = Path(__file__).with_name("source_claim_matrix.json")
REQUIREMENTS = {"B01", "B02", "B05", "B07", "B09", "F07"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "created_date",
    "accessed_date",
    "requirements_in_scope",
    "purpose",
    "full_ten_journal_search_complete",
    "ten_journal_search_status",
    "sources",
    "unresolved_items",
}
SOURCE_FIELDS = {
    "source_id",
    "requirement_ids",
    "title",
    "publisher",
    "source_type",
    "url",
    "accessed_date",
    "published_or_updated",
    "verification_status",
    "exact_supported_claims",
    "version_endpoint_distinctions",
    "limitations",
}
UNRESOLVED_FIELDS = {
    "requirement_ids",
    "status",
    "issue",
    "consequence",
    "next_authorized_step",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def nonempty_strings(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def main() -> int:
    errors: list[str] = []

    try:
        data = json.loads(MATRIX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read valid JSON from {MATRIX}: {exc}", file=sys.stderr)
        return 1

    missing_top = TOP_LEVEL_FIELDS - set(data)
    if missing_top:
        errors.append(f"missing top-level fields: {sorted(missing_top)}")

    if data.get("full_ten_journal_search_complete") is not False:
        errors.append(
            "full_ten_journal_search_complete must be exactly false; "
            "the full search has not been completed"
        )

    search_status = data.get("ten_journal_search_status", "")
    if not isinstance(search_status, str) or "INCOMPLETE" not in search_status.upper():
        errors.append("ten_journal_search_status must explicitly say INCOMPLETE")

    declared_requirements = set(data.get("requirements_in_scope", []))
    if declared_requirements != REQUIREMENTS:
        errors.append(
            "requirements_in_scope must equal "
            f"{sorted(REQUIREMENTS)}, found {sorted(declared_requirements)}"
        )

    if not DATE_RE.fullmatch(str(data.get("accessed_date", ""))):
        errors.append("top-level accessed_date must use YYYY-MM-DD")

    sources = data.get("sources", [])
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a nonempty list")
        sources = []

    source_ids: list[str] = []
    urls: list[str] = []
    covered_requirements: set[str] = set()

    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be an object")
            continue

        missing = SOURCE_FIELDS - set(source)
        if missing:
            errors.append(f"{label} missing fields: {sorted(missing)}")

        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"{label}.source_id must be a nonempty string")
        else:
            source_ids.append(source_id)
            label = source_id

        requirement_ids = source.get("requirement_ids", [])
        if not nonempty_strings(requirement_ids):
            errors.append(f"{label}.requirement_ids must be a nonempty string list")
        else:
            unknown = set(requirement_ids) - REQUIREMENTS
            if unknown:
                errors.append(f"{label} has unknown requirements: {sorted(unknown)}")
            covered_requirements.update(requirement_ids)

        url = source.get("url")
        if not isinstance(url, str) or not url.strip():
            errors.append(f"{label}.url must be a nonempty string")
        else:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"{label}.url must be an absolute HTTPS URL: {url}")
            urls.append(url)

        if not DATE_RE.fullmatch(str(source.get("accessed_date", ""))):
            errors.append(f"{label}.accessed_date must use YYYY-MM-DD")

        for field in (
            "exact_supported_claims",
            "version_endpoint_distinctions",
            "limitations",
        ):
            if not nonempty_strings(source.get(field)):
                errors.append(f"{label}.{field} must be a nonempty string list")

        for field in (
            "title",
            "publisher",
            "source_type",
            "published_or_updated",
            "verification_status",
        ):
            if not isinstance(source.get(field), str) or not source[field].strip():
                errors.append(f"{label}.{field} must be a nonempty string")

    duplicated_ids = sorted({item for item in source_ids if source_ids.count(item) > 1})
    if duplicated_ids:
        errors.append(f"duplicate source_id values: {duplicated_ids}")

    duplicated_urls = sorted({item for item in urls if urls.count(item) > 1})
    if duplicated_urls:
        errors.append(f"duplicate canonical URLs: {duplicated_urls}")

    missing_coverage = REQUIREMENTS - covered_requirements
    if missing_coverage:
        errors.append(f"requirements without a source record: {sorted(missing_coverage)}")

    unresolved = data.get("unresolved_items", [])
    if not isinstance(unresolved, list) or not unresolved:
        errors.append("unresolved_items must be a nonempty list")
        unresolved = []

    incomplete_search_recorded = False
    for index, item in enumerate(unresolved):
        label = f"unresolved_items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = UNRESOLVED_FIELDS - set(item)
        if missing:
            errors.append(f"{label} missing fields: {sorted(missing)}")
        requirement_ids = item.get("requirement_ids", [])
        if not nonempty_strings(requirement_ids):
            errors.append(f"{label}.requirement_ids must be a nonempty string list")
        elif set(requirement_ids) - REQUIREMENTS:
            errors.append(f"{label} has unknown requirement IDs")
        for field in ("status", "issue", "consequence", "next_authorized_step"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{label}.{field} must be a nonempty string")
        if "B09" in requirement_ids and "INCOMPLETE" in str(item.get("status", "")).upper():
            incomplete_search_recorded = True

    if not incomplete_search_recorded:
        errors.append("an unresolved B09 INCOMPLETE_SEARCH record is required")

    if errors:
        print("FAIL: external source matrix integrity check", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("PASS: external source matrix integrity check")
    print(f"- {len(sources)} unique source records")
    print(f"- {len(urls)} unique canonical HTTPS URLs")
    print(f"- requirements covered: {', '.join(sorted(covered_requirements))}")
    print("- full ten-journal search remains INCOMPLETE (explicitly and correctly recorded)")
    print("- this PASS is an artifact-integrity result, not a novelty-gate result")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
