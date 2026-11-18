"""Bounded, deterministic candidate extraction; never writes semantic values.

Input must be the caller's retained full text. It is not normalized here, so
every half-open Python codepoint offset addresses precisely that input string.
Only standard-library modules and pinned existing LinkUp vocabularies are used.
See README.md for the complete contract and limits.
"""
from __future__ import annotations

import hashlib
import json
import re
from bisect import bisect_left
from pathlib import Path
from typing import Iterable

try:
    from . import frozen_vocabulary as frozen
except ImportError:  # Standalone import when rules/ is on sys.path.
    import frozen_vocabulary as frozen

VERSION = "linkup-cpu-candidates-20261119-v1"
CACHE_VERSION = VERSION
MAX_TEXT_CHARACTERS = 500_000
MAX_CANDIDATES = 1024
MAX_CONTEXT_CHARACTERS = 8192
COORDINATE_SYSTEM = "input_text_python_codepoint_half_open"
EXPERIENCE_FIELDS = tuple("experience." + value for value in (
    "general_work", "occupation_task", "industry_domain", "tool_specific"))
SUPPORTED_FAMILIES = ("experience", "education", "technology", "entry.explicit_no_experience")

def _rx(pattern):
    return re.compile(pattern, re.I)

# The original numeric grammar is retained and extended at its syntactic
# boundary: spelled-out 13--19, units on both range endpoints, and suffixes.
# This does not add a subject/occupation/industry taxonomy.
_NUMWORDS = dict(frozen.NUMWORDS, thirteen=13, fourteen=14, sixteen=16,
                 seventeen=17, eighteen=18, nineteen=19)
_NUMBER = r"(?:\d{1,2}(?:\.\d+)?|" + "|".join(_NUMWORDS) + r")"
_UNIT = r"(?:years?|yrs?|months?|mos?)"
_YEARS = _rx(
    r"(?<![\w.])(?:(?P<prefix>at least|a minimum of|minimum of|minimum|"
    r"more than|over|up to|at most|no more than|maximum of|less than|under|"
    r"fewer than|exactly|between)\s+)?(?P<lo>" + _NUMBER + r")"
    r"(?:\s*\((?P<paren>\d{1,2})\))?"
    r"(?:\s*(?P<firstunit>" + _UNIT + r")?\s*(?:-|–|—|to|and)\s*"
    r"(?P<hi>" + _NUMBER + r"))?\s*(?P<plus>\+|or more)?\s*[-–]?\s*"
    r"(?P<unit>" + _UNIT + r")\b(?:\s+(?P<suffix>or more|or less|or fewer|minimum|maximum))?")
_SENTENCE_END = re.compile(r"[!?](?=\s|$)|\.(?=\s+(?:[A-Z]|[-*•])|$)")
_SEMICOLON = re.compile(r";")
_OR = _rx(r"\b(?:either|alternatively|and/or)\b|\bor\b(?!\s+(?:more|less|fewer)\b)")
_SUBSTITUTION = _rx(r"\bin lieu of\b|\binstead of\b|\bsubstitut\w*\b|\bequivalent combination\b")
_CONDITION = _rx(r"\b(?:unless|depending on|if|provided that|alternatively)\b")
_NEGATION = _rx(r"\b(?:no|not|never|without|need not)\b")
_PART_TIME = _rx(r"\bpart[- ]time\b")
_RATIO = _rx(r"\b(?:for each|per year|per academic|equivalent to|credited as|prorat\w*)\b")
_OTHER_PEOPLE = _rx(r"\b(?:mentor|mentoring|train|training|supervise|supervising|manage|managing)\b.{0,65}\b(?:junior|staff|employees?|engineers?|graduates?|interns?|team)\b")
_APPLICANT = _rx(r"\b(?:you (?:have|bring|possess|must)|candidates? (?:have|must|with)|applicants? (?:have|must|with))\b")
_AGE_TAIL = _rx(r"^\s*(?:of age|old\b|-old\b)")
_NOT_WORK_TAIL = _rx(r"^\s*(?:anniversary|warranty|contract|fixed[- ]term|lease|degree|degree program|course|program|old|of age)\b")
_COMPANY_HISTORY = _rx(r"\b(?:we have|our company has|our firm has|we bring|in business for|company history|founded|established)\b")
_QUESTIONNAIRE = _rx(r"\bWhich of the following (?:best )?describes\b|\bHow would you rate your\b")
_MARKUP = re.compile(r"</?[A-Za-z][^>]*>")
_LOCAL_BOUNDARY = re.compile(r"\s*(?:(?:[-*•]|#{1,6})\s*)?")
_HEADINGS = (("required", _rx(r"^must[- ]haves?\s*:?$")),) + frozen._HEADING_RULES
_INLINE_HEADINGS = tuple((section, _rx(r"^\s*(?:" + pattern + r")\s*:\s*"))
                         for section, pattern in frozen._INLINE_HEADING_RULES)
_DEGREES = tuple((level, _rx(pattern)) for level, pattern in frozen._DEGREES)
_DEGREE_EXTRA = (
    ("bachelor", _rx(r"\bbachelor(?:['’]?s)?\b")),
    ("master", _rx(r"\bmaster['’]s\b")),
    ("unspecified_degree", _rx(r"\bdegree\b")),
)
# Fix the legacy trailing word-boundary omission for C++/C#. Terms themselves
# are unchanged. TECH remains lexical presence, not adoption or tool usage.
_PUNCTUATED_SOFTWARE = re.compile(r"(?<!\w)(?:C\+\+|C#)(?!\w)", re.I)
_TECH = tuple((category, _rx(pattern.pattern.replace(r"C\+\+|C#|", ""))
               if category == "software" else pattern) for category, pattern in frozen.TECH.items())
_ABBREVIATION = re.compile(r"(?:AA|AS|BA|BS|MA|MS|MBA|BSc|MSc|B\.?\s*[AS]\.?)", re.I)


def _requested_fields(missing_fields: Iterable[str] | None) -> tuple[str, ...]:
    if missing_fields is None:
        raise TypeError("missing_fields must explicitly identify missing fields")
    if isinstance(missing_fields, (str, bytes)):
        raise TypeError("missing_fields must be an iterable of field names, not a string")
    fields = tuple(missing_fields)
    if any(not isinstance(value, str) or not value for value in fields):
        raise TypeError("every missing field must be a nonempty string")
    return tuple(sorted(set(fields)))


def _family(field):
    if field == "experience" or any(field == root or field.startswith(root + ".") for root in EXPERIENCE_FIELDS):
        return "experience"
    if field in ("degree", "degrees", "education") or field.startswith("education."):
        return "education"
    if field in ("tool", "tools", "ai", "technology") or field.startswith("technology."):
        return "technology"
    if field == "entry.explicit_no_experience" or field.startswith("entry.explicit_no_experience."):
        return "entry.explicit_no_experience"
    return None


def _source_sha(text):
    # surrogatepass also makes exceptional undecoded strings deterministic;
    # their exact input string remains the evidence coordinate system.
    return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()


def cache_key(text: str, missing_fields: Iterable[str]) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    payload = [CACHE_VERSION, ENGINE_SHA256, _source_sha(text), _requested_fields(missing_fields)]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def _span(text, start, end):
    return {"start": start, "end": end, "quote": text[start:end]}


def _context_span(text, start, end, focus):
    if end - start <= MAX_CONTEXT_CHARACTERS:
        return _span(text, start, end)
    left = max(start, min(focus - MAX_CONTEXT_CHARACTERS // 2, end - MAX_CONTEXT_CHARACTERS))
    value = _span(text, left, min(end, left + MAX_CONTEXT_CHARACTERS))
    value.update(full_start=start, full_end=end, truncated=True)
    return value


def _trim(text, start, end):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _parts(text):
    """Yield clauses with retained full sentence/line and inherited headings."""
    section = "unknown"
    offset = 0
    for raw in text.splitlines(keepends=True):
        left, right = _trim(text, offset, offset + len(raw))
        offset += len(raw)
        if left == right:
            continue
        line = text[left:right]
        clean = _LOCAL_BOUNDARY.sub("", line, count=1).rstrip("*").strip()
        heading = next((kind for kind, pattern in _HEADINGS if pattern.fullmatch(clean)), None)
        if heading and len(clean) <= 80:
            section = heading
            continue
        local_section = section
        for kind, pattern in _INLINE_HEADINGS:
            match = pattern.match(line)
            if match:
                section = local_section = kind
                left += match.end()
                break
        # Sentences retain ; and OR branches; clauses retain commas and AND.
        sentence_left = left
        sentence_ends = [left + m.end() for m in _SENTENCE_END.finditer(text[left:right])
                         if not text[max(left, left + m.end() - 6):left + m.end()].lower().endswith(
                             ("ph.d.", "phd.", "b.s.", "b.a."))]
        for sentence_right in sentence_ends + [right]:
            sl, sr = _trim(text, sentence_left, sentence_right)
            if sl < sr:
                clause_left = sl
                for clause_right in [sl + m.end() for m in _SEMICOLON.finditer(text[sl:sr])] + [sr]:
                    cl, cr = _trim(text, clause_left, clause_right)
                    if cl < cr:
                        yield cl, cr, sl, sr, local_section
                    clause_left = clause_right
            sentence_left = sentence_right


def _number(value):
    return float(_NUMWORDS[value.lower()]) if value.lower() in _NUMWORDS else float(value)


def _duration(match):
    value = _number(match["lo"])
    hi = _number(match["hi"]) if match["hi"] else None
    prefix = (match["prefix"] or "").lower()
    suffix = (match["suffix"] or "").lower()
    unit = match["unit"].lower()
    first_unit = (match["firstunit"] or unit).lower()
    low_factor = 1 / 12 if first_unit.startswith(("month", "mo")) else 1
    high_factor = 1 / 12 if unit.startswith(("month", "mo")) else 1
    kind = "stated_unspecified"
    lower, upper = value * low_factor, None
    strict_lower = prefix in ("more than", "over")
    strict_upper = prefix in ("less than", "under", "fewer than")
    reasons = []
    if hi is not None:
        kind, upper = "range", hi * high_factor
        if upper < lower:
            reasons.append("reversed_range_unresolved")
            lower = upper = None
    elif prefix in ("up to", "at most", "no more than", "maximum of", "less than", "under", "fewer than") or suffix in ("or less", "or fewer", "maximum"):
        kind, lower, upper = "maximum", None, lower
    elif prefix == "exactly":
        kind, upper = "exact", lower
    elif prefix in ("at least", "a minimum of", "minimum of", "minimum", "more than", "over") or match["plus"] or suffix in ("or more", "minimum"):
        kind = "minimum"
    if match["paren"] and float(match["paren"]) != value:
        reasons.append("word_parenthetical_number_disagreement")
        lower = upper = None
    if prefix == "between" and hi is None:
        reasons.append("incomplete_between_range")
    return {"kind": kind, "stated_value": value, "lower_years": lower, "upper_years": upper,
            "strict_lower": strict_lower, "strict_upper": strict_upper,
            "original_unit": unit, "first_original_unit": first_unit,
            "prefix": prefix or None, "suffix": suffix or match["plus"] or None,
            "is_posting_minimum": False}, reasons


def _subject_cues(clause):
    values = []
    for category, pattern in (("tool", frozen.TOOL), ("industry_domain", frozen.DOMAIN),
                              ("occupation_task", frozen.TASK)):
        if pattern.search(clause):
            values.append(category)
    general = frozen.GENERAL.search(clause)
    if general:
        values.append("general_work")
    # These are co-occurring cues, never an assignment of the number to them.
    return values


def _strength(clause, section):
    preferred, required = bool(frozen.PREFERRED.search(clause)), bool(frozen.REQUIRED.search(clause))
    if preferred and required:
        return "mixed"
    if preferred:
        return "preferred"
    if required:
        return "required"
    return section if section in ("required", "preferred") else "unspecified"


def extract(text: str, missing_fields: Iterable[str]) -> dict:
    """Return candidates only for requested missing fields; never accepted values.

    All requested fields remain unresolved. Unsupported fields are reported,
    never silently reclassified as a no-hit. Empty or oversized input returns a
    distinct status. Non-string text and invalid field selections raise TypeError.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    fields = _requested_fields(missing_fields)
    by_family = {family: tuple(field for field in fields if _family(field) == family)
                 for family in SUPPORTED_FAMILIES}
    result = {
        "version": VERSION, "cache_version": CACHE_VERSION, "engine_sha256": ENGINE_SHA256,
        "source_text_sha256": _source_sha(text), "cache_key": cache_key(text, fields),
        "coordinate_system": COORDINATE_SYSTEM, "candidate_only": True,
        "status": "processed", "candidates": [], "excluded_spans": [],
        "excluded_span_count": 0, "excluded_spans_truncated": False,
        "resolved_fields": [], "field_updates": {}, "requested_fields": list(fields),
        "unsupported_fields": [field for field in fields if _family(field) is None],
        "field_status": {}, "document_flags": [], "candidate_count_before_limit": 0,
        "candidates_truncated": False,
        "interpretation": "Lexical candidates only; no-hit is unknown, not absence. No semantic accuracy or recall certification.",
    }
    if not text.strip():
        result["status"] = "empty_input"
    elif len(text) > MAX_TEXT_CHARACTERS:
        result["status"] = "input_limit_exceeded"
    elif not fields:
        result["status"] = "no_fields_requested"
    if result["status"] != "processed":
        result["field_status"] = {field: {"state": result["status"] + "_unknown", "candidate_count": 0} for field in fields}
        return result
    if _MARKUP.search(text):
        result["document_flags"].append("markup_present_original_coordinates_retained")
    multiline = [m.span() for m in re.finditer(r"(?im)^\s*[-*•]?\s*OR\s*$", text)]
    multiline_starts = [a for a, _ in multiline]
    if multiline:
        result["document_flags"].append("multiline_alternative_unresolved")
    questionnaire = _QUESTIONNAIRE.search(text)
    if questionnaire:
        result["document_flags"].append("questionnaire_tail_context")
    counts = {field: 0 for field in fields}
    context_cache = {}

    def add(kind, match_start, match_end, bounds, family, **extra):
        targets = by_family[family]
        if not targets:
            return
        result["candidate_count_before_limit"] += 1
        for field in targets:
            counts[field] += 1
        if len(result["candidates"]) >= MAX_CANDIDATES:
            result["candidates_truncated"] = True
            return
        cl, cr, sl, sr, section = bounds
        context = context_cache.get(bounds)
        if context is None:
            clause, sentence = text[cl:cr], text[sl:sr]
            scopes = [cue for cue, pattern in (("or_alternative", _OR), ("substitution", _SUBSTITUTION),
                      ("condition", _CONDITION), ("negation", _NEGATION),
                      ("duration_equivalence_or_ratio", _RATIO)) if pattern.search(sentence)]
            actor = "other_people_cue" if _OTHER_PEOPLE.search(clause) else "advertised_worker_cue" if _APPLICANT.search(clause) else "unresolved"
            context = (scopes, actor, _strength(clause, section), _subject_cues(clause), bool(_PART_TIME.search(clause)))
            context_cache[bounds] = context
        base_scopes, actor, strength, subjects, part_time = context
        scopes = list(base_scopes)
        reasons = ["semantic_validation_required"]
        or_index = bisect_left(multiline_starts, match_start)
        nearby_or = next(((a, b) for a, b in multiline[max(0, or_index - 1):or_index + 1]
                          if a - 1400 <= match_start <= b + 1400), None)
        if nearby_or:
            scopes.append("multiline_alternative_unresolved")
        if actor == "other_people_cue":
            reasons.append("advertised_worker_relation_unresolved")
        if section in frozen.EXCLUDED:
            reasons.append("nonqualification_section")
        if questionnaire and match_start >= questionnaire.start():
            reasons.append("questionnaire_answer_or_prompt")
        if strength == "mixed":
            reasons.append("mixed_required_preferred")
        if scopes:
            reasons.append("scope_requires_semantic_resolution")
        if kind.startswith("experience") and not subjects:
            reasons.append("experience_subject_unknown")
        if len(subjects) > 1:
            reasons.append("multiple_subject_cues")
        item = {
            "kind": kind, "target_fields": list(targets),
            "match": _span(text, match_start, match_end), "clause": _context_span(text, cl, cr, match_start),
            "sentence": _context_span(text, sl, sr, match_start), "section": section,
            "strength_cue": strength, "scope_cues": scopes,
            "subject_cues": subjects, "subject_assignment": "unresolved",
            "actor_cue": actor, "part_time_cue": part_time,
            "semantic_status": "unknown", "review_reasons": reasons,
        }
        if nearby_or:
            a, b = nearby_or
            item["alternative_context"] = _span(text, max(0, a - 1400), min(len(text), b + 1400))
        if item["clause"].get("truncated") or item["sentence"].get("truncated"):
            reasons.append("context_quote_truncated_full_bounds_retained")
        extra_reasons = extra.pop("review_reasons", [])
        item.update(extra)
        item["review_reasons"] = sorted(set(reasons + extra_reasons))
        result["candidates"].append(item)

    for bounds in _parts(text):
        cl, cr, sl, sr, section = bounds
        clause = text[cl:cr]
        if by_family["experience"] or by_family["entry.explicit_no_experience"]:
            waivers = list(frozen.NOEXP.finditer(clause))
            exp_mentions = list(frozen.EXP.finditer(clause))
            exp_starts = [match.start() for match in exp_mentions]
            durations = list(_YEARS.finditer(clause))
            for waiver in waivers:
                for family in ("experience", "entry.explicit_no_experience"):
                    add("experience_waiver", cl + waiver.start(), cl + waiver.end(), bounds, family,
                        waiver_cue=True, review_reasons=["waiver_subject_and_scope_unresolved"])
            retained_durations = 0
            for match in durations:
                tail = clause[match.end():]
                before = clause[:match.start()]
                excluded_reason = None
                if _AGE_TAIL.search(tail):
                    excluded_reason = "age_duration"
                elif _NOT_WORK_TAIL.search(tail):
                    excluded_reason = "explicit_non_experience_duration"
                elif _COMPANY_HISTORY.search(before) and not frozen.REQUIRED.search(before):
                    excluded_reason = "company_history_duration"
                if excluded_reason:
                    result["excluded_span_count"] += 1
                    if len(result["excluded_spans"]) < MAX_CANDIDATES:
                        result["excluded_spans"].append({"match": _span(text, cl + match.start(), cl + match.end()), "reason": excluded_reason})
                    else:
                        result["excluded_spans_truncated"] = True
                    continue
                retained_durations += 1
                duration, reasons = _duration(match)
                if not exp_mentions:
                    reasons.append("no_explicit_experience_anchor")
                if len(durations) > 1 or len(exp_mentions) > 1:
                    reasons.append("duration_experience_association_unresolved")
                exp_index = bisect_left(exp_starts, match.start())
                nearest_exps = exp_mentions[max(0, exp_index - 1):exp_index + 1]
                add("experience_duration", cl + match.start(), cl + match.end(), bounds, "experience",
                    duration=duration, experience_anchor_count=len(exp_mentions),
                    experience_anchors=[_span(text, cl + m.start(), cl + m.end()) for m in nearest_exps],
                    review_reasons=reasons)
            if exp_mentions and not retained_durations and not waivers:
                for match in exp_mentions:
                    add("experience_mention", cl + match.start(), cl + match.end(), bounds, "experience",
                        duration=None, review_reasons=["no_duration_resolved"])
        if by_family["education"]:
            degrees = []
            for level, pattern in _DEGREES + _DEGREE_EXTRA:
                for match in pattern.finditer(clause):
                    # Old case-insensitive AS/MA/BS patterns also match ordinary
                    # words. Retain uppercase abbreviations as ambiguous cues.
                    abbreviation = bool(_ABBREVIATION.fullmatch(match.group(0)))
                    if abbreviation and not match.group(0).isupper() and match.group(0) not in ("BSc", "MSc"):
                        continue
                    degrees.append((match.start(), match.end(), level, abbreviation))
            covered = []
            for start, end, level, abbreviation in sorted(degrees, key=lambda d: (-(d[1] - d[0]), d[0], d[2])):
                if any(start >= left and end <= right for left, right in covered):
                    continue
                covered.append((start, end))
                add("degree_mention", cl + start, cl + end, bounds, "education", degree_level_cue=level,
                    review_reasons=["abbreviated_degree_ambiguous"] if abbreviation else [])
        if by_family["technology"]:
            hits = set()
            for category, pattern in _TECH + (("software", _PUNCTUATED_SOFTWARE),):
                for match in pattern.finditer(clause):
                    key = (category, match.start(), match.end())
                    if key in hits:
                        continue
                    hits.add(key)
                    add("technology_keyword", cl + match.start(), cl + match.end(), bounds, "technology",
                        technology_category=category, term=match.group(0), lexical_only=True)
    result["candidates"].sort(key=lambda item: (item["match"]["start"], item["match"]["end"], item["kind"], tuple(item["target_fields"])))
    if result["candidates_truncated"]:
        result["status"] = "candidate_limit_exceeded"
    for field in fields:
        state = "unsupported_unknown" if _family(field) is None else "candidates_present_unknown" if counts[field] else "no_rule_hit_unknown"
        result["field_status"][field] = {"state": state, "candidate_count": counts[field]}
    return result


_HERE = Path(__file__).resolve().parent
ENGINE_SHA256 = hashlib.sha256(b"\0".join(
    (name.encode() + b"\0" + (_HERE / name).read_bytes())
    for name in ("cpu_candidates.py", "frozen_vocabulary.py"))).hexdigest()

__all__ = ["extract", "cache_key", "VERSION", "CACHE_VERSION", "ENGINE_SHA256",
           "MAX_TEXT_CHARACTERS", "MAX_CANDIDATES", "MAX_CONTEXT_CHARACTERS", "SUPPORTED_FAMILIES"]
