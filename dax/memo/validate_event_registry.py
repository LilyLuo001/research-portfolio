"""Fail-closed structural checks for the DAX W1 event registry.

This validator checks provenance shape only. It does not claim that a URL's
content independently verifies a date; that judgment is recorded explicitly
in ``verification_status`` and remains part of W1 review.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib
import re
import sys


REGISTRY = pathlib.Path(__file__).with_name("event_registry_v1.csv")
PRICE_PANEL = REGISTRY.parent.parent / "data_built" / "price_histories.csv"
START = dt.date(2021, 11, 1)
FREEZE_DATE = dt.date(2026, 8, 6)
EVENT_ID = re.compile(r"^[A-Z][A-Z0-9_]*$")
ANALYSIS_STATUSES = {"eligible", "candidate", "excluded_binding"}
VERIFICATION_STATUSES = {"verified", "pending_second_date_locator"}
PRICE_STATUSES = {
    "verified_w2", "relative_price_verified", "pending_w2", "conflict_b", "n_a"
}
REQUIRED = {
    "event_id",
    "api_effective_date",
    "classification",
    "model_ids",
    "analysis_status",
    "verification_status",
    "price_status",
    "source_1",
    "source_2",
    "date_conflict",
    "notes",
}


def validate(path: pathlib.Path = REGISTRY) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        if fields != REQUIRED:
            errors.append(
                f"header mismatch: missing={sorted(REQUIRED - fields)} "
                f"extra={sorted(fields - REQUIRED)}"
            )
        rows = list(reader)

    panel_statuses: dict[str, set[str]] = {}
    price_panel = path.parent.parent / "data_built" / "price_histories.csv"
    if price_panel.is_file():
        with price_panel.open(newline="", encoding="utf-8") as handle:
            for price_row in csv.DictReader(handle):
                panel_statuses.setdefault(price_row["model_id"], set()).add(
                    price_row["price_status"]
                )

    seen: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        event_id = row.get("event_id", "")
        prefix = f"line {line_number} ({event_id or 'missing event_id'})"
        if not EVENT_ID.fullmatch(event_id):
            errors.append(f"{prefix}: invalid event_id")
        if event_id in seen:
            errors.append(f"{prefix}: duplicate event_id")
        seen.add(event_id)

        try:
            event_date = dt.date.fromisoformat(row.get("api_effective_date", ""))
        except ValueError:
            errors.append(f"{prefix}: invalid ISO api_effective_date")
        else:
            if not START <= event_date <= FREEZE_DATE:
                errors.append(
                    f"{prefix}: event date {event_date} outside frozen registry window"
                )

        analysis_status = row.get("analysis_status", "")
        verification_status = row.get("verification_status", "")
        price_status = row.get("price_status", "")
        if analysis_status not in ANALYSIS_STATUSES:
            errors.append(f"{prefix}: invalid analysis_status={analysis_status!r}")
        if verification_status not in VERIFICATION_STATUSES:
            errors.append(
                f"{prefix}: invalid verification_status={verification_status!r}"
            )
        if price_status not in PRICE_STATUSES:
            errors.append(f"{prefix}: invalid price_status={price_status!r}")
        if price_status != "n_a" and panel_statuses:
            models = [m.strip() for m in row.get("model_ids", "").split("|") if m.strip()]
            fully_verified = bool(models) and all(
                panel_statuses.get(model) == {"verified"} for model in models
            )
            if price_status == "verified_w2" and not fully_verified:
                errors.append(
                    f"{prefix}: verified_w2 but one or more model price rows are not verified"
                )
            if fully_verified and price_status != "verified_w2":
                errors.append(
                    f"{prefix}: all model price rows are verified but registry is "
                    f"{price_status!r}, not 'verified_w2'"
                )
        if analysis_status == "eligible" and verification_status != "verified":
            errors.append(f"{prefix}: eligible event is not date-verified")
        if analysis_status == "excluded_binding" and not row.get("notes", "").strip():
            errors.append(f"{prefix}: binding exclusion lacks rationale")

        # F2 (2026-08-18): a second locator that cannot date the RELEASE may not
        # support `verified`. A model page confirms identity; a deprecations page
        # dates retirement; a pricing page carries no history. Such a row may only
        # be verified when the model snapshot id itself embeds a date matching
        # api_effective_date. This is the standard the memo already states for
        # GPT56_FAMILY_LAUNCH, now enforced instead of applied by hand.
        weak_second = any(token in row.get("source_2", "")
                          for token in ("/models/", "deprecations", "pricing"))
        dated_slugs = [s for s in row.get("model_ids", "").split("|")
                       if re.search(r"\d{4}-\d{2}-\d{2}", s)]
        slug_dates_it = any(row.get("api_effective_date", "") in s for s in dated_slugs)
        if (row.get("verification_status") == "verified"
                and weak_second and not slug_dates_it):
            errors.append(
                f"{prefix}: verified on a second locator that cannot date the "
                f"release, and no dated snapshot id matches api_effective_date"
            )

        conflict = row.get("date_conflict", "").strip()
        if conflict and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", conflict):
            errors.append(f"{prefix}: date_conflict must be an ISO date or blank")
        if conflict and conflict == row.get("api_effective_date"):
            errors.append(f"{prefix}: date_conflict duplicates api_effective_date")

        sources = [row.get("source_1", "").strip(), row.get("source_2", "").strip()]
        if any(not source.startswith("https://") for source in sources):
            errors.append(f"{prefix}: both sources must be HTTPS locators")
        if len(set(sources)) != 2:
            errors.append(f"{prefix}: source locators must be distinct")
        for field in REQUIRED - {"date_conflict"}:   # blank means "no conflict"
            if not row.get(field, "").strip():
                errors.append(f"{prefix}: blank required field {field}")

    return rows, errors


def main() -> int:
    rows, errors = validate()
    if errors:
        print("event registry FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["analysis_status"]] = counts.get(row["analysis_status"], 0) + 1
    pending = sum(
        row["verification_status"] == "pending_second_date_locator" for row in rows
    )
    print(
        "event registry PASSED — "
        f"{len(rows)} rows; "
        f"eligible={counts.get('eligible', 0)}, "
        f"candidate={counts.get('candidate', 0)}, "
        f"excluded={counts.get('excluded_binding', 0)}, "
        f"pending_second_date_locator={pending}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
