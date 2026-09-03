"""Fail-closed qualification checks for real-human duration annotators."""

from __future__ import annotations

from collections.abc import Mapping


MIN_YEARS_EXPERIENCE = 2.0
EARLIEST_RECENT_YEAR = 2016
ALLOWED_ROLES = {"hands_on_professional", "direct_supervisor"}
ALLOWED_CREDENTIAL = {"not_required", "active", "recent_direct_supervision_of_credentialed_work"}


def qualification_result(
    record: Mapping[str, object],
    *,
    task_occupation: str,
    task_sector: str,
    task_format: str,
    credential_required: bool,
) -> dict[str, object]:
    """Apply task-specific professional, recency, tool, and conflict rules."""
    reasons = []
    private_code = str(record.get("private_annotator_code", "")).strip()
    if not private_code:
        reasons.append("missing private annotator code")
    if str(record.get("occupation", "")).strip() != task_occupation:
        reasons.append("no exact GDPval-occupation experience")
    if str(record.get("sector", "")).strip() != task_sector:
        reasons.append("no matching task-sector experience")
    if str(record.get("experience_role", "")).strip() not in ALLOWED_ROLES:
        reasons.append("experience is neither hands-on professional nor direct supervisor")
    try:
        years = float(record.get("years_experience", 0))
    except (TypeError, ValueError):
        years = 0
    if years < MIN_YEARS_EXPERIENCE:
        reasons.append("fewer than two years relevant experience")
    try:
        last_active_year = int(record.get("last_active_year", 0))
    except (TypeError, ValueError):
        last_active_year = 0
    if last_active_year < EARLIEST_RECENT_YEAR:
        reasons.append("relevant work not active within the last ten years")
    formats = {value.strip() for value in str(record.get("task_format_competence", "")).split("|") if value.strip()}
    if task_format not in formats and "all" not in formats:
        reasons.append("task-format/tool competence not documented")
    credential = str(record.get("credential_status", "")).strip()
    if credential not in ALLOWED_CREDENTIAL or (credential_required and credential == "not_required"):
        reasons.append("required regulated-domain credential/supervision not documented")
    for field in ("conflict_clear", "consent_complete", "confidentiality_complete", "human_identity_verified"):
        if str(record.get(field, "")).strip().casefold() != "true":
            reasons.append(f"{field} is not verified")
    if str(record.get("qualification_reviewer_code", "")).strip() == "":
        reasons.append("independent qualification review missing")
    return {"status": "PASS" if not reasons else "FAIL", "reasons": reasons}
