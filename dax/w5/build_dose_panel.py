"""Fail-closed construction of the private DAX W5 dose panel.

The constructor intentionally accepts no outcome data. It emits retained
event x OCC2010 bounded components plus a separate exclusion audit. No event
can enter dose construction unless its written dated-evidence verdict is
frozen as retained, and no unresolved crosswalk mass is converted to zero or
to a resolved point.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping


EVENT_DATE_PASS = "written_dated_verified"
EVENT_RETAINED = "retained"
RESOLVED = "resolved_employment_weighted"
PROVISIONAL_PREFIX = "provisional_"
UNRESOLVED_STATUSES = {
    "unresolved",
    "partial_unresolved",
    "absent_from_crosswalk",
}
FORBIDDEN_COLUMN_TOKENS = {
    "outcome",
    "employment",
    "employed",
    "empstat",
    "wage",
    "earnings",
    "hours",
    "uhrsworkt",
    "labor_force",
    "post_event",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
OCC2010 = re.compile(r"^\d{4}$")


class PanelContractError(ValueError):
    """Raised when an input would violate the frozen W5 panel contract."""


def _text(row: Mapping[str, object], field: str) -> str:
    value = str(row.get(field, "")).strip()
    if not value:
        raise PanelContractError(f"blank required field {field}")
    return value


def _number(row: Mapping[str, object], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as error:
        raise PanelContractError(f"invalid numeric field {field}") from error
    if not math.isfinite(value):
        raise PanelContractError(f"non-finite numeric field {field}")
    return value


def _positive_count(row: Mapping[str, object], field: str) -> int:
    value = _number(row, field)
    if value < 1 or not value.is_integer():
        raise PanelContractError(f"{field} must be a positive integer")
    return int(value)


def _hash(row: Mapping[str, object], field: str) -> str:
    value = _text(row, field).lower()
    if not SHA256.fullmatch(value):
        raise PanelContractError(f"{field} must be a lowercase SHA-256")
    return value


def _reject_outcome_columns(rows: Iterable[Mapping[str, object]], label: str) -> None:
    for row in rows:
        forbidden = sorted(
            str(column)
            for column in row
            if any(token in str(column).lower() for token in FORBIDDEN_COLUMN_TOKENS)
        )
        if forbidden:
            raise PanelContractError(
                f"{label} contains outcome-like columns before unsealing: {forbidden}"
            )


def _interval(row: Mapping[str, object], prefix: str) -> tuple[float, float, float]:
    lower = _number(row, f"{prefix}_lower")
    center = _number(row, f"{prefix}_center")
    upper = _number(row, f"{prefix}_upper")
    if lower < 0 or not lower <= center <= upper:
        raise PanelContractError(
            f"{prefix} interval must satisfy 0 <= lower <= center <= upper"
        )
    return lower, center, upper


def _lineage(row: Mapping[str, object], stem: str) -> tuple[str, str, int]:
    return (
        _text(row, f"{stem}_version"),
        _hash(row, f"{stem}_sha256"),
        _positive_count(row, f"{stem}_row_count"),
    )


def stable_row_id(
    panel_version: str, event_id: str, cps_occ2010: str, component_id: str
) -> str:
    payload = "\x1f".join((panel_version, event_id, cps_occ2010, component_id))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _event_exclusion(row: Mapping[str, object]) -> dict[str, object]:
    reason = _text(row, "exclusion_reason")
    return {
        "entity_type": "event",
        "entity_id": _text(row, "event_id"),
        "status": _text(row, "event_inclusion_status"),
        "reason": reason,
        "event_date_status": _text(row, "event_date_status"),
        "price_evidence_status": _text(row, "price_evidence_status"),
    }


def _occupation_exclusion(row: Mapping[str, object]) -> dict[str, object]:
    reason = _text(row, "exclusion_reason")
    return {
        "entity_type": "occupation",
        "entity_id": str(row.get("cps_occ2010", "")).strip().zfill(4),
        "status": _text(row, "crosswalk_status"),
        "reason": reason,
    }


def build_panel(
    events: Iterable[Mapping[str, object]],
    components: Iterable[Mapping[str, object]],
    *,
    panel_version: str,
    build_code_version: str,
    build_code_sha256: str,
    tolerance: float = 1e-10,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Build retained event x occupation components and exclusion records.

    Component intervals are already uncertainty groups from the frozen
    crosswalk standard. Event intervals are multiplied into them; all inputs
    are constrained nonnegative, so endpoint multiplication is valid.
    """

    event_rows = [dict(row) for row in events]
    component_rows = [dict(row) for row in components]
    _reject_outcome_columns(event_rows, "event input")
    _reject_outcome_columns(component_rows, "component input")
    if not panel_version.strip() or not build_code_version.strip():
        raise PanelContractError("panel and build-code versions must be nonblank")
    if not SHA256.fullmatch(build_code_sha256):
        raise PanelContractError("build_code_sha256 must be a lowercase SHA-256")
    if tolerance <= 0:
        raise PanelContractError("tolerance must be positive")

    retained_events: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    seen_events: set[str] = set()
    for event in event_rows:
        event_id = _text(event, "event_id")
        if event_id in seen_events:
            raise PanelContractError(f"duplicate event_id {event_id}")
        seen_events.add(event_id)
        try:
            dt.date.fromisoformat(_text(event, "event_date"))
        except ValueError as error:
            raise PanelContractError(f"invalid event_date for {event_id}") from error
        date_status = _text(event, "event_date_status")
        inclusion = _text(event, "event_inclusion_status")
        _text(event, "price_evidence_status")
        _lineage(event, "event_evidence")
        _lineage(event, "price_input")
        if inclusion == EVENT_RETAINED and date_status == EVENT_DATE_PASS:
            if str(event.get("exclusion_reason", "")).strip():
                raise PanelContractError(f"retained event {event_id} has exclusion_reason")
            _interval(event, "event_multiplier")
            retained_events.append(event)
        else:
            exclusions.append(_event_exclusion(event))

    eligible_components: list[dict[str, object]] = []
    seen_components: set[tuple[str, str]] = set()
    for component in component_rows:
        code = str(component.get("cps_occ2010", "")).strip().zfill(4)
        if not OCC2010.fullmatch(code):
            raise PanelContractError(f"invalid cps_occ2010 {code!r}")
        component["cps_occ2010"] = code
        component_id = _text(component, "component_id")
        key = (code, component_id)
        if key in seen_components:
            raise PanelContractError(f"duplicate occupation component {key}")
        seen_components.add(key)
        status = _text(component, "crosswalk_status")
        _text(component, "route_status")
        _lineage(component, "mapping_input")
        _lineage(component, "dose_input")
        if status in UNRESOLVED_STATUSES or status.startswith("unresolved_"):
            exclusions.append(_occupation_exclusion(component))
            continue
        lower, center, upper = _interval(component, "component_dose")
        weight = _number(component, "component_weight")
        if not 0 <= weight <= 1:
            raise PanelContractError("component_weight must lie in [0, 1]")
        if status.startswith(PROVISIONAL_PREFIX) and math.isclose(
            lower, upper, abs_tol=tolerance
        ):
            raise PanelContractError(
                f"provisional occupation {code} component {component_id} requires bounds"
            )
        if status != RESOLVED and not status.startswith(PROVISIONAL_PREFIX):
            raise PanelContractError(f"unsupported crosswalk_status {status!r}")
        if str(component.get("exclusion_reason", "")).strip():
            raise PanelContractError(f"eligible occupation {code} has exclusion_reason")
        eligible_components.append(component)

    weights: dict[str, float] = defaultdict(float)
    for component in eligible_components:
        weights[str(component["cps_occ2010"])] += _number(
            component, "component_weight"
        )
    for code, total in weights.items():
        if not math.isclose(total, 1.0, abs_tol=tolerance):
            raise PanelContractError(
                f"component weights for {code} sum to {total}, expected 1"
            )

    panel: list[dict[str, object]] = []
    for event in retained_events:
        event_interval = _interval(event, "event_multiplier")
        pending: list[dict[str, object]] = []
        totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
        for component in eligible_components:
            component_interval = _interval(component, "component_dose")
            weight = _number(component, "component_weight")
            doses = tuple(
                weight * event_value * component_value
                for event_value, component_value in zip(event_interval, component_interval)
            )
            code = str(component["cps_occ2010"])
            for index, value in enumerate(doses):
                totals[code][index] += value
            pending.append({
                "panel_row_id": stable_row_id(
                    panel_version,
                    str(event["event_id"]),
                    code,
                    str(component["component_id"]),
                ),
                "panel_version": panel_version,
                "event_id": event["event_id"],
                "event_date": event["event_date"],
                "event_date_status": event["event_date_status"],
                "event_evidence_version": event["event_evidence_version"],
                "event_evidence_sha256": event["event_evidence_sha256"],
                "event_evidence_row_count": int(event["event_evidence_row_count"]),
                "price_evidence_status": event["price_evidence_status"],
                "price_input_version": event["price_input_version"],
                "price_input_sha256": event["price_input_sha256"],
                "price_input_row_count": int(event["price_input_row_count"]),
                "cps_occ2010": code,
                "component_id": component["component_id"],
                "crosswalk_status": component["crosswalk_status"],
                "route_status": component["route_status"],
                "component_weight": weight,
                "dose_lower": doses[0],
                "dose_center": doses[1],
                "dose_upper": doses[2],
                "mapping_input_version": component["mapping_input_version"],
                "mapping_input_sha256": component["mapping_input_sha256"],
                "mapping_input_row_count": int(component["mapping_input_row_count"]),
                "dose_input_version": component["dose_input_version"],
                "dose_input_sha256": component["dose_input_sha256"],
                "dose_input_row_count": int(component["dose_input_row_count"]),
                "build_code_version": build_code_version,
                "build_code_sha256": build_code_sha256,
                "exclusion_reason": "",
            })
        for row in pending:
            total = totals[str(row["cps_occ2010"])]
            row["occupation_total_lower"] = total[0]
            row["occupation_total_center"] = total[1]
            row["occupation_total_upper"] = total[2]
            panel.append(row)

    validate_panel(panel, tolerance=tolerance)
    return sorted(panel, key=lambda row: str(row["panel_row_id"])), exclusions


def validate_panel(
    rows: Iterable[Mapping[str, object]], *, tolerance: float = 1e-10
) -> None:
    """Validate interval order, stable IDs, lineage, and group reconciliation."""

    panel = [dict(row) for row in rows]
    _reject_outcome_columns(panel, "constructed panel")
    seen: set[str] = set()
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in panel:
        row_id = _text(row, "panel_row_id")
        expected = stable_row_id(
            _text(row, "panel_version"),
            _text(row, "event_id"),
            _text(row, "cps_occ2010"),
            _text(row, "component_id"),
        )
        if row_id != expected:
            raise PanelContractError(f"unstable or invalid panel_row_id {row_id}")
        if row_id in seen:
            raise PanelContractError(f"duplicate panel_row_id {row_id}")
        seen.add(row_id)
        if _text(row, "event_date_status") != EVENT_DATE_PASS:
            raise PanelContractError("panel contains an event that failed the date gate")
        if str(row.get("exclusion_reason", "")).strip():
            raise PanelContractError("retained panel row has an exclusion reason")
        for stem in ("event_evidence", "price_input", "mapping_input", "dose_input"):
            _lineage(row, stem)
        _text(row, "build_code_version")
        _hash(row, "build_code_sha256")
        lower = _number(row, "dose_lower")
        center = _number(row, "dose_center")
        upper = _number(row, "dose_upper")
        if lower < 0 or not lower <= center <= upper:
            raise PanelContractError("panel dose bounds are unordered")
        grouped[(_text(row, "event_id"), _text(row, "cps_occ2010"))].append(row)

    for key, group in grouped.items():
        sums = [sum(_number(row, field) for row in group) for field in (
            "dose_lower", "dose_center", "dose_upper"
        )]
        reported = [
            {_number(row, field) for row in group}
            for field in (
                "occupation_total_lower",
                "occupation_total_center",
                "occupation_total_upper",
            )
        ]
        if any(len(values) != 1 for values in reported):
            raise PanelContractError(f"inconsistent occupation totals for {key}")
        for calculated, values in zip(sums, reported):
            if not math.isclose(calculated, values.pop(), abs_tol=tolerance):
                raise PanelContractError(f"component totals do not reconcile for {key}")


def audit_crosswalk_mass(
    occupations: Iterable[Mapping[str, object]],
    *,
    expected_provisional_share: float | None = None,
    tolerance: float = 1e-6,
) -> dict[str, float]:
    """Audit status mass without treating unresolved/provisional as resolved."""

    rows = [dict(row) for row in occupations]
    _reject_outcome_columns(rows, "crosswalk mass input")
    total = sum(_number(row, "occupation_mass") for row in rows)
    if total <= 0:
        raise PanelContractError("occupation mass total must be positive")
    masses = {"resolved": 0.0, "provisional": 0.0, "unresolved": 0.0}
    for row in rows:
        mass = _number(row, "occupation_mass")
        if mass < 0:
            raise PanelContractError("occupation_mass must be nonnegative")
        status = _text(row, "crosswalk_status")
        if status == RESOLVED:
            bucket = "resolved"
        elif status.startswith(PROVISIONAL_PREFIX):
            lower, _, upper = _interval(row, "dose")
            if math.isclose(lower, upper, abs_tol=tolerance):
                raise PanelContractError("provisional mass lacks nondegenerate bounds")
            bucket = "provisional"
        elif status in UNRESOLVED_STATUSES or status.startswith("unresolved_"):
            bucket = "unresolved"
        else:
            raise PanelContractError(f"unsupported crosswalk_status {status!r}")
        masses[bucket] += mass
    shares = {f"{key}_mass_share": value / total for key, value in masses.items()}
    if not math.isclose(sum(shares.values()), 1.0, abs_tol=tolerance):
        raise PanelContractError("crosswalk status mass does not reconcile")
    if expected_provisional_share is not None and not math.isclose(
        shares["provisional_mass_share"], expected_provisional_share,
        abs_tol=tolerance,
    ):
        raise PanelContractError(
            "provisional mass share differs from the frozen standard: "
            f"{shares['provisional_mass_share']} != {expected_provisional_share}"
        )
    return shares
