"""Deterministic recruitment-text candidate extraction.

The output of :func:`extract` is deliberately a set of *candidates* for human
validation.  It is not a set of validated requirements, economic measures, or
claims about employer adoption of a technology.

Only the Python standard library is used.  Evidence offsets use the returned
``normalized_text`` coordinate system, never the source HTML coordinate system.
"""

from __future__ import annotations

import html
import re
from collections import defaultdict
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


NORMALIZATION_VERSION = "recruitment-html-text-v1"
EVIDENCE_LIMIT = 100
MODULES = ("software", "ai", "experience", "education", "tasks")


class _VisibleTextParser(HTMLParser):
    """HTML-to-text parser that retains block and list boundaries."""

    _BLOCKS = {
        "address", "article", "aside", "blockquote", "br", "dd", "div",
        "dl", "dt", "figcaption", "figure", "footer", "h1", "h2", "h3",
        "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
        "p", "pre", "section", "table", "tbody", "td", "tfoot", "th",
        "thead", "tr", "ul",
    }
    _HIDDEN = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.parts: List[str] = []
        self.hidden_depth = 0

    def _break(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_starttag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in self._HIDDEN:
            self.hidden_depth += 1
            return
        if not self.hidden_depth and tag in self._BLOCKS:
            self._break()

    def handle_startendtag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        if not self.hidden_depth and tag.lower() in self._BLOCKS:
            self._break()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._HIDDEN:
            if self.hidden_depth:
                self.hidden_depth -= 1
            return
        if not self.hidden_depth and tag in self._BLOCKS:
            self._break()

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def _normalize(text: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(text)
    parser.close()
    visible = html.unescape("".join(parser.parts))
    visible = visible.replace("\r\n", "\n").replace("\r", "\n")
    visible = visible.replace("\u00a0", " ").replace("\u200b", "")
    lines = []
    for line in visible.split("\n"):
        line = re.sub(r"[\t\f\v ]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


_HEADING_RULES = (
    ("preferred", re.compile(r"^(?:preferred|preferred qualifications?|nice to have|bonus(?: points)?|desired)(?:\s*:)?$", re.I)),
    ("required", re.compile(r"^(?:required|requirements?|required qualifications?|minimum qualifications?|what you(?:'|’)ll need)(?:\s*:)?$", re.I)),
    ("unknown", re.compile(r"^(?:qualifications?(?: and skills)?|who you are)(?:\s*:)?$", re.I)),
    ("duties", re.compile(r"^(?:responsibilities|duties|what you(?:'|’)ll do|the role|job description)(?:\s*:)?$", re.I)),
    ("company", re.compile(r"^(?:about(?: us| the company)?|our company|who we are|company overview)(?:\s*:)?$", re.I)),
    ("benefits", re.compile(r"^(?:benefits|perks|what we offer|compensation(?: and benefits)?)(?:\s*:)?$", re.I)),
)

_LOCAL_PREFERRED = re.compile(r"\b(?:preferred|preferably|desired|nice[- ]to[- ]have|a plus|bonus)\b", re.I)
_LOCAL_REQUIRED = re.compile(r"\b(?:require(?:d|s)?|must(?: have)?|minimum qualification|need(?:ed)?|shall)\b", re.I)
_LOCAL_DUTIES = re.compile(r"\b(?:responsib(?:le|ilities)|duties include|you will|you(?:'|’)ll)\b", re.I)
_LOCAL_COMPANY = re.compile(r"\b(?:our company|we are a|founded in|has been in business|company history)\b", re.I)
_LOCAL_BENEFITS = re.compile(r"\b(?:we offer|benefits include|paid time off|health insurance|salary|compensation)\b", re.I)


def _heading_context(line: str) -> Optional[str]:
    cleaned = re.sub(r"^#{1,6}\s*", "", line.strip())
    if len(cleaned) > 80:
        return None
    for context, pattern in _HEADING_RULES:
        if pattern.match(cleaned):
            return context
    return None


def _line_context(line: str, section: str) -> str:
    # Explicit wording closest to the candidate takes precedence over a heading.
    if _LOCAL_PREFERRED.search(line):
        return "preferred"
    if _LOCAL_REQUIRED.search(line):
        return "required"
    if _LOCAL_DUTIES.search(line):
        return "duties"
    if _LOCAL_BENEFITS.search(line):
        return "benefits"
    if _LOCAL_COMPANY.search(line):
        return "company"
    return section


def _clause_bounds(line: str, start: int, end: int) -> Tuple[int, int]:
    boundaries = [match.start() for match in re.finditer(r"[;!?]|\.(?=\s|$)", line)]
    left = max([point + 1 for point in boundaries if point < start] or [0])
    right = min([point for point in boundaries if point >= end] or [len(line)])
    return left, right


def _context_for_match(line: str, start: int, end: int, section: str) -> Tuple[str, bool]:
    """Resolve explicit qualifiers within the punctuation-bounded local clause."""
    left, right = _clause_bounds(line, start, end)
    clause = line[left:right]
    preferred = list(_LOCAL_PREFERRED.finditer(clause))
    required = list(_LOCAL_REQUIRED.finditer(clause))
    mixed = bool(preferred and required)
    if preferred or required:
        center = ((start - left) + (end - left)) / 2.0
        choices: List[Tuple[float, str]] = []
        choices.extend((abs(((m.start() + m.end()) / 2.0) - center), "preferred") for m in preferred)
        choices.extend((abs(((m.start() + m.end()) / 2.0) - center), "required") for m in required)
        choices.sort(key=lambda value: (value[0], value[1]))
        return choices[0][1], mixed
    return _line_context(clause, section), mixed


def _requirement_strength(context: str) -> str:
    if context in ("required", "preferred"):
        return context
    return "unspecified"


def _negated_candidate(line: str, start: int, end: int) -> bool:
    """Conservatively flag explicit negation near a candidate mention."""
    before = line[max(0, start - 60):start]
    after = line[end:min(len(line), end + 80)]
    return bool(
        re.search(r"\b(?:no|without)\s+(?:prior\s+)?(?:need\s+for\s+)?[^.;:]{0,35}$", before, re.I)
        or re.search(r"\b(?:do|does|is|are)\s+not\s+(?:require|need|expect)[^.;:]{0,35}$", before, re.I)
        or re.match(r"(?:\s+(?:skills?|knowledge|experience|degree))?\s+(?:is\s+|are\s+)?not\s+(?:required|needed|necessary|expected)\b", after, re.I)
    )


def _negated_or_optional(line: str, start: int, end: int) -> bool:
    before = line[max(0, start - 60):start]
    after = line[end:min(len(line), end + 80)]
    return bool(
        _negated_candidate(line, start, end)
        or re.search(r"\boptional\s+(?:knowledge\s+of\s+|experience\s+with\s+)?[^.;:]{0,35}$", before, re.I)
        or re.match(r"(?:\s+(?:skills?|knowledge|experience|degree))?\s+(?:is\s+|are\s+)?optional\b", after, re.I)
    )


def _line_records(text: str) -> Iterable[Tuple[str, int, str]]:
    section = "unknown"
    position = 0
    for line in text.split("\n"):
        start = position
        position += len(line) + 1
        new_section = _heading_context(line)
        if new_section is not None:
            section = new_section
            continue
        yield line, start, _line_context(line, section)


def _snippet(text: str, start: int, end: int, radius: int = 120) -> Tuple[str, int, int]:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    # Prefer line boundaries while keeping snippets bounded.
    line_left = text.rfind("\n", left, start)
    if line_left >= 0:
        left = line_left + 1
    line_right = text.find("\n", end, right)
    if line_right >= 0:
        right = line_right
    return text[left:right], left, right


def _evidence(
    normalized: str,
    module: str,
    candidate_type: str,
    value: Any,
    start: int,
    end: int,
    context: str,
    **extra: Any
) -> Dict[str, Any]:
    snippet, snippet_start, snippet_end = _snippet(normalized, start, end)
    item: Dict[str, Any] = {
        "module": module,
        "candidate_type": candidate_type,
        "value": value,
        "start": start,
        "end": end,
        "snippet": snippet,
        "snippet_start": snippet_start,
        "snippet_end": snippet_end,
        "context": context,
        "requirement_strength": _requirement_strength(context),
        "candidate_only": True,
    }
    item.update(extra)
    return item


_SOFTWARE: Dict[str, Sequence[Tuple[str, str]]] = {
    "office": (
        ("Microsoft Office", r"\b(?:Microsoft|MS)\s+Office\b"),
        ("Excel", r"\bExcel\b"),
        ("PowerPoint", r"\bPower\s*Point\b"),
        ("Microsoft Word", r"\b(?:Microsoft|MS)\s+Word\b"),
        ("Microsoft Access", r"\b(?:Microsoft|MS)\s+Access\b"),
        ("Google Sheets", r"\bGoogle\s+Sheets\b"),
    ),
    "data": (
        ("SQL", r"(?<![A-Za-z0-9_])SQL(?![A-Za-z0-9_])"),
        ("R", r"(?<![A-Za-z0-9_])R(?![A-Za-z0-9_]|&D\b)"),
        ("Tableau", r"\bTableau\b"),
        ("Power BI", r"\bPower\s*BI\b"),
        ("SAS", r"(?<![A-Za-z0-9_])SAS(?![A-Za-z0-9_])"),
        ("SPSS", r"\bSPSS\b"),
        ("Stata", r"\bStata\b"),
    ),
    "programming": (
        ("Python", r"\bPython\b"),
        ("Java", r"\bJava\b(?!\s*Script)"),
        ("JavaScript", r"\bJavaScript\b"),
        ("TypeScript", r"\bTypeScript\b"),
        ("C++", r"(?<![A-Za-z0-9_])C\+\+(?!\+)"),
        ("C#", r"(?<![A-Za-z0-9_])C#(?![A-Za-z0-9_])"),
        (".NET", r"(?<![A-Za-z0-9_])\.NET\b"),
        ("Ruby", r"\bRuby\b"),
        ("Go", r"(?<![A-Za-z0-9_])(?:Go|Golang)(?![A-Za-z0-9_])"),
        ("MATLAB", r"\bMATLAB\b"),
    ),
    "enterprise": (
        ("Salesforce", r"\bSalesforce\b"),
        ("SAP", r"(?<![A-Za-z0-9_])SAP(?![A-Za-z0-9_])"),
        ("Oracle", r"\bOracle\b"),
        ("Workday", r"\bWorkday\b"),
        ("ServiceNow", r"\bServiceNow\b"),
    ),
    "collaboration": (
        ("Slack", r"\bSlack\b"),
        ("Microsoft Teams", r"\bMicrosoft\s+Teams\b"),
        ("Zoom", r"\bZoom\b"),
        ("Jira", r"\bJira\b"),
        ("Confluence", r"\bConfluence\b"),
        ("Asana", r"\bAsana\b"),
        ("Trello", r"\bTrello\b"),
        ("GitHub", r"\bGitHub\b"),
        ("GitLab", r"\bGitLab\b"),
    ),
}

_AI_NAMES: Sequence[Tuple[str, str]] = (
    ("AI", r"(?<![A-Za-z0-9_])AI(?![A-Za-z0-9_])"),
    ("artificial intelligence", r"\bartificial\s+intelligence\b"),
    ("machine learning", r"\bmachine\s+learning\b"),
    ("generative AI", r"\bgenerative\s+AI\b"),
    ("ChatGPT", r"\bChatGPT\b"),
    ("OpenAI", r"\bOpenAI\b"),
    ("GPT", r"(?<![A-Za-z0-9_])GPT(?:-?\d+(?:\.\d+)?)?(?![A-Za-z0-9_])"),
    ("Claude", r"\bClaude\b"),
    ("Gemini", r"\bGemini\b"),
    ("Copilot", r"\b(?:GitHub|Microsoft)?\s*Copilot\b"),
    ("DALL-E", r"\bDALL[ -]?E\b"),
    ("Midjourney", r"\bMidjourney\b"),
)


def _extract_software(normalized: str, lines: Sequence[Tuple[str, int, str]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for line, base, context in lines:
        for group, terms in _SOFTWARE.items():
            for canonical, pattern in terms:
                for match in re.finditer(pattern, line, re.I if canonical not in ("R", "SQL", "SAS", "SAP", "C++", "C#", ".NET", "Go") else 0):
                    item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
                    ambiguous_excel_verb = False
                    if canonical == "Excel":
                        tail = line[match.end():]
                        ambiguous_excel_verb = bool(re.match(r"\s+(?:at|in|as|by|through|within)\b", tail, re.I))
                    start, end = base + match.start(), base + match.end()
                    negated = _negated_candidate(line, match.start(), match.end())
                    negated_or_optional = _negated_or_optional(line, match.start(), match.end())
                    clause_left, clause_right = _clause_bounds(line, match.start(), match.end())
                    local_clause = line[clause_left:clause_right]
                    ambiguous_programming_name = canonical == "Go" and not bool(re.search(
                        r"\b(?:Go|Golang)\s+(?:programming|language|developer)|"
                        r"\b(?:programming|language|developer|software|backend)\s+(?:in|with|using)?\s*(?:Go|Golang)\b|"
                        r"\b(?:experience|proficiency|knowledge|skills?)\s+(?:in|with|of)\s+(?:Go|Golang)\b",
                        local_clause, re.I,
                    ))
                    found.append(_evidence(
                        normalized, "software", "software_entity", canonical,
                        start, end, item_context, group=group,
                        matched_text=match.group(0),
                        ambiguous_excel_verb=ambiguous_excel_verb,
                        ambiguous_programming_name=ambiguous_programming_name,
                        negated=negated,
                        negated_or_optional=negated_or_optional,
                        mixed_requirement_scope=mixed_scope,
                        is_applicant_requirement=(item_context in ("required", "preferred") and not ambiguous_excel_verb and not ambiguous_programming_name and not negated_or_optional),
                    ))
    return found


def _ai_claim_type(line: str, context: str) -> str:
    if context == "company":
        return "company_or_marketing"
    if context == "duties":
        return "duty"
    if context in ("required", "preferred"):
        return "qualification"
    if re.search(r"\b(?:our|we)\b.*\b(?:platform|product|solution|company)\b", line, re.I):
        return "company_or_marketing"
    return "mention_unspecified"


def _extract_ai(normalized: str, lines: Sequence[Tuple[str, int, str]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    occupied: set = set()
    # Longer/specific names win over the generic AI token at the same location.
    for line, base, context in lines:
        for canonical, pattern in reversed(_AI_NAMES):
            for match in re.finditer(pattern, line, re.I if canonical not in ("AI", "GPT") else 0):
                start, end = base + match.start(), base + match.end()
                if any(start >= a and end <= b for a, b in occupied):
                    continue
                occupied.add((start, end))
                item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
                negated = _negated_candidate(line, match.start(), match.end())
                negated_or_optional = _negated_or_optional(line, match.start(), match.end())
                found.append(_evidence(
                    normalized, "ai", "ai_name_or_technology", canonical,
                    start, end, item_context, matched_text=match.group(0),
                    claim_type=_ai_claim_type(line, item_context),
                    adoption_claim=False,
                    negated=negated,
                    negated_or_optional=negated_or_optional,
                    mixed_requirement_scope=mixed_scope,
                    is_applicant_requirement=item_context in ("required", "preferred") and not negated_or_optional,
                ))
    return found


_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
_NUM = r"(?:\d{1,2}(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
_YEARS_EXPERIENCE = re.compile(
    r"(?P<prefix>at\s+least|minimum(?:\s+of)?|a\s+minimum\s+of|more\s+than|over|up\s+to)?\s*"
    r"(?P<lo>" + _NUM + r")\s*"
    r"(?:(?P<sep>-|–|—|to)\s*(?P<hi>" + _NUM + r")\s*)?"
    r"(?P<plus>\+|or\s+more)?\s*(?:years?|yrs?)(?:\s+of)?\s+"
    r"(?:(?P<descriptor>[A-Za-z][A-Za-z /&+.#-]{0,80}?)\s+)?experience\b",
    re.I,
)
_EXPERIENCE_AT_LEAST = re.compile(
    r"\bexperience\s+of\s+(?P<prefix>at\s+least|a\s+minimum\s+of|minimum(?:\s+of)?)\s+"
    r"(?P<lo>" + _NUM + r")\s*(?:years?|yrs?)\b", re.I,
)
_NO_EXPERIENCE = re.compile(
    r"\b(?:no\s+(?:prior\s+|previous\s+|professional\s+|work\s+)?experience\s+(?:is\s+)?(?:required|necessary|needed)|"
    r"experience\s+(?:is\s+)?not\s+(?:required|necessary|needed)|without\s+(?:prior\s+)?experience|"
    r"entry[- ]level\s*[;,:-]?\s*no\s+experience)\b", re.I,
)


def _number(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    lowered = value.lower()
    if lowered in _NUMBER_WORDS:
        return float(_NUMBER_WORDS[lowered])
    return float(value)


def _tidy_number(value: Optional[float]) -> Optional[Any]:
    if value is None:
        return None
    return int(value) if value.is_integer() else value


def _experience_scope(line: str, descriptor: str) -> str:
    scope_text = (descriptor + " " + line).lower()
    if re.search(r"\b(?:software|programming|coding|developer|python|java|sql|\.net|c\+\+|c#|erp|crm)\b", scope_text):
        return "software_or_tool"
    if re.search(r"\b(?:related|relevant|industry|field|domain|role|similar)\b", scope_text):
        return "related"
    if re.search(r"\b(?:professional|work|overall|general)\b", scope_text):
        return "general"
    return "unspecified"


def _extract_experience(normalized: str, lines: Sequence[Tuple[str, int, str]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for line, base, context in lines:
        occupied: List[Tuple[int, int]] = []
        for match in _NO_EXPERIENCE.finditer(line):
            item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
            start, end = base + match.start(), base + match.end()
            occupied.append((match.start(), match.end()))
            found.append(_evidence(
                normalized, "experience", "experience_clause", match.group(0),
                start, end, item_context, min_years=0, max_years=0,
                bound_type="no_experience", no_experience_explicit=True,
                scope="general", matched_text=match.group(0),
                negated_or_optional=True,
                mixed_requirement_scope=mixed_scope,
                is_applicant_requirement=False,
                overlapping_clauses_not_summed=True,
            ))
        for pattern in (_YEARS_EXPERIENCE, _EXPERIENCE_AT_LEAST):
            for match in pattern.finditer(line):
                if any(match.start() < b and match.end() > a for a, b in occupied):
                    continue
                occupied.append((match.start(), match.end()))
                lo = _number(match.group("lo"))
                hi = _number(match.groupdict().get("hi"))
                prefix = (match.groupdict().get("prefix") or "").lower()
                plus = bool(match.groupdict().get("plus"))
                if hi is not None:
                    bound_type = "range"
                elif plus or prefix in ("at least", "minimum", "minimum of", "a minimum of", "more than", "over"):
                    bound_type = "minimum"
                elif prefix == "up to":
                    bound_type = "maximum"
                    hi, lo = lo, None
                else:
                    bound_type = "exact_or_unspecified"
                descriptor = match.groupdict().get("descriptor") or ""
                start, end = base + match.start(), base + match.end()
                item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
                negated = _negated_candidate(line, match.start(), match.end())
                negated_or_optional = _negated_or_optional(line, match.start(), match.end())
                found.append(_evidence(
                    normalized, "experience", "experience_clause", match.group(0),
                    start, end, item_context,
                    min_years=_tidy_number(lo), max_years=_tidy_number(hi),
                    bound_type=bound_type, no_experience_explicit=False,
                    scope=_experience_scope(line, descriptor),
                    matched_text=match.group(0),
                    negated=negated,
                    negated_or_optional=negated_or_optional,
                    mixed_requirement_scope=mixed_scope,
                    is_applicant_requirement=item_context in ("required", "preferred") and not negated_or_optional,
                    overlapping_clauses_not_summed=True,
                ))
    return found


_DEGREES: Sequence[Tuple[str, str]] = (
    ("high_school", r"\b(?:high school diploma|high school degree|secondary school diploma|GED)\b"),
    ("associate", r"\b(?:associate(?:'s)? degree|AA|AS)\b"),
    ("bachelor", r"\b(?:bachelor(?:'s)? degree|baccalaureate|BA|BS|BSc)\b"),
    ("master", r"\b(?:master(?:'s)? degree|MA|MS|MSc|MBA)\b"),
    ("doctorate", r"\b(?:doctoral degree|doctorate|Ph\.?D\.?)\b"),
    ("unspecified_degree", r"\b(?:college|university) degree\b"),
)
_EQUIVALENT = re.compile(
    r"\b(?:or\s+(?:an?\s+)?equivalent(?:\s+(?:combination\s+of\s+)?(?:education\s+and/or\s+)?experience)?|"
    r"or\s+equivalent\s+work\s+experience|in\s+lieu\s+of\s+(?:a\s+)?degree|"
    r"degree\s+or\s+(?:[A-Za-z0-9+ -]+\s+)?experience)\b", re.I,
)


def _extract_education(normalized: str, lines: Sequence[Tuple[str, int, str]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for line, base, context in lines:
        equivalent = bool(_EQUIVALENT.search(line))
        alternative = line if equivalent else None
        for level, pattern in _DEGREES:
            flags = re.I
            for match in re.finditer(pattern, line, flags):
                # Short degree abbreviations are candidates only when uppercase in source.
                if match.group(0).lower() in ("ba", "bs", "bsc", "ma", "ms", "msc", "mba", "aa", "as") and not match.group(0).isupper():
                    continue
                start, end = base + match.start(), base + match.end()
                item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
                negated = _negated_candidate(line, match.start(), match.end())
                negated_or_optional = _negated_or_optional(line, match.start(), match.end())
                abbreviation = match.group(0).upper() in ("AA", "AS", "BA", "BS", "BSC", "MA", "MS", "MSC", "MBA")
                clause_left, clause_right = _clause_bounds(line, match.start(), match.end())
                local_clause = line[clause_left:clause_right]
                ambiguous_abbreviation = abbreviation and not bool(re.search(
                    r"\b(?:degree|education)\b|\b(?:AA|AS|BA|BS|BSc|MA|MS|MSc|MBA)\s+(?:in|from)\b",
                    local_clause,
                ))
                found.append(_evidence(
                    normalized, "education", "education_clause", level,
                    start, end, item_context, degree_level=level,
                    matched_text=match.group(0), equivalent_experience=equivalent,
                    alternative_path_text=alternative,
                    alternatives_retained=True,
                    negated=negated,
                    negated_or_optional=negated_or_optional,
                    ambiguous_degree_abbreviation=ambiguous_abbreviation,
                    mixed_requirement_scope=mixed_scope,
                    is_applicant_requirement=item_context in ("required", "preferred") and not negated_or_optional and not ambiguous_abbreviation,
                ))
    return found


_TASKS: Dict[str, Sequence[str]] = {
    "coding": (
        r"\b(?:write|develop|design|maintain|debug|test|review)\s+(?:[A-Za-z-]+\s+){0,3}(?:code|software|applications?|programs?|APIs?)\b",
        r"\b(?:code|program|debug)\s+(?:in|using|with)\b",
    ),
    "writing": (
        r"\b(?:write|draft|edit|prepare|author|create)\s+(?:[A-Za-z-]+\s+){0,3}(?:reports?|documentation|content|copy|proposals?|articles?|manuals?)\b",
    ),
    "data_analysis": (
        r"\b(?:analy[sz]e|interpret|model|visuali[sz]e|clean|query)\s+(?:[A-Za-z-]+\s+){0,3}(?:data|datasets?|metrics?|results?)\b",
        r"\b(?:data|statistical|quantitative)\s+analysis\b",
    ),
    "coordination": (
        r"\b(?:coordinate|organize|schedule|facilitate|manage)\s+(?:[A-Za-z-]+\s+){0,3}(?:projects?|meetings?|teams?|stakeholders?|workflows?|events?|deliverables?)\b",
        r"\bcross[- ]functional\s+(?:coordination|collaboration)\b",
    ),
    "customer_interaction": (
        r"\b(?:support|assist|advise|serve|onboard|train|communicate with|respond to)\s+(?:[A-Za-z-]+\s+){0,3}(?:customers?|clients?|users?|patients?|guests?)\b",
        r"\b(?:customer|client)\s+(?:support|service|interaction|communications?|meetings?)\b",
    ),
}


def _extract_tasks(normalized: str, lines: Sequence[Tuple[str, int, str]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for line, base, context in lines:
        for family, patterns in _TASKS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, line, re.I):
                    start, end = base + match.start(), base + match.end()
                    item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
                    found.append(_evidence(
                        normalized, "tasks", "task_family", family,
                        start, end, item_context, task_family=family,
                        matched_text=match.group(0), candidate_task_only=True,
                        negated_or_optional=_negated_or_optional(line, match.start(), match.end()),
                        mixed_requirement_scope=mixed_scope,
                        is_actual_duty_candidate=item_context == "duties" and not _negated_or_optional(line, match.start(), match.end()),
                        included_in_requirement_count=False,
                    ))
    return found


def _deduplicate(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for item in sorted(items, key=lambda x: (x["start"], x["end"], x["module"], str(x["value"]))):
        key = (item["module"], item["candidate_type"], str(item["value"]), item["start"], item["end"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _summary(module: str, items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "candidate" if items else "no_candidate",
        "candidate_count": len(items),
        "requirement_candidate_count": sum(bool(x.get("is_applicant_requirement")) for x in items),
        "company_or_benefits_evidence_count": sum(x["context"] in ("company", "benefits") for x in items),
    }
    if module == "software":
        groups: Dict[str, List[str]] = defaultdict(list)
        for item in items:
            if item["value"] not in groups[item["group"]]:
                groups[item["group"]].append(item["value"])
        result["entities_by_group"] = {key: values for key, values in sorted(groups.items())}
        result["ambiguous_excel_verb_count"] = sum(bool(x.get("ambiguous_excel_verb")) for x in items)
    elif module == "ai":
        result["names"] = sorted(set(str(x["value"]) for x in items))
        result["adoption_inferred"] = False
    elif module == "experience":
        result["no_experience_explicit"] = any(bool(x.get("no_experience_explicit")) for x in items)
        result["clauses_not_summed"] = True
    elif module == "education":
        result["degree_levels"] = sorted(set(str(x["degree_level"]) for x in items))
        result["has_equivalent_experience_path"] = any(bool(x.get("equivalent_experience")) for x in items)
    elif module == "tasks":
        result["families"] = sorted(set(str(x["task_family"]) for x in items))
        result["candidate_only"] = True
    return result


def _error_result(error: str) -> Dict[str, Any]:
    return {
        "record_kind": "CANDIDATES",
        "candidate_only": True,
        "normalization_version": NORMALIZATION_VERSION,
        "offset_coordinate_system": "normalized_text_python_codepoint_half_open",
        "normalized_text": "",
        "summary": {module: {"status": "parse_error", "candidate_count": 0} for module in MODULES},
        "evidence": [],
        "evidence_limit": EVIDENCE_LIMIT,
        "evidence_truncated": False,
        "evidence_total_before_truncation": 0,
        "module_evidence_truncated": {module: False for module in MODULES},
        "errors": [error],
    }


def extract(text: str) -> Dict[str, Any]:
    """Return bounded candidate summaries and normalized-text evidence.

    ``text`` is never modified. Invalid non-string input produces per-module
    ``parse_error`` statuses rather than being mislabeled as no requirement.
    A valid string with no dictionary hit produces ``no_candidate`` statuses;
    that status means only that this bounded extractor found no candidate.
    """

    if not isinstance(text, str):
        return _error_result("text must be str")
    try:
        normalized = _normalize(text)
        lines = list(_line_records(normalized))
        by_module: Dict[str, List[Dict[str, Any]]] = {
            "software": _extract_software(normalized, lines),
            "ai": _extract_ai(normalized, lines),
            "experience": _extract_experience(normalized, lines),
            "education": _extract_education(normalized, lines),
            "tasks": _extract_tasks(normalized, lines),
        }
        for module in MODULES:
            by_module[module] = _deduplicate(by_module[module])
        all_evidence = _deduplicate([item for module in MODULES for item in by_module[module]])
        returned = all_evidence[:EVIDENCE_LIMIT]
        returned_counts = defaultdict(int)
        for item in returned:
            returned_counts[item["module"]] += 1
        return {
            "record_kind": "CANDIDATES",
            "candidate_only": True,
            "normalization_version": NORMALIZATION_VERSION,
            "offset_coordinate_system": "normalized_text_python_codepoint_half_open",
            "normalized_text": normalized,
            "summary": {module: _summary(module, by_module[module]) for module in MODULES},
            "evidence": returned,
            "evidence_limit": EVIDENCE_LIMIT,
            "evidence_truncated": len(all_evidence) > EVIDENCE_LIMIT,
            "evidence_total_before_truncation": len(all_evidence),
            "module_evidence_truncated": {
                module: returned_counts[module] < len(by_module[module]) for module in MODULES
            },
            "errors": [],
        }
    except Exception as exc:  # A row-level failure must remain distinguishable.
        return _error_result("%s: %s" % (type(exc).__name__, exc))


__all__ = ["extract", "NORMALIZATION_VERSION", "EVIDENCE_LIMIT"]
