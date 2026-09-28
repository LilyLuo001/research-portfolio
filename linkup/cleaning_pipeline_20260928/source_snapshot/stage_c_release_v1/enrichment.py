"""Conservative explicit-relation enrichment for frozen LinkUp V6 payloads.

The module never copies normalized text into its result.  All textual evidence
is represented by half-open offsets into ``payload['normalized_text']``.
Education and no-experience absence are outside this enrichment contract.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ENRICHMENT_VERSION = "linkup-exp-tech-explicit-v1"

_TECH_PATTERNS: Sequence[Tuple[str, str, re.Pattern]] = (
    ("generative_ai", "large_language_model", re.compile(r"\blarge language models?\b", re.I)),
    ("unspecified_ai", "llm_ambiguous", re.compile(r"(?<![A-Za-z0-9])LLMs?(?![A-Za-z0-9])")),
    ("generative_ai", "generative_ai", re.compile(r"\bgenerative AI\b", re.I)),
    ("generative_ai", "chatgpt", re.compile(r"\bChatGPT\b|\bGPT-?[234](?:\.\d+)?\b", re.I)),
    ("unspecified_ai", "machine_learning", re.compile(r"\bmachine learning\b", re.I)),
    ("unspecified_ai", "deep_learning", re.compile(r"\bdeep learning\b", re.I)),
    ("unspecified_ai", "neural_network", re.compile(r"\bneural networks?\b", re.I)),
    ("predictive_ai", "predictive_model", re.compile(r"\bpredictive models?\b", re.I)),
    ("unspecified_ai", "computer_vision", re.compile(r"\bcomputer vision\b", re.I)),
    ("unspecified_ai", "natural_language_processing", re.compile(r"\bnatural language processing\b|\bNLP\b", re.I)),
    ("unspecified_ai", "artificial_intelligence", re.compile(r"\bartificial intelligence\b|(?<![A-Za-z0-9])AI(?![A-Za-z0-9])")),
    ("traditional_software", "microsoft_office", re.compile(r"\b(?:Microsoft|MS) Office\b", re.I)),
    ("traditional_software", "excel", re.compile(r"\bExcel\b")),
    ("traditional_software", "power_bi", re.compile(r"\bPower BI\b", re.I)),
    ("traditional_software", "tableau", re.compile(r"\bTableau\b", re.I)),
    ("traditional_software", "salesforce", re.compile(r"\bSalesforce\b", re.I)),
    ("traditional_software", "sap", re.compile(r"(?<![A-Za-z0-9])SAP(?![A-Za-z0-9])")),
    ("traditional_software", "python", re.compile(r"\bPython\b")),
    ("traditional_software", "sql", re.compile(r"(?<![A-Za-z0-9_])SQL(?![A-Za-z0-9_])")),
    ("traditional_software", "java", re.compile(r"\bJava\b(?!Script)")),
)

_ROLE_PATTERNS: Sequence[Tuple[str, re.Pattern]] = (
    ("develop", re.compile(r"\b(?:develop|build|train|fine[- ]tune|design|create|program)\b", re.I)),
    ("implement", re.compile(r"\b(?:implement|integrate|deploy|embed|configure)\b", re.I)),
    ("use", re.compile(r"\b(?:use|using|operate|operating|work(?:ing)? with|proficien(?:t|cy) (?:in|with)|experience (?:in|with))\b", re.I)),
)

_DURATION_OBJECT = re.compile(
    r"(?P<duration>(?P<lo>\d{1,2}(?:\.\d+)?)\s*(?:(?P<sep>-|–|—|to)\s*(?P<hi>\d{1,2}(?:\.\d+)?)\s*)?"
    r"(?P<plus>\+|or more)?\s*(?P<unit>years?|yrs?\.?|months?|mos?\.?))"
    r"\s*(?:of\s+)?(?P<object>[A-Za-z][A-Za-z0-9+/#.&'’ -]{0,80}?)\s+experience\b",
    re.I,
)
_GENERIC_OBJECT = re.compile(
    r"(?P<object>[A-Za-z][A-Za-z0-9+/#.&'’ -]{0,80}?)\s+experience\b", re.I,
)
_POST_OBJECT = re.compile(
    r"\bexperience\s+(?:in|with|using)\s+(?P<objects>[A-Za-z0-9+/#.&'’ -]{1,100})",
    re.I,
)
_GENERAL = re.compile(r"^(?:overall|general|professional|work)$", re.I)
_INDUSTRY = re.compile(r"\b(?:healthcare|clinical|finance|banking|insurance|defen[cs]e|government|manufacturing|construction|retail|coating|pharmaceutical|education|telecommunications?)\b", re.I)
_TOOL = re.compile(r"\b(?:Python|SQL|Java|SAP|Excel|Tableau|Power BI|Salesforce|Microsoft Office)\b", re.I)


def _clause_bounds(text: str, start: int, end: int) -> Tuple[int, int]:
    left_candidates = [text.rfind(mark, 0, start) for mark in ("\n", ";", ".", "!", "?")]
    left = max(left_candidates) + 1
    rights = [p for p in (text.find(mark, end) for mark in ("\n", ";", ".", "!", "?")) if p >= 0]
    return left, min(rights) if rights else len(text)


def _context_at(payload: Dict[str, Any], start: int, end: int) -> Tuple[str, bool]:
    overlaps = [x for x in payload.get("evidence", [])
                if x.get("module") in ("software", "ai") and x.get("start", -1) < end and x.get("end", -1) > start]
    if not overlaps:
        return "unknown", False
    overlaps.sort(key=lambda x: (abs(x["start"] - start), x["end"] - x["start"]))
    item = overlaps[0]
    return str(item.get("context") or "unknown"), bool(item.get("is_applicant_qualification_candidate"))


def _experience_context(payload: Dict[str, Any], start: int, end: int) -> Tuple[str, bool, str]:
    overlaps = [x for x in payload.get("evidence", [])
                if x.get("module") == "experience" and x.get("start", -1) < end and x.get("end", -1) > start]
    if not overlaps:
        return "unknown", False, "unspecified"
    overlaps.sort(key=lambda x: (abs(x["start"] - start), x["end"] - x["start"]))
    item = overlaps[0]
    return (str(item.get("context") or "unknown"),
            bool(item.get("is_applicant_qualification_candidate")),
            str(item.get("requirement_strength") or "unspecified"))


def _object_type(value: str) -> str:
    cleaned = value.strip(" ,:-").lower()
    if not cleaned or _GENERAL.fullmatch(cleaned):
        return "general_work"
    if _TOOL.search(value):
        return "specific_tool"
    if _INDUSTRY.search(value):
        return "industry_domain"
    return "object_unspecified"


def _years(value: Optional[str], unit: str) -> Optional[float]:
    if value is None:
        return None
    number = float(value)
    return number / 12.0 if unit.lower().startswith(("month", "mo")) else number


def _relation(clause: str) -> str:
    if re.search(r"\binclud(?:e|es|ing)\b", clause, re.I):
        return "includes"
    if re.search(r"\b(?:or|and/or)\b", clause, re.I):
        return "OR"
    if re.search(r"\band\b", clause, re.I):
        return "AND"
    return "none"


def _experience(payload: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    occupied: List[Tuple[int, int]] = []
    for match in _DURATION_OBJECT.finditer(text):
        obj = match.group("object").strip(" ,:-")
        object_start = match.start("object") + (len(match.group("object")) - len(match.group("object").lstrip(" ,:-")))
        object_end = object_start + len(obj)
        left, right = _clause_bounds(text, match.start(), match.end())
        clause = text[left:right]
        context, applicant, strength = _experience_context(payload, match.start(), match.end())
        unit = match.group("unit")
        lo, hi = _years(match.group("lo"), unit), _years(match.group("hi"), unit)
        if match.group("plus") and hi is None:
            pass
        rows.append({
            "clause_start": left, "clause_end": right,
            "object_start": object_start, "object_end": object_end,
            "object_type": _object_type(obj), "min_years": lo, "max_years": hi,
            "duration_unit": "months" if unit.lower().startswith(("month", "mo")) else "years",
            "bound_type": "range" if hi is not None else ("minimum" if match.group("plus") else "exact_or_unspecified"),
            "binding_status": "explicit", "relation": _relation(clause),
            "optional": bool(re.search(r"\b(?:optional|preferred|nice to have|a plus)\b", clause, re.I)),
            "context": context, "applicant_context_candidate": applicant,
            "requirement_strength": strength,
        })
        occupied.append((match.start(), match.end()))
    for match in _POST_OBJECT.finditer(text):
        if any(match.start() < b and match.end() > a for a, b in occupied):
            continue
        raw = match.group("objects")
        # Stop at a new qualification/action phrase; commas inside a tool list remain.
        raw = re.split(r"\b(?:required|preferred|responsible|while|where|who)\b", raw, maxsplit=1, flags=re.I)[0].strip(" ,:-")
        if not raw:
            continue
        base = match.start("objects")
        parts = list(re.finditer(r"[^,]+?(?=\s+(?:and|or|and/or)\s+|,|$)", raw, re.I))
        if not parts:
            parts = [re.match(r".+", raw)]
        left, right = _clause_bounds(text, match.start(), match.end())
        clause = text[left:right]
        context, applicant, strength = _experience_context(payload, match.start(), match.end())
        relation = _relation(raw)
        for part in parts:
            value = part.group(0).strip(" ,:-")
            if not value:
                continue
            offset = part.start() + (len(part.group(0)) - len(part.group(0).lstrip(" ,:-")))
            rows.append({"clause_start": left, "clause_end": right,
                         "object_start": base + offset, "object_end": base + offset + len(value),
                         "object_type": _object_type(value), "min_years": None, "max_years": None,
                         "duration_unit": None, "bound_type": "duration_unspecified",
                         "binding_status": "explicit", "relation": relation,
                         "optional": bool(re.search(r"\b(?:optional|preferred|nice to have|a plus)\b", clause, re.I)),
                         "context": context, "applicant_context_candidate": applicant,
                         "requirement_strength": strength})
    return rows


def _add_unspecified_v6_experience(payload: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    """Retain V6 experience candidates whose object grammar is unresolved."""
    text = payload["normalized_text"]
    for item in payload.get("evidence", []):
        if item.get("module") != "experience" or not item.get("is_applicant_qualification_candidate"):
            continue
        if item.get("no_experience_explicit"):
            continue
        start, end = item.get("start"), item.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if any(row["clause_start"] <= start < row["clause_end"] and row.get("object_start") is not None
               for row in rows):
            continue
        left, right = _clause_bounds(text, start, end)
        context, applicant, strength = _experience_context(payload, start, end)
        rows.append({"clause_start": left, "clause_end": right,
                     "object_start": None, "object_end": None,
                     "object_type": "object_unspecified",
                     "min_years": item.get("min_years"), "max_years": item.get("max_years"),
                     "duration_unit": item.get("duration_unit"),
                     "bound_type": item.get("bound_type") or "duration_unspecified",
                     "binding_status": "unknown", "relation": _relation(text[left:right]),
                     "optional": bool(item.get("negated_or_optional") or item.get("context") == "preferred"),
                     "context": context, "applicant_context_candidate": applicant,
                     "requirement_strength": strength})


def _technologies(payload: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
    mentions: List[Tuple[int, int, str, str]] = []
    occupied: List[Tuple[int, int]] = []
    for technology_type, canonical, pattern in _TECH_PATTERNS:
        for match in pattern.finditer(text):
            if any(match.start() < b and match.end() > a for a, b in occupied):
                continue
            mentions.append((match.start(), match.end(), technology_type, canonical))
            occupied.append((match.start(), match.end()))
    rows: List[Dict[str, Any]] = []
    for start, end, technology_type, canonical in sorted(mentions):
        left, right = _clause_bounds(text, start, end)
        clause = text[left:right]
        rel_start, rel_end = start - left, end - left
        candidates: List[Tuple[str, int, int]] = []
        for role, pattern in _ROLE_PATTERNS:
            for verb in pattern.finditer(clause):
                # Explicit action-target relation: action precedes the technology,
                # remains within 60 characters, and no strong separator intervenes.
                if verb.end() <= rel_start and rel_start - verb.end() <= 60:
                    between = clause[verb.end():rel_start]
                    intervening_technology = any(
                        other_start >= left + verb.end() and other_end <= start
                        for other_start, other_end, _, _ in mentions
                        if (other_start, other_end) != (start, end)
                    )
                    if not re.search(r"[;.!?\n]", between) and not intervening_technology:
                        candidates.append((role, left + verb.start(), left + verb.end()))
        roles: List[Tuple[str, int, int]] = []
        if candidates:
            nearest = max(candidates, key=lambda x: x[2])
            roles.append(nearest)
            # Retain coordinated actions sharing the same explicit target,
            # e.g. "develop and deploy prediction models".
            for candidate in candidates:
                if candidate == nearest:
                    continue
                connector = text[candidate[2]:nearest[1]]
                if re.fullmatch(r"\s*(?:,?\s*and\s+|,\s*)", connector, re.I):
                    roles.append(candidate)
        context, applicant = _context_at(payload, start, end)
        if roles:
            for role, role_start, role_end in sorted(set(roles)):
                between = text[role_end:start]
                directly_bound = bool(re.fullmatch(
                    r"\s*(?:(?:an?|the|our|new|advanced|custom|enterprise|pretrained|predictive|generative)\s+){0,3}",
                    between, re.I,
                ))
                rows.append({"technology_start": start, "technology_end": end,
                             "technology_type": technology_type, "technology_name": canonical,
                             "role_start": role_start, "role_end": role_end, "role": role,
                             "binding_status": "explicit" if directly_bound else "candidate_local_relation",
                             "role_candidate": True, "technology_ambiguity": "bare_llm" if canonical == "llm_ambiguous" else None,
                             "context": context, "applicant_context_candidate": applicant})
        else:
            rows.append({"technology_start": start, "technology_end": end,
                         "technology_type": technology_type, "technology_name": canonical,
                         "role_start": None, "role_end": None, "role": "unknown",
                         "binding_status": "unknown", "role_candidate": False,
                         "technology_ambiguity": "bare_llm" if canonical == "llm_ambiguous" else None,
                         "context": context,
                         "applicant_context_candidate": applicant})
    return rows


def enrich(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return sparse relation evidence for one frozen V6 payload."""
    parse_error = bool(payload.get("errors"))
    truncated = bool(payload.get("evidence_truncated"))
    incomplete = bool(payload.get("v6_candidate_incomplete")) or parse_error or truncated
    flags = {
        "enrichment_version": ENRICHMENT_VERSION,
        "source_normalization_version": payload.get("normalization_version"),
        "offset_coordinate_system": "normalized_text_python_codepoint_half_open",
        "input_parse_error": parse_error,
        "input_evidence_truncated": truncated,
        "enrichment_incomplete": incomplete,
    }
    if incomplete:
        return {"experience_evidence": [], "technology_evidence": [], "flags": flags}
    text = payload.get("normalized_text")
    if not isinstance(text, str):
        flags["enrichment_incomplete"] = True
        flags["input_parse_error"] = True
        return {"experience_evidence": [], "technology_evidence": [], "flags": flags}
    experience = _experience(payload, text)
    _add_unspecified_v6_experience(payload, experience)
    technology = _technologies(payload, text)
    for ordinal, row in enumerate(experience):
        row["evidence_ordinal"] = ordinal
    for ordinal, row in enumerate(technology):
        row["evidence_ordinal"] = ordinal
    return {"experience_evidence": experience, "technology_evidence": technology, "flags": flags}


__all__ = ["enrich", "ENRICHMENT_VERSION"]
