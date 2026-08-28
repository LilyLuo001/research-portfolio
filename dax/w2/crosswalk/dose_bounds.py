"""Fail-closed construction of CPS occupation dose intervals.

Crosswalk mapping weights are point weights only when a whole CPS OCC2010 code
is ``resolved_employment_weighted``.  Equal SOC/O*NET weights and equal legacy
source weights are diagnostic centers.  This module converts those diagnostic
centers to explicit intervals before any downstream estimator can use them.
"""

from __future__ import annotations

import csv
import dataclasses
import math
import pathlib
from collections import defaultdict
from collections.abc import Iterable, Mapping


@dataclasses.dataclass(frozen=True)
class DoseInterval:
    """A diagnostic center and the source-supported closed interval."""

    center: float
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        values = (self.minimum, self.center, self.maximum)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"dose interval contains a non-finite value: {values}")
        if self.minimum > self.center or self.center > self.maximum:
            raise ValueError(
                "dose interval must satisfy minimum <= center <= maximum: "
                f"{values}"
            )

    @classmethod
    def point(cls, value: float) -> "DoseInterval":
        return cls(float(value), float(value), float(value))

    @property
    def is_point(self) -> bool:
        return math.isclose(self.minimum, self.maximum, abs_tol=1e-12)


@dataclasses.dataclass(frozen=True)
class CpsDose:
    """Downstream dose record; only resolved codes expose ``point_estimate``."""

    cps_occ2010: str
    status: str
    diagnostic_center: float | None
    dose_min: float | None
    dose_max: float | None
    point_estimate: float | None
    downstream_eligible: bool


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"expected true/false, got {value!r}")
    return normalized == "true"


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def legacy_profile_intervals(
    fallback_rows: Iterable[Mapping[str, object]],
    task_doses: Mapping[tuple[str, str], float],
) -> dict[str, DoseInterval]:
    """Bound each 2019 legacy profile across its official 2010 sources.

    ``task_doses`` is indexed by ``(onet_soc2010, task_id)``.  The committed
    equal source mix is retained only as ``center``; minimum and maximum are
    taken across the independently constructed source profiles.
    """

    rows_by_new_source: dict[
        tuple[str, str], list[Mapping[str, object]]
    ] = defaultdict(list)
    for row in fallback_rows:
        if not _as_bool(row["bounds_required"]):
            raise ValueError("every legacy fallback row must require bounds")
        new_code = str(row["onet_soc2019"]).strip()
        old_code = str(row["onet_soc2010"]).strip()
        rows_by_new_source[(new_code, old_code)].append(row)

    source_profiles: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for (new_code, old_code), rows in sorted(rows_by_new_source.items()):
        shares = [float(row["legacy_task_time_share"]) for row in rows]
        if not math.isclose(sum(shares), 1.0, abs_tol=1e-9):
            raise ValueError(
                f"legacy task shares for {new_code}/{old_code} do not sum to one"
            )
        source_weights = {float(row["legacy_source_weight"]) for row in rows}
        if len(source_weights) != 1:
            raise ValueError(
                f"legacy source weight changes within {new_code}/{old_code}"
            )
        source_dose = 0.0
        for row, share in zip(rows, shares):
            key = (old_code, str(row["task_id"]).strip())
            if key not in task_doses:
                raise ValueError(f"missing task dose for legacy source task {key}")
            source_dose += share * float(task_doses[key])
        source_profiles[new_code].append((source_weights.pop(), source_dose))

    result = {}
    for new_code, profiles in sorted(source_profiles.items()):
        if not math.isclose(sum(weight for weight, _ in profiles), 1.0, abs_tol=1e-9):
            raise ValueError(f"legacy source weights for {new_code} do not sum to one")
        doses = [dose for _, dose in profiles]
        result[new_code] = DoseInterval(
            center=sum(weight * dose for weight, dose in profiles),
            minimum=min(doses),
            maximum=max(doses),
        )
    return result


def _validate_code_rows(code: str, rows: list[Mapping[str, object]]) -> str:
    statuses = {str(row["cps_code_status"]).strip() for row in rows}
    if len(statuses) != 1:
        raise ValueError(f"CPS code {code} has inconsistent whole-code statuses")
    code_status = statuses.pop()
    expected_eligibility = code_status == "resolved_employment_weighted"
    for row in rows:
        if _as_bool(row["downstream_eligible"]) != expected_eligibility:
            raise ValueError(
                f"CPS code {code} violates the whole-code eligibility rule"
            )
    return code_status


def _interval_for_group(
    rows: list[Mapping[str, object]],
    onet_intervals: Mapping[str, DoseInterval],
) -> DoseInterval:
    weighted_center = 0.0
    intervals = []
    total_weight = 0.0
    for row in rows:
        onet = str(row["onet_soc2019"]).strip()
        if not onet or onet not in onet_intervals:
            raise ValueError(f"missing O*NET dose interval for {onet or '<blank>'}")
        weight = float(row["mapping_weight"])
        interval = onet_intervals[onet]
        total_weight += weight
        weighted_center += weight * interval.center
        intervals.append(interval)
    if total_weight <= 0:
        raise ValueError("bounded component has non-positive total weight")
    return DoseInterval(
        center=weighted_center,
        minimum=total_weight * min(item.minimum for item in intervals),
        maximum=total_weight * max(item.maximum for item in intervals),
    )


def construct_cps_doses(
    crosswalk_rows: Iterable[Mapping[str, object]],
    onet_intervals: Mapping[str, DoseInterval],
    expected_cps_codes: Iterable[str] = (),
) -> dict[str, CpsDose]:
    """Construct point doses or mandatory intervals under the frozen standard.

    Unresolved and absent CPS codes return no center, interval, or point.  A
    provisional code returns a center plus min/max bounds, never a point.  A
    resolved code returns a point only if every linked O*NET input is itself a
    degenerate interval.
    """

    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in crosswalk_rows:
        grouped[str(row["cps_occ2010"]).strip().zfill(4)].append(row)

    result: dict[str, CpsDose] = {}
    all_codes = sorted(set(grouped) | {str(code).strip().zfill(4)
                                      for code in expected_cps_codes})
    for code in all_codes:
        rows = grouped.get(code, [])
        if not rows:
            result[code] = CpsDose(
                code, "absent_from_crosswalk", None, None, None, None, False
            )
            continue
        code_status = _validate_code_rows(code, rows)
        if code_status in {"unresolved", "partial_unresolved"} or any(
            str(row["route_status"]).startswith("unresolved_") for row in rows
        ):
            result[code] = CpsDose(
                code, code_status, None, None, None, None, False
            )
            continue

        components: list[DoseInterval] = []
        consumed: set[int] = set()

        # Missing OEWS employment makes the whole official SOC child set for a
        # Census route uncertain, so bind all children of that route together.
        equal_soc_groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
        # Equal O*NET subdivisions are uncertain only within their SOC child.
        equal_onet_groups: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
        # A SOC can contain several current/legacy children. The builder labels
        # the whole set legacy-provisional if any child uses the dated bridge;
        # bind across both the linked children and each child's source interval.
        legacy_groups: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
        for index, row in enumerate(rows):
            route_status = str(row["route_status"])
            base = (
                str(row["census_2018_occ"]),
                str(row["soc_2018_pattern"]),
                str(row["base_route_weight"]),
            )
            if route_status == "provisional_equal_soc_missing_oews":
                equal_soc_groups[base].append(index)
            elif route_status == "provisional_equal_within_soc":
                equal_onet_groups[base + (str(row["soc_2018"]),)].append(index)
            elif route_status == "provisional_legacy_task_ratings":
                legacy_groups[base + (str(row["soc_2018"]),)].append(index)

        for indexes in equal_soc_groups.values():
            components.append(_interval_for_group([rows[i] for i in indexes], onet_intervals))
            consumed.update(indexes)
        for indexes in equal_onet_groups.values():
            components.append(_interval_for_group([rows[i] for i in indexes], onet_intervals))
            consumed.update(indexes)
        for indexes in legacy_groups.values():
            components.append(_interval_for_group([rows[i] for i in indexes], onet_intervals))
            consumed.update(indexes)

        for index, row in enumerate(rows):
            if index in consumed:
                continue
            route_status = str(row["route_status"])
            if route_status != "resolved_employment_weighted":
                raise ValueError(
                    f"unsupported route status {route_status!r} for CPS code {code}"
                )
            onet = str(row["onet_soc2019"]).strip()
            if onet not in onet_intervals:
                raise ValueError(f"missing O*NET dose interval for {onet}")
            interval = onet_intervals[onet]
            weight = float(row["mapping_weight"])
            components.append(DoseInterval(
                center=weight * interval.center,
                minimum=weight * interval.minimum,
                maximum=weight * interval.maximum,
            ))

        center = sum(component.center for component in components)
        minimum = sum(component.minimum for component in components)
        maximum = sum(component.maximum for component in components)
        if code_status == "resolved_employment_weighted":
            if any(not component.is_point for component in components):
                raise ValueError(
                    f"resolved CPS code {code} received a bounded O*NET input"
                )
            result[code] = CpsDose(
                code, code_status, center, minimum, maximum, center, True
            )
        else:
            result[code] = CpsDose(
                code, code_status, center, minimum, maximum, None, False
            )
    return result
