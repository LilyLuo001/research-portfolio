"""Bounded V6 repair layered on the frozen V5 candidate parser.

V6 makes one concentrated education/experience repair.  The underlying V5
source remains immutable and is loaded by path.  Additions are grammatical or
structural; no job identifiers or diagnostic row identifiers are embedded.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path
from typing import Any, Dict, List


BASE_PATH = Path(__file__).resolve().parents[1] / "stage_c_v5" / "requirement_candidates.py"
BASE_SHA256 = "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd"
if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != BASE_SHA256:
    raise RuntimeError("frozen V5 base parser SHA-256 mismatch")
_spec = importlib.util.spec_from_file_location("linkup_frozen_v5_base", str(BASE_PATH))
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load frozen V5 base parser")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

NORMALIZATION_VERSION = "recruitment-html-text-v6"
_base.NORMALIZATION_VERSION = NORMALIZATION_VERSION

# Qualification field headings observed in ordinary exports.  These are
# structural labels, not claims of mandatory strength unless the label says so.
_base._HEADING_RULES = (
    ("required", re.compile(r"^(?:required skills?|minimum education\s*/\s*experience requirements?)(?:\s*:)?$", re.I)),
    ("qualification_unspecified", re.compile(r"^job specifications?(?:\s*:)?$", re.I)),
) + _base._HEADING_RULES
_base._INLINE_HEADING_RULES = (
    ("required", r"required skills?|minimum education\s*/\s*experience requirements?"),
    ("qualification_unspecified", r"job specifications?"),
) + _base._INLINE_HEADING_RULES

_old_embedded = _base._EMBEDDED_HEADING
_embedded_pattern = (
    r"(?P<label>Minimum Education/Experience Requirements|" +
    _old_embedded.pattern.split("(?P<label>", 1)[1]
)
_embedded_pattern = _embedded_pattern.replace(
    r"|\s*(?=[•]))",
    r"|\s+(?=(?:A|An|The)\s+[A-Z])|\s*(?=[•]))",
)
_base._EMBEDDED_HEADING = re.compile(_embedded_pattern, _old_embedded.flags)
_base._EMBEDDED_HEADING_CONTEXT["minimum education/experience requirements"] = "required"

# Extend one existing credential family without treating generic school
# references as qualifications.
_base._DEGREES = tuple(
    (level, pattern.replace(
        "high school diploma|high school degree|high school graduate",
        "high school diploma|high school degree|high school graduate|high school or equivalent",
    ) if level == "high_school" else pattern)
    for level, pattern in _base._DEGREES
)
_base._DEGREE_MARKER = re.compile(
    _base._DEGREE_MARKER.pattern.replace(
        "high school (?:diploma|degree|graduate)",
        "high school (?:diploma|degree|graduate|or equivalent)",
    ),
    _base._DEGREE_MARKER.flags,
)

_CURRENT_ENROLLMENT = re.compile(
    r"\bcurrent\s+(?:(?:first|second|third|fourth|1st|2nd|3rd|4th)\s+year"
    r"(?:\s*,\s*(?:(?:first|second|third|fourth|1st|2nd|3rd|4th)\s+year))*"
    r"(?:\s*,?\s*(?:or|and)\s*(?:(?:first|second|third|fourth|1st|2nd|3rd|4th)\s+year))?"
    r"|undergraduate|graduate|college|university)\s+student\b",
    re.I,
)


def _line_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    left = text.rfind("\n", 0, start) + 1
    right = text.find("\n", end)
    return left, len(text) if right < 0 else right


def _add_current_enrollment(payload: Dict[str, Any]) -> None:
    normalized = payload["normalized_text"]
    additions: List[Dict[str, Any]] = []
    for match in _CURRENT_ENROLLMENT.finditer(normalized):
        additions.append(_base._evidence(
            normalized, "education", "education_enrollment_eligibility",
            "current_enrollment", match.start(), match.end(),
            "unknown", degree_level="current_enrollment",
            education_status="current_enrollment", attained_degree=False,
            matched_text=match.group(0), equivalent_experience=False,
            equivalent_credential=False, equivalence_type="none",
            alternative_path_text=None, alternative_training_or_experience=False,
            alternatives_retained=True, negated=False, negated_or_optional=False,
            ambiguous_degree_abbreviation=False,
            qualification_relation_unresolved=False,
            is_unconditional_education_requirement=False,
            qualification_scope_text=match.group(0),
            qualification_scope_start=match.start(),
            qualification_scope_end=match.end(),
            qualification_scope_rule="current_enrollment_phrase",
            local_path_scope_applied=False, alternative_scope_local=True,
            mixed_requirement_scope=False, context_conflict=False,
            is_applicant_requirement=False,
            is_applicant_qualification_candidate=False,
            education_enrollment_mention_candidate=True,
            qualification_presence_rule="exploratory_current_enrollment_mention",
        ))
    payload["evidence"].extend(additions)


def _promote_compound_qualification_lines(payload: Dict[str, Any]) -> None:
    """Recover credential + explicit-years qualifications under a duties heading."""
    normalized = payload["normalized_text"]
    by_line: Dict[tuple[int, int], List[Dict[str, Any]]] = {}
    for item in payload["evidence"]:
        if item.get("module") in ("education", "experience"):
            by_line.setdefault(_line_bounds(normalized, item["start"], item["end"]), []).append(item)
    for (left, right), items in by_line.items():
        line = normalized[left:right]
        education = [x for x in items if x.get("module") == "education"]
        durations = [x for x in items if x.get("module") == "experience" and x.get("has_explicit_duration")]
        if not education or not durations or not re.search(r"\b(?:AND|OR|and|or)\b", line):
            continue
        if re.search(r"\b(?:maintain|prepare|manage|perform|coordinate|develop|support|assist)\b", line, re.I):
            continue
        for item in education + durations:
            if item.get("context") not in ("duties", "unknown"):
                continue
            item["context"] = "qualification_unspecified"
            item["requirement_strength"] = "unspecified"
            if not item.get("negated_or_optional") and not item.get("ambiguous_degree_abbreviation"):
                item["is_applicant_qualification_candidate"] = True
            item["is_applicant_requirement"] = False
            item["qualification_presence_rule"] = "compound_credential_duration_line"


def _drop_compensation_eligibility_experience(payload: Dict[str, Any]) -> None:
    normalized = payload["normalized_text"]
    retained = []
    for item in payload["evidence"]:
        if item.get("module") != "experience" or not item.get("has_explicit_duration"):
            retained.append(item)
            continue
        left, right = _line_bounds(normalized, item["start"], item["end"])
        before = normalized[max(left, item["start"] - 180):item["start"]]
        local = normalized[left:min(right, item["end"] + 80)]
        compensation = re.search(r"\b(?:sign[- ]on bonus|relocation(?: bonus| assistance)?)\b", before, re.I)
        eligibility = re.search(r"\b(?:for|available to)\b[^.;\n]{0,100}$", before, re.I)
        if compensation and eligibility and re.search(r"\bexternal applicants?\b", local, re.I):
            continue
        retained.append(item)
    payload["evidence"] = retained


def _refresh(payload: Dict[str, Any]) -> Dict[str, Any]:
    all_evidence = _base._deduplicate(payload["evidence"])
    payload["evidence_total_before_truncation"] = len(all_evidence)
    visible = all_evidence[:payload["evidence_limit"]]
    payload["evidence"] = visible
    payload["evidence_truncated"] = len(visible) < len(all_evidence)
    for module in _base.MODULES:
        all_module_items = [x for x in all_evidence if x["module"] == module]
        module_items = [x for x in visible if x["module"] == module]
        payload["summary"][module] = _base._summary(module, all_module_items)
        payload["module_evidence_truncated"][module] = len(module_items) < len(all_module_items)
    payload["normalization_version"] = NORMALIZATION_VERSION
    return payload


def extract(text: Any) -> Dict[str, Any]:
    payload = _base.extract(text)
    if payload.get("errors") or not isinstance(text, str):
        payload["normalization_version"] = NORMALIZATION_VERSION
        return payload
    if payload.get("evidence_truncated"):
        # The base summaries cover all evidence, while only the first 100
        # evidence rows are available for safe post-processing.  Preserve the
        # complete base metadata and explicitly exclude this row from V6
        # semantic denominators instead of pretending that the unseen tail was
        # inspected by the repair layer.
        payload["normalization_version"] = NORMALIZATION_VERSION
        payload["v6_candidate_incomplete"] = True
        payload["v6_candidate_incomplete_reason"] = "base_evidence_truncated_before_v6_postprocessing"
        return payload
    _add_current_enrollment(payload)
    _promote_compound_qualification_lines(payload)
    _drop_compensation_eligibility_experience(payload)
    return _refresh(payload)


_normalize = _base._normalize
