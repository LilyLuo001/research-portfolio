"""Deterministic recruitment-text candidate extraction.

The output of :func:`extract` is deliberately a set of *candidates* for human
validation.  It is not a set of validated requirements, economic measures, or
claims about employer adoption of a technology.

V5 separates qualification presence from strength.  In particular,
``is_applicant_qualification_candidate`` does not imply required, preferred,
or unconditional; ``is_applicant_requirement`` remains the narrower flag.

Only the Python standard library is used.  Evidence offsets use the returned
``normalized_text`` coordinate system, never the source HTML coordinate system.
"""

from __future__ import annotations

import html
import hashlib
import re
from collections import defaultdict
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


NORMALIZATION_VERSION = "recruitment-html-text-v5"
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


_PUNCTUATION_ESCAPES = {
    r"\u00a0": " ",
    r"\u2013": "–",
    r"\u2014": "—",
    r"\u2018": "‘",
    r"\u2019": "’",
    r"\u201c": "“",
    r"\u201d": "”",
    r"\u2022": "•",
}


def _controlled_literal_decoding(text: str) -> Tuple[str, Dict[str, Any]]:
    """Decode only strongly signaled layout escapes and known punctuation.

    This intentionally does not use ``unicode_escape``.  A lone ``\\n`` such as
    the one in ``C:\\new`` and unknown ``\\uXXXX`` sequences remain byte-for-byte
    text equivalents in the normalized input stage.
    """
    literal_newlines = len(re.findall(r"(?<!\\)\\n", text))
    layout_signal = bool(re.search(
        r"(?<!\\)\\n\s*(?:(?<!\\)\\n\s*)?(?:[*•-]\s+|"
        r"(?:requirements?|qualifications?|responsibilities|duties|benefits|"
        r"preferred qualifications?|minimum qualifications?|about(?: us)?|"
        r"equal opportunity|artificial intelligence statement|special instructions to applicants)\s*:?)",
        text, re.I,
    ))
    decode_newlines = literal_newlines >= 2 and layout_signal
    protected_spans: List[Tuple[int, int]] = []
    # Windows paths and quoted code/string literals can legitimately contain
    # the two characters backslash+n.  Their spans are protected even when the
    # surrounding advertisement is clearly serialized with escaped layout.
    for pattern in (
        r"(?i)\b[A-Z]:\\[^\s<>\"|?*]+",
        r"(?:[rubfRUBF]{0,2})?([\"'`])\\n\1",
        r"(?:=|return\s+|print\()\s*(?:[rubfRUBF]{0,2})?([\"'`])[^\"'`\r\n]{0,120}\\n[^\"'`\r\n]{0,120}\1",
    ):
        protected_spans.extend((m.start(), m.end()) for m in re.finditer(pattern, text))

    def is_protected(start: int, end: int) -> bool:
        return any(start >= left and end <= right for left, right in protected_spans)

    decoded = text
    protected_layout_escapes = 0
    if decode_newlines:
        def replace_layout(match: "re.Match[str]") -> str:
            nonlocal protected_layout_escapes
            if is_protected(match.start(), match.end()):
                protected_layout_escapes += 1
                return match.group(0)
            return "\n"

        decoded = re.sub(r"(?<!\\)\\(?:r\\n|n|r)", replace_layout, decoded)
    punctuation_applied: List[str] = []
    for escaped, replacement in _PUNCTUATION_ESCAPES.items():
        pattern = re.compile(r"(?<!\\)" + re.escape(escaped), re.I)
        if pattern.search(decoded):
            decoded = pattern.sub(replacement, decoded)
            punctuation_applied.append(escaped.lower())
    flags: Dict[str, Any] = {
        "had_actual_newline": "\n" in text or "\r" in text,
        "literal_backslash_n_count": literal_newlines,
        "literal_newline_layout_signal": layout_signal,
        "literal_newlines_decoded": decode_newlines,
        "protected_literal_layout_escape_count": protected_layout_escapes,
        "literal_unicode_escape_count": len(re.findall(r"(?<!\\)\\u[0-9a-fA-F]{4}", text)),
        "punctuation_escapes_decoded": punctuation_applied,
        "unknown_literal_unicode_escape_retained": bool(re.search(r"(?<!\\)\\u[0-9a-fA-F]{4}", decoded)),
        "html_markup_detected": bool(re.search(r"</?[A-Za-z][^>]*>", text)),
    }
    return decoded, flags


def _normalize_with_flags(text: str) -> Tuple[str, Dict[str, Any]]:
    decoded, flags = _controlled_literal_decoding(text)
    parser = _VisibleTextParser()
    parser.feed(decoded)
    parser.close()
    visible = html.unescape("".join(parser.parts))
    visible = visible.replace("\r\n", "\n").replace("\r", "\n")
    visible = visible.replace("\u00a0", " ").replace("\u200b", "")
    lines = []
    for line in visible.split("\n"):
        line = re.sub(r"[\t\f\v ]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines), flags


def _normalize(text: str) -> str:
    """Compatibility helper returning normalized text only."""
    return _normalize_with_flags(text)[0]


_HEADING_RULES = (
    ("preferred", re.compile(r"^(?:preferred|preferred qualifications?|preferred experience|nice to have|bonus(?: points)?|desired(?: qualifications?)?)(?:\s*:)?$", re.I)),
    ("required", re.compile(r"^(?:required|requirements?|other requirements?|position requirements?|education requirements?|other requirements?|basic qualifications?|required qualifications?|minimum|minimum requirements?|minimum qualifications?|what you(?:'|’)ll need|what you will need|what you will bring|what we require|what we expect from you|knowledge and skills|GS-\d+|education\s*/\s*experience required|experience and required skills)(?:\s*:)?$", re.I)),
    ("application_policy", re.compile(r"^(?:artificial intelligence statement|AI (?:application|applicant|recruiting|interview) policy|application process|how to apply|special instructions to applicants?|interview process|recruiting process)(?:\s*:)?$", re.I)),
    ("equal_opportunity", re.compile(r"^(?:equal opportunity(?: employment| employer)?|equal employment opportunity|EEO(?: statement)?|diversity and inclusion)(?:\s*:)?$", re.I)),
    ("qualification_unspecified", re.compile(r"^(?:qualifications?(?: and skills)?|position specifications?|who you are|education(?: and (?:experience|training))?|education and/or training|experience(?:\s*/\s*education)?)(?:\s*:)?$", re.I)),
    ("unknown", re.compile(r"^(?:physical demands?|work hours?|schedule|location)(?:\s*:)?$", re.I)),
    ("duties", re.compile(r"^(?:responsibilities|key responsibilities|duties|what you(?:'|’)ll do|what you will do|the role|about the role|job description|essential functions)(?:\s*:)?$", re.I)),
    ("company", re.compile(r"^(?:about(?: us| the company)?|about (?!the role\b|this role\b|the job\b).+|our company|who we are|company overview)(?:\s*:)?$", re.I)),
    ("benefits", re.compile(r"^(?:benefits|perks|what we offer(?: you)?|compensation(?: and benefits)?)(?:\s*:)?$", re.I)),
)

_INLINE_HEADING_RULES = (
    ("preferred", r"preferred(?: qualifications?)?|nice to have|desired(?: qualifications?)?"),
    ("required", r"requirements?|other requirements?|position requirements?|basic qualifications?|required qualifications?|minimum(?: requirements?| qualifications?)?|what you will need|what we expect from you"),
    ("application_policy", r"artificial intelligence statement|AI (?:application|applicant|recruiting|interview) policy|application process|how to apply|special instructions to applicants?"),
    ("equal_opportunity", r"equal opportunity(?: employment| employer)?|equal employment opportunity|EEO(?: statement)?"),
    ("duties", r"responsibilities|key responsibilities|duties|what you(?:'|’)ll do|what you will do|job description|essential functions"),
    ("company", r"about us|about the company|our company|company overview"),
    ("benefits", r"benefits|perks|what we offer(?: you)?|compensation(?: and benefits)?"),
    ("qualification_unspecified", r"qualifications?(?: and skills)?|position specifications?|education(?: and (?:experience|training))?|education and/or training|experience(?:\s*/\s*education)?"),
    ("unknown", r"physical demands?|work hours?|schedule|location"),
)

_EMBEDDED_HEADING = re.compile(
    r"(?P<label>REQUIRED QUALIFICATIONS|Required Qualifications|Preferred Qualifications|"
    r"Preferred qualifications|Basic Qualifications|Required Education|Education Requirements|"
    r"Minimum requirements|GS-\d+)(?P<delimiter>\s*:|\s+(?=(?:Candidates|Applicants)\s+should\s+have\b)|\s*(?=[•]))",
)

_EMBEDDED_HEADING_CONTEXT = {
    "required qualifications": "required",
    "basic qualifications": "required",
    "required education": "required",
    "education requirements": "required",
    "minimum requirements": "required",
    "preferred qualifications": "preferred",
}

_LOCAL_PREFERRED = re.compile(r"\b(?:preferred|preferably|desired|helpful|nice[- ]to[- ]have|(?:a|huge) plus|bonus)\b", re.I)
_LOCAL_REQUIRED = re.compile(r"\b(?:require(?:d|s)?|must(?: have)?|minimum qualification|need(?:ed)?|shall)\b", re.I)
_LOCAL_APPLICANT_EXPECTED = re.compile(r"\b(?:applicants?|candidates?)\s+should\s+have\b", re.I)
_LOCAL_DUTIES = re.compile(r"\b(?:responsib(?:le|ilities)|duties include|you will|you(?:'|’)ll)\b", re.I)
_LOCAL_COMPANY = re.compile(r"\b(?:our company|we are a|founded in|has been in business|company history)\b", re.I)
_LOCAL_BENEFITS = re.compile(r"\b(?:we offer|benefits include|paid time off|health insurance|salary|compensation)\b", re.I)
_LOCAL_EQUAL_OPPORTUNITY = re.compile(
    r"\b(?:equal opportunity employer|equal employment opportunity|protected characteristic|"
    r"military spouses? to apply|veterans?,? reservists? and national guard)\b", re.I,
)


def _heading_context(line: str) -> Optional[str]:
    cleaned = re.sub(r"^(?:#{1,6}|[*•-])\s*", "", line.strip())
    cleaned = re.sub(r"\s*\*+\s*$", "", cleaned)
    if len(cleaned) > 80:
        return None
    for context, pattern in _HEADING_RULES:
        if pattern.match(cleaned):
            return context
    return None


def _line_context(line: str, section: str) -> str:
    # Explicit wording closest to the candidate takes precedence over a heading.
    if section == "company" and _LOCAL_DUTIES.search(line):
        return "duties"
    if section in ("company", "benefits", "application_policy", "equal_opportunity"):
        return section
    if _LOCAL_EQUAL_OPPORTUNITY.search(line):
        return "equal_opportunity"
    if _LOCAL_PREFERRED.search(line):
        return "preferred"
    if _LOCAL_REQUIRED.search(line):
        return "required"
    if _LOCAL_APPLICANT_EXPECTED.search(line):
        return "qualification_expected"
    if _LOCAL_DUTIES.search(line):
        return "duties"
    if _LOCAL_BENEFITS.search(line):
        return "benefits"
    if _LOCAL_COMPANY.search(line):
        return "company"
    return section


def _clause_bounds(line: str, start: int, end: int) -> Tuple[int, int]:
    boundaries = list(re.finditer(r"[;!?]|\.(?=\s|$)|(?<=\s)[•-](?=\s)", line))
    left = max([match.end() for match in boundaries if match.start() < start] or [0])
    right = min([match.start() for match in boundaries if match.start() >= end] or [len(line)])
    return left, right


def _clause_text(line: str, left: int, right: int) -> str:
    terminal = line[right:right + 1] if right < len(line) and line[right] in ".!?;" else ""
    return (line[left:right] + terminal).strip()


def _context_for_match(line: str, start: int, end: int, section: str) -> Tuple[str, bool]:
    """Resolve explicit qualifiers within the punctuation-bounded local clause."""
    left, right = _clause_bounds(line, start, end)
    clause = line[left:right]
    if section == "company" and _LOCAL_DUTIES.search(clause):
        return "duties", False
    if section in ("company", "benefits", "application_policy", "equal_opportunity"):
        return section, False
    if _LOCAL_EQUAL_OPPORTUNITY.search(clause):
        return "equal_opportunity", False
    preferred = list(_LOCAL_PREFERRED.finditer(clause))
    required = list(_LOCAL_REQUIRED.finditer(clause))
    mixed = bool(preferred and required)
    if section == "preferred" and required:
        return "preferred", True
    if preferred or required:
        center = ((start - left) + (end - left)) / 2.0
        choices: List[Tuple[float, str]] = []
        choices.extend((abs(((m.start() + m.end()) / 2.0) - center), "preferred") for m in preferred)
        choices.extend((abs(((m.start() + m.end()) / 2.0) - center), "required") for m in required)
        choices.sort(key=lambda value: (value[0], value[1]))
        return choices[0][1], mixed
    if _LOCAL_APPLICANT_EXPECTED.search(clause):
        return "qualification_expected", False
    return _line_context(clause, section), mixed


def _context_conflict_for_match(line: str, start: int, end: int, section: str) -> bool:
    left, right = _clause_bounds(line, start, end)
    clause = line[left:right]
    local_preferred = bool(_LOCAL_PREFERRED.search(clause))
    local_required = bool(_LOCAL_REQUIRED.search(clause))
    return bool(
        (local_preferred and local_required)
        or (section == "preferred" and local_required)
        or (section == "required" and local_preferred)
    )


def _requirement_strength(context: str) -> str:
    if context in ("required", "preferred"):
        return context
    if context == "qualification_expected":
        return "expected_unspecified_mandatoriness"
    return "unspecified"


def _negated_candidate(line: str, start: int, end: int) -> bool:
    """Conservatively flag explicit negation near a candidate mention."""
    before = line[max(0, start - 60):start]
    after = line[end:min(len(line), end + 80)]
    return bool(
        re.search(r"\b(?:no|without)\s+(?:prior\s+)?(?:need\s+for\s+)?[^.;:]{0,35}$", before, re.I)
        or re.search(r"\b(?:do|does|is|are)\s+not\s+(?:require|need|expect)[^.;:]{0,35}$", before, re.I)
        or re.match(r"(?:\s+(?:skills?|knowledge|experience|degree))?\s+(?:is\s+|are\s+)?not\s+(?:required|needed|necessary|expected)\b", after, re.I)
        or re.search(r"^[^.;]{0,80}\bnot\s+(?:required|needed|necessary|expected)\b", after, re.I)
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
        cleaned = re.sub(r"^(?:#{1,6}|[*•-])\s*", "", line.strip())
        if re.fullmatch(r"Experience\s*:?,?", cleaned, re.I):
            # Keep this token for the bounded next-line duration binder while
            # propagating qualification presence to the following field value.
            section = "qualification_unspecified"
            yield line, start, section
            continue
        new_section = _heading_context(line)
        if new_section is not None:
            section = new_section
            continue
        embedded = list(_EMBEDDED_HEADING.finditer(line))
        if embedded:
            cursor = 0
            for heading in embedded:
                preceding = line[cursor:heading.start()]
                if preceding.strip():
                    leading = len(preceding) - len(preceding.lstrip())
                    yield preceding.strip(), start + cursor + leading, section
                label = heading.group("label").lower()
                section = "required" if label.startswith("gs-") else _EMBEDDED_HEADING_CONTEXT[label]
                cursor = heading.end()
            trailing = line[cursor:]
            if trailing.strip():
                leading = len(trailing) - len(trailing.lstrip())
                yield trailing.strip(), start + cursor + leading, section
            continue
        inline = None
        for candidate_context, label in _INLINE_HEADING_RULES:
            match = re.match(r"^(?:[*•#-]\s*)?(?:" + label + r")\s*:\s*(?P<body>.+)$", line, re.I)
            if match:
                inline = (candidate_context, match)
                break
        if inline is not None:
            section, match = inline
            body = match.group("body")
            yield body, start + match.start("body"), section
        else:
            yield line, start, section


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
        "is_applicant_qualification_candidate": module != "tasks" and context in (
            "required", "preferred", "qualification_expected", "qualification_unspecified"
        ),
        "candidate_only": True,
    }
    item.update(extra)
    # Presence is broader than mandatory/preferred strength, but explicit
    # negation, optionality, no-experience statements, and ambiguous degree
    # abbreviations remain excluded from positive qualification presence.
    if (
        item.get("negated_or_optional")
        or item.get("no_experience_explicit")
        or item.get("ambiguous_degree_abbreviation")
    ):
        item["is_applicant_qualification_candidate"] = False
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
                        context_conflict=_context_conflict_for_match(line, match.start(), match.end(), context),
                        is_applicant_requirement=(item_context in ("required", "preferred") and not ambiguous_excel_verb and not ambiguous_programming_name and not negated_or_optional),
                    ))
    return found


def _ai_claim_type(line: str, context: str) -> str:
    if context == "company":
        return "company_or_marketing"
    if context == "application_policy":
        return "applicant_ai_policy"
    if context == "equal_opportunity":
        return "equal_opportunity_statement"
    if context == "benefits":
        return "benefits_or_boilerplate"
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
                    context_conflict=_context_conflict_for_match(line, match.start(), match.end(), context),
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
_DURATION_EXPERIENCE = re.compile(
    r"(?P<prefix>at\s+least|minimum(?:\s+of)?|a\s+minimum\s+of|more\s+than|over|up\s+to)?\s*"
    r"(?P<lo>" + _NUM + r")(?:\s*\(\d{1,2}\))?\s*"
    r"(?:(?P<sep>-|–|—|to)\s*(?P<hi>" + _NUM + r")\s*)?"
    r"(?P<plus>\+|or\s+more)?\s*(?P<unit>years?|yrs?\.?|months?|mos?\.?)\s*"
    r"(?:['’]\s*,?\s*|of\s+|,\s*)?"
    r"(?P<descriptor>(?:[A-Za-z]|\.(?=NET\b))[^.;\n]{0,119}?)?\s*experience\b",
    re.I,
)
_EXPERIENCE_AT_LEAST = re.compile(
    r"\bexperience\s+of\s+(?P<prefix>at\s+least|a\s+minimum\s+of|minimum(?:\s+of)?)\s+"
    r"(?P<lo>" + _NUM + r")\s*(?P<unit>years?|yrs?\.?|months?|mos?\.?)\b", re.I,
)
_NO_EXPERIENCE = re.compile(
    r"\b(?:no\s+(?:prior\s+|previous\s+|professional\s+|work\s+)?experience\s+(?:is\s+)?(?:required|necessary|needed)|"
    r"experience\s+(?:is\s+)?not\s+(?:required|necessary|needed)|without\s+(?:prior\s+)?experience|"
    r"entry[- ]level\s*[;,:-]?\s*no\s+experience)\b", re.I,
)
_GENERIC_EXPERIENCE = re.compile(
    r"\b(?:(?:prior|previous|relevant|related|professional|work|industry|hands[- ]on|"
    r"demonstrated|equivalent|management|development|customer service)\s+){0,3}experience\b",
    re.I,
)
_QUALIFICATION_BACKGROUND = re.compile(
    r"\b(?P<descriptor>sales|business development|marketing|accounting|audit|tax|"
    r"engineering|technical|healthcare|clinical|nursing|education|teaching|finance|"
    r"banking|insurance|construction|manufacturing|operations|management|customer service)"
    r"(?:\s+or\s+(?:sales|business development|marketing|technical|clinical|management))?"
    r"\s+background\b",
    re.I,
)
_APPLICANT_EXPERIENCE_ATTRIBUTE = re.compile(
    r"\b(?:(?:the\s+)?(?:candidate|applicant|individual|incumbent)\s+(?:has|possesses?|brings?)|"
    r"you\s+(?:have|bring)|skilled\s+in[^.;]{0,100}\band\s+has)\s+"
    r"(?:[A-Za-z-]+\s+){0,3}experience\s+and\s+knowledge\s+"
    r"(?:in|with|related\s+to)\b",
    re.I,
)
_DURATION_ONLY = re.compile(
    r"^\s*(?P<prefix>at\s+least|minimum(?:\s+of)?|a\s+minimum\s+of|more\s+than|over|up\s+to)?\s*"
    r"(?P<lo>" + _NUM + r")(?:\s*\(\d{1,2}\))?\s*"
    r"(?:(?P<sep>-|–|—|to)\s*(?P<hi>" + _NUM + r")\s*)?"
    r"(?P<plus>\+|or\s+more)?\s*(?P<unit>years?|yrs?\.?|months?|mos?\.?)"
    r"(?:\s+(?:required|preferred))?\s*[.!]?\s*$",
    re.I,
)
_DURATION_HEADING_LINE = re.compile(
    r"^\s*(?P<prefix>at\s+least|minimum(?:\s+of)?|a\s+minimum\s+of|more\s+than|over|up\s+to)?\s*"
    r"(?P<lo>" + _NUM + r")(?:\s*\(\d{1,2}\))?\s*"
    r"(?:(?P<sep>-|–|—|to)\s*(?P<hi>" + _NUM + r")\s*)?"
    r"(?P<plus>\+|or\s+more)?\s*(?P<unit>years?|yrs?\.?|months?|mos?\.?)"
    r"(?P<descriptor>\s+(?!of\s+(?:age|service)\b)[^.;\n]{1,120})?[.!]?\s*$",
    re.I,
)
_ALTERNATIVE_PATH = re.compile(
    r"\b(?:or|and/or)\b[^.;]{0,100}\b(?:formal\s+training|training|education|degree|certification)\b|"
    r"\bcombination\s+of\s+(?:education|training|experience)[^.;]{0,100}\b(?:education|training|experience)\b|"
    r"\b(?:degree|diploma|GED|education|training|certification)\b[^.;]{0,100}\bor\b[^.;]{0,80}\bexperience\b",
    re.I,
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


def _duration_to_years(value: Optional[float], unit: str) -> Optional[float]:
    if value is None:
        return None
    return value / 12.0 if unit == "months" else value


def _canonical_unit(raw_unit: str) -> str:
    return "months" if raw_unit.lower().startswith(("month", "mo")) else "years"


def _experience_scope(descriptor: str) -> str:
    scope_text = descriptor.lower()
    if re.search(r"\b(?:software|programming|coding|developer|python|java|sql|\.net|c\+\+|c#|erp|crm)\b", scope_text):
        return "software_or_tool"
    if re.search(r"\b(?:related|relevant|industry|field|domain|role|similar)\b", scope_text):
        return "related"
    if re.search(r"\b(?:professional|work|overall|general)\b", scope_text):
        return "general"
    if re.search(r"\b(?:management|restaurant|childcare|insurance|financial|healthcare|sales|marketing|office|as an?|with)\b", scope_text):
        return "industry_or_occupation"
    return "unspecified"


def _experience_heading_token(line: str, start: int, end: int) -> bool:
    cleaned = re.sub(r"^(?:#{1,6}|[*•-])\s*", "", line.strip())
    if re.fullmatch(r"experience\s*:?", cleaned, re.I):
        return True
    for slash_heading in re.finditer(r"(?:[A-Z]+\s*/\s*){2,}[A-Z]+", line):
        if slash_heading.start() <= start and end <= slash_heading.end():
            return True
    composite = re.match(
        r"^(?:[*•#-]\s*)?[A-Z][A-Z /,&-]{0,100}\bEXPERIENCE\b[A-Z /,&:-]{0,100}",
        line,
    )
    if composite is not None and start < composite.end():
        return True
    if cleaned.isupper() and re.search(r"\b(?:skills?|education|knowledge|abilities)\b", cleaned, re.I) and len(cleaned) <= 100:
        return True
    return False


def _extract_experience(normalized: str, lines: Sequence[Tuple[str, int, str]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    # Bind only a standalone Experience heading to one immediately following
    # duration-only line. This recovers "Experience:\nOne to three years"
    # without turning arbitrary headings into experience evidence.
    for index in range(len(lines) - 1):
        heading_line, _, heading_context = lines[index]
        if not re.fullmatch(r"\s*Experience\s*:\s*", heading_line, re.I):
            continue
        next_line, next_base, next_context = lines[index + 1]
        duration_match = _DURATION_ONLY.fullmatch(next_line) or _DURATION_HEADING_LINE.fullmatch(next_line)
        if duration_match is None:
            continue
        if re.search(
            r"\b(?:after hire|upon hire|within \d+ (?:days?|months?) of (?:hire|employment)|"
            r"benefits?|salary|paid time off|vacation|hours? per week)\b",
            next_line,
            re.I,
        ):
            continue
        lo = _number(duration_match.group("lo"))
        hi = _number(duration_match.groupdict().get("hi"))
        prefix = (duration_match.groupdict().get("prefix") or "").lower()
        plus = bool(duration_match.groupdict().get("plus"))
        raw_unit = duration_match.group("unit")
        unit = _canonical_unit(raw_unit)
        descriptor = duration_match.groupdict().get("descriptor") or ""
        if hi is not None:
            bound_type = "range"
        elif plus or prefix in ("at least", "minimum", "minimum of", "a minimum of", "more than", "over"):
            bound_type = "minimum"
        elif prefix == "up to":
            bound_type = "maximum"
            hi, lo = lo, None
        else:
            bound_type = "exact_or_unspecified"
        item_context = next_context if next_context in ("required", "preferred") else heading_context
        start, end = next_base + duration_match.start(), next_base + duration_match.end()
        found.append(_evidence(
            normalized, "experience", "experience_clause", duration_match.group(0),
            start, end, item_context,
            min_years=_tidy_number(_duration_to_years(lo, unit)),
            max_years=_tidy_number(_duration_to_years(hi, unit)),
            min_duration=_tidy_number(lo), max_duration=_tidy_number(hi),
            duration_unit=unit, original_duration_unit=raw_unit,
            has_explicit_duration=True, bound_type=bound_type,
            no_experience_explicit=False, scope=_experience_scope(descriptor),
            matched_text=duration_match.group(0), negated=False,
            negated_or_optional=False, alternative_training_or_education=False,
            alternative_path_text=None, is_unconditional_experience_requirement=True,
            mixed_requirement_scope=False,
            is_applicant_requirement=item_context in ("required", "preferred"),
            overlapping_clauses_not_summed=True,
            bound_from_experience_heading=True,
            experience_heading_text=heading_line.strip(),
            heading_bound_descriptor=descriptor.strip() or None,
        ))
    for line_index, (line, base, context) in enumerate(lines):
        occupied: List[Tuple[int, int]] = []
        for match in _NO_EXPERIENCE.finditer(line):
            item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
            start, end = base + match.start(), base + match.end()
            occupied.append((match.start(), match.end()))
            found.append(_evidence(
                normalized, "experience", "experience_clause", match.group(0),
                start, end, item_context, min_years=0, max_years=0,
                min_duration=0, max_duration=0, duration_unit="years",
                original_duration_unit=None, has_explicit_duration=True,
                bound_type="no_experience", no_experience_explicit=True,
                scope="general", matched_text=match.group(0),
                negated_or_optional=True,
                alternative_training_or_education=False,
                alternative_path_text=None,
                is_unconditional_experience_requirement=False,
                mixed_requirement_scope=mixed_scope,
                context_conflict=_context_conflict_for_match(line, match.start(), match.end(), context),
                is_applicant_requirement=False,
                overlapping_clauses_not_summed=True,
            ))
        for pattern in (_DURATION_EXPERIENCE, _EXPERIENCE_AT_LEAST):
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
                raw_unit = match.groupdict().get("unit") or "years"
                unit = _canonical_unit(raw_unit)
                min_years = _duration_to_years(lo, unit)
                max_years = _duration_to_years(hi, unit)
                start, end = base + match.start(), base + match.end()
                item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
                negated = _negated_candidate(line, match.start(), match.end())
                negated_or_optional = _negated_or_optional(line, match.start(), match.end())
                clause_left, clause_right = _clause_bounds(line, match.start(), match.end())
                local_clause = line[clause_left:clause_right]
                relation_unresolved = _qualification_relation_unresolved(local_clause) or _cross_line_or_path(lines, line_index)
                alternative_path, alternative_text = _locally_associated_alternative(
                    _ALTERNATIVE_PATH, local_clause,
                    match.start() - clause_left, match.end() - clause_left,
                )
                found.append(_evidence(
                    normalized, "experience", "experience_clause", match.group(0),
                    start, end, item_context,
                    min_years=_tidy_number(min_years), max_years=_tidy_number(max_years),
                    min_duration=_tidy_number(lo), max_duration=_tidy_number(hi),
                    duration_unit=unit, original_duration_unit=raw_unit,
                    has_explicit_duration=True,
                    bound_type=bound_type, no_experience_explicit=False,
                    scope=_experience_scope((descriptor + " " + local_clause).strip()),
                    matched_text=match.group(0),
                    negated=negated,
                    negated_or_optional=negated_or_optional,
                    alternative_training_or_education=alternative_path,
                    alternative_path_text=alternative_text,
                    alternative_scope_local=True,
                    qualification_relation_unresolved=relation_unresolved,
                    is_unconditional_experience_requirement=not alternative_path and not relation_unresolved,
                    mixed_requirement_scope=mixed_scope,
                    context_conflict=_context_conflict_for_match(line, match.start(), match.end(), context),
                    is_applicant_requirement=item_context in ("required", "preferred") and not negated_or_optional and not alternative_path and not relation_unresolved,
                    overlapping_clauses_not_summed=True,
                ))
        for match in _QUALIFICATION_BACKGROUND.finditer(line):
            if any(match.start() < b and match.end() > a for a, b in occupied):
                continue
            item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
            if item_context in ("company", "benefits", "application_policy", "equal_opportunity", "duties"):
                continue
            occupied.append((match.start(), match.end()))
            clause_left, clause_right = _clause_bounds(line, match.start(), match.end())
            local_clause = line[clause_left:clause_right]
            relation_unresolved = _qualification_relation_unresolved(local_clause) or _cross_line_or_path(lines, line_index)
            alternative_path, alternative_text = _locally_associated_alternative(
                _ALTERNATIVE_PATH, local_clause,
                match.start() - clause_left, match.end() - clause_left,
            )
            negated_or_optional = _negated_or_optional(line, match.start(), match.end())
            start, end = base + match.start(), base + match.end()
            found.append(_evidence(
                normalized, "experience", "experience_clause", match.group(0),
                start, end, item_context, min_years=None, max_years=None,
                min_duration=None, max_duration=None, duration_unit=None,
                original_duration_unit=None, has_explicit_duration=False,
                bound_type="duration_unspecified", no_experience_explicit=False,
                scope="industry_or_occupation", matched_text=match.group(0),
                negated=_negated_candidate(line, match.start(), match.end()),
                negated_or_optional=negated_or_optional,
                alternative_training_or_education=alternative_path, alternative_path_text=alternative_text,
                alternative_scope_local=True, qualification_relation_unresolved=relation_unresolved,
                is_unconditional_experience_requirement=not alternative_path and not relation_unresolved,
                mixed_requirement_scope=mixed_scope,
                context_conflict=_context_conflict_for_match(line, match.start(), match.end(), context),
                is_applicant_requirement=item_context in ("required", "preferred") and not negated_or_optional and not alternative_path and not relation_unresolved,
                overlapping_clauses_not_summed=True,
                qualification_presence_rule="explicit_domain_background",
            ))
        for match in _GENERIC_EXPERIENCE.finditer(line):
            if any(match.start() < b and match.end() > a for a, b in occupied):
                continue
            if _experience_heading_token(line, match.start(), match.end()):
                continue
            item_context, mixed_scope = _context_for_match(line, match.start(), match.end(), context)
            modifier = match.group(0)
            clause_left, clause_right = _clause_bounds(line, match.start(), match.end())
            local_clause = line[clause_left:clause_right]
            applicant_attribute = bool(_APPLICANT_EXPERIENCE_ATTRIBUTE.search(local_clause))
            if item_context == "unknown" and applicant_attribute:
                item_context = "qualification_unspecified"
            # Bare mentions in unknown prose are retained only when the local
            # clause supplies a qualification cue or a meaningful modifier.
            meaningful_modifier = modifier.lower() != "experience"
            if item_context == "unknown" and not meaningful_modifier:
                continue
            relation_unresolved = _qualification_relation_unresolved(local_clause) or _cross_line_or_path(lines, line_index)
            alternative_path, alternative_text = _locally_associated_alternative(
                _ALTERNATIVE_PATH, local_clause,
                match.start() - clause_left, match.end() - clause_left,
            )
            negated_or_optional = _negated_or_optional(line, match.start(), match.end())
            start, end = base + match.start(), base + match.end()
            found.append(_evidence(
                normalized, "experience", "experience_clause", match.group(0),
                start, end, item_context, min_years=None, max_years=None,
                min_duration=None, max_duration=None, duration_unit=None,
                original_duration_unit=None, has_explicit_duration=False,
                bound_type="duration_unspecified", no_experience_explicit=False,
                scope=_experience_scope(local_clause), matched_text=match.group(0),
                negated=_negated_candidate(line, match.start(), match.end()),
                negated_or_optional=negated_or_optional,
                alternative_training_or_education=alternative_path,
                alternative_path_text=alternative_text,
                alternative_scope_local=True,
                qualification_relation_unresolved=relation_unresolved,
                is_unconditional_experience_requirement=not alternative_path and not relation_unresolved,
                mixed_requirement_scope=mixed_scope,
                context_conflict=_context_conflict_for_match(line, match.start(), match.end(), context),
                is_applicant_requirement=item_context in ("required", "preferred") and not negated_or_optional and not alternative_path and not relation_unresolved,
                overlapping_clauses_not_summed=True,
                qualification_presence_rule="applicant_attribute" if applicant_attribute else "section_or_local_cue",
            ))
    return found


_DEGREES: Sequence[Tuple[str, str]] = (
    ("high_school", r"\b(?:high school diploma|high school degree|high school graduate|secondary school diploma|H\.?\s*S\.?\s+(?:diploma|degree)|GED)\b"),
    ("associate", r"\b(?:associate(?:['’]?s)? degree|AA|AS)\b"),
    ("bachelor", r"\b(?:bachelor(?:['’]?s)?(?:\s+degree|(?=\s+(?:or|and)\s+master(?:['’]?s)?\s+degree))|baccalaureate|B\.?\s*A\.?|B\.?\s*S\.?|BSc)\b"),
    ("undergraduate", r"\bundergraduate degree\b"),
    ("advanced_degree", r"\badvanced degree\b"),
    ("master", r"\b(?:master(?:['’]?s)? degree|MA|MS|MSc|MBA)\b"),
    ("doctorate", r"\b(?:doctoral degree|doctorate|Ph\.?D\.?)\b"),
    ("vocational_program", r"\bgraduate of (?:an?\s+)?(?:approved\s+)?(?:practical|vocational) nursing\b"),
    ("training_program", r"\bgraduation from (?:an?\s+)?(?:approved\s+)?(?:medical assistant|practical nursing|vocational nursing) program\b"),
    ("certificate_program", r"\bcompletion of (?:an?\s+)?[A-Za-z -]{0,40}certificate program\b"),
    ("unspecified_degree", r"\b(?:college|university) degree\b"),
    ("unspecified_degree", r"\b(?:appropriate\s+)?degree\s+from\s+an?\s+accredited\s+institution\b"),
)
_EQUIVALENT_EXPERIENCE = re.compile(
    r"\b(?:or\s+(?:an?\s+)?equivalent(?:\s+combination\s+of\s+education\s+and)?\s+(?:work\s+)?experience|"
    r"or\s+equivalent\s+work\s+experience|in\s+lieu\s+of\s+(?:a\s+)?degree|"
    r"degree\s+or\s+(?:(?:" + _NUM + r")\s*(?:\+|or\s+more)?\s*(?:years?|yrs?)\s+(?:of\s+)?)?"
    r"(?:equivalent\s+|related\s+|work\s+|professional\s+)*experience)\b",
    re.I,
)
_EQUIVALENT_CREDENTIAL = re.compile(
    r"\bor\s+(?:an?\s+)?equivalent\b(?!\s+(?:work\s+)?experience|\s+combination\s+of\s+education\s+and\s+experience)",
    re.I,
)
_EDUCATION_ALTERNATIVE = re.compile(
    r"\b(?:degree|diploma|GED|education)\b[^.;]{0,70}\b(?:or|and/or)\b"
    r"(?:(?!\b(?:plus|degree|diploma|GED)\b)[^.;]){0,70}\b(?:experience|formal\s+training|certification)\b|"
    r"\b(?:or|and/or)\s+(?:an?\s+)?(?:equivalent\s+(?:work\s+)?experience|formal\s+training|certification)\b|"
    r"\bgraduation from\b[^.;]{0,240}\bor\b[^.;]{0,80}\b(?:military\s+)?training\b[^.;]{0,50}\bexperience\b|"
    r"\bin\s+lieu\s+of\s+(?:a\s+)?degree\b",
    re.I,
)
_DEGREE_MARKER = re.compile(
    r"\b(?:high school (?:diploma|degree|graduate)|secondary school diploma|H\.?\s*S\.?\s+(?:diploma|degree)|GED|"
    r"associate(?:['’]?s)? degree|bachelor(?:['’]?s)? degree|baccalaureate|"
    r"undergraduate degree|advanced degree|"
    r"master(?:['’]?s)? degree|doctoral degree|doctorate|Ph\.?D\.?|"
    r"(?:college|university) degree|(?:appropriate\s+)?degree\s+from\s+an?\s+accredited\s+institution)\b",
    re.I,
)


def _education_scope_bounds(
    line: str, start: int, end: int, clause_left: int, clause_right: int
) -> Tuple[int, int, str]:
    """Return a bounded local path scope for one credential mention.

    Parentheses and commas separating two explicit credentials are useful
    boundaries. Ordinary field lists (``degree in marketing, finance``) do not
    create a boundary because the neighboring text has no credential marker.
    This intentionally is not a full qualification-relationship parser.
    """
    def has_path_cue(value: str) -> bool:
        return bool(
            _LOCAL_REQUIRED.search(value)
            or _LOCAL_PREFERRED.search(value)
            or _EDUCATION_ALTERNATIVE.search(value)
        )

    open_at = line.rfind("(", clause_left, start)
    close_before = line.rfind(")", clause_left, start)
    close_at = line.find(")", end, clause_right)
    if open_at >= clause_left and open_at > close_before and close_at >= 0:
        parenthetical = line[open_at + 1:close_at]
        if has_path_cue(parenthetical):
            return open_at + 1, close_at, "parenthetical"

    next_open = line.find("(", end, clause_right)
    next_close = line.find(")", next_open + 1, clause_right) if next_open >= 0 else -1
    if next_open >= 0 and next_close >= 0:
        parenthetical = line[next_open + 1:next_close]
    else:
        parenthetical = ""
    if parenthetical and _DEGREE_MARKER.search(parenthetical) and has_path_cue(parenthetical):
        clause_right = next_open
        right_rule = "before_parenthetical"
    else:
        right_rule = "clause"

    left = clause_left
    right = clause_right
    for comma_match in re.finditer(r",", line[clause_left:clause_right]):
        comma = comma_match.start() + clause_left
        if comma < start and _DEGREE_MARKER.search(line[clause_left:comma]):
            left = comma + 1
        elif comma >= end and _DEGREE_MARKER.search(line[comma + 1:clause_right]):
            right = comma
            break
    if left != clause_left or right != clause_right:
        return left, right, "credential_comma"
    return left, right, right_rule


def _locally_associated_alternative(
    pattern: "re.Pattern[str]", scope: str, relative_start: int, relative_end: int
) -> Tuple[bool, Optional[str]]:
    """Associate a conjunction path only with the nearby mention it qualifies."""
    matches: List[str] = []
    for candidate in pattern.finditer(scope):
        overlaps = candidate.start() < relative_end and candidate.end() > relative_start
        immediately_after = 0 <= candidate.start() - relative_end <= 12
        immediately_before = 0 <= relative_start - candidate.end() <= 12
        if overlaps or immediately_after or immediately_before:
            matches.append(candidate.group(0))
    return bool(matches), " ".join(matches) if matches else None


def _qualification_relation_unresolved(clause: str) -> bool:
    """Flag a bounded OR-of-combinations without flattening either path."""
    paths = re.split(r"\b(?:or|and/or)\b", clause, flags=re.I)
    combined_paths = [
        path for path in paths
        if _DEGREE_MARKER.search(path) and re.search(r"\bexperience\b", path, re.I)
    ]
    return len(combined_paths) >= 2


def _cross_line_or_path(lines: Sequence[Tuple[str, int, str]], index: int) -> bool:
    """Retain adjacent list-item OR paths without claiming a full graph."""
    current = lines[index][0].strip()
    previous = lines[index - 1][0].strip() if index else ""
    return bool(
        re.search(r"\bOR\s*$", current, re.I)
        or (re.search(r"\bOR\s*$", previous, re.I) and re.search(r"\b(?:degree|diploma|experience)\b", current, re.I))
    )


def _ambiguous_degree_abbreviation(token: str, clause: str, context: str) -> bool:
    upper = re.sub(r"[.\s]", "", token.upper())
    if upper not in ("AA", "AS", "BA", "BS", "BSC", "MA", "MS", "MSC", "MBA"):
        return False
    if re.search(r"\bMS\s+Office\b", clause, re.I):
        return True
    if re.search(r",\s*" + re.escape(token) + r"(?:\s+\d{5}(?:-\d{4})?|\s*$)", clause):
        return True
    if re.search(r"\b(?:degree|education)\b", clause, re.I):
        return False
    if re.search(r"\b(?:AA|AS|BA|BS)\s*(?:/|or|and)\s*(?:AA|AS|BA|BS)\b", clause):
        return False
    if re.search(r"\b(?:AA|AS|BA|BS|BSc|MA|MS|MSc|MBA)\s+(?:in|from)\b", clause):
        return False
    if upper in ("BA", "BS", "BSC") and context in ("required", "preferred", "qualification_unspecified"):
        return False
    if upper in ("BA", "BS") and re.search(r"\b(?:BA|BS)\s*(?:/|or|and)\s*(?:BA|BS)\b", clause):
        return False
    return True


def _extract_education(normalized: str, lines: Sequence[Tuple[str, int, str]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for line_index, (line, base, context) in enumerate(lines):
        for level, pattern in _DEGREES:
            flags = re.I
            for match in re.finditer(pattern, line, flags):
                # Short degree abbreviations are candidates only when uppercase in source.
                compact_token = re.sub(r"[.\s]", "", match.group(0))
                if compact_token.lower() in ("ba", "bs", "bsc", "ma", "ms", "msc", "mba", "aa", "as") and not compact_token.isupper():
                    continue
                start, end = base + match.start(), base + match.end()
                abbreviation = compact_token.upper() in ("AA", "AS", "BA", "BS", "BSC", "MA", "MS", "MSC", "MBA")
                clause_left, clause_right = _clause_bounds(line, match.start(), match.end())
                qualification_relation_unresolved = (
                    _qualification_relation_unresolved(line[clause_left:clause_right])
                    or _cross_line_or_path(lines, line_index)
                )
                scope_left, scope_right, scope_rule = _education_scope_bounds(
                    line, match.start(), match.end(), clause_left, clause_right
                )
                local_scope = line[scope_left:scope_right]
                scope_leading = len(local_scope) - len(local_scope.lstrip())
                scope_trailing = len(local_scope) - len(local_scope.rstrip())
                scope_text = local_scope.strip()
                scope_text_start = base + scope_left + scope_leading
                scope_text_end = base + scope_right - scope_trailing
                relative_start = match.start() - scope_left
                relative_end = match.end() - scope_left
                item_context, mixed_scope = _context_for_match(
                    local_scope, relative_start, relative_end, context
                )
                negated = _negated_candidate(local_scope, relative_start, relative_end)
                negated_or_optional = _negated_or_optional(local_scope, relative_start, relative_end)
                alternative_path, alternative_text = _locally_associated_alternative(
                    _EDUCATION_ALTERNATIVE, local_scope, relative_start, relative_end
                )
                equivalent_experience = bool(
                    alternative_path and alternative_text
                    and _EQUIVALENT_EXPERIENCE.search(alternative_text)
                )
                equivalent_credential = bool(_EQUIVALENT_CREDENTIAL.search(local_scope))
                alternative = _clause_text(line, scope_left, scope_right) if alternative_path else None
                if equivalent_experience:
                    equivalence_type = "experience_alternative"
                elif equivalent_credential:
                    equivalence_type = "credential_equivalent"
                else:
                    equivalence_type = "none"
                ambiguous_abbreviation = abbreviation and _ambiguous_degree_abbreviation(
                    match.group(0), local_scope, item_context
                )
                found.append(_evidence(
                    normalized, "education", "education_clause", level,
                    start, end, item_context, degree_level=level,
                    matched_text=match.group(0), equivalent_experience=equivalent_experience,
                    equivalent_credential=equivalent_credential,
                    equivalence_type=equivalence_type,
                    alternative_path_text=alternative,
                    alternative_training_or_experience=alternative_path,
                    alternatives_retained=True,
                    negated=negated,
                    negated_or_optional=negated_or_optional,
                    ambiguous_degree_abbreviation=ambiguous_abbreviation,
                    qualification_relation_unresolved=qualification_relation_unresolved,
                    is_unconditional_education_requirement=not alternative_path and not qualification_relation_unresolved,
                    qualification_scope_text=scope_text,
                    qualification_scope_start=scope_text_start,
                    qualification_scope_end=scope_text_end,
                    qualification_scope_rule=scope_rule,
                    local_path_scope_applied=(scope_left != clause_left or scope_right != clause_right),
                    alternative_scope_local=True,
                    mixed_requirement_scope=mixed_scope,
                    context_conflict=_context_conflict_for_match(local_scope, relative_start, relative_end, context),
                    is_applicant_requirement=item_context in ("required", "preferred") and not negated_or_optional and not ambiguous_abbreviation and not alternative_path and not qualification_relation_unresolved,
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
                        context_conflict=_context_conflict_for_match(line, match.start(), match.end(), context),
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
        "applicant_qualification_candidate_count": sum(bool(x.get("is_applicant_qualification_candidate")) for x in items),
        "qualification_unspecified_candidate_count": sum(
            bool(x.get("is_applicant_qualification_candidate")) and x.get("context") == "qualification_unspecified"
            for x in items
        ),
        "context_conflict_candidate_count": sum(bool(x.get("context_conflict")) for x in items),
        "company_or_benefits_evidence_count": sum(x["context"] in ("company", "benefits") for x in items),
        "policy_or_boilerplate_evidence_count": sum(
            x["context"] in ("company", "benefits", "application_policy", "equal_opportunity") for x in items
        ),
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
        result["explicit_duration_candidate_count"] = sum(bool(x.get("has_explicit_duration")) for x in items)
        result["duration_unspecified_candidate_count"] = sum(x.get("has_explicit_duration") is False for x in items)
        result["alternative_path_candidate_count"] = sum(bool(x.get("alternative_training_or_education")) for x in items)
        result["qualification_relation_unresolved_count"] = sum(bool(x.get("qualification_relation_unresolved")) for x in items)
    elif module == "education":
        result["degree_levels"] = sorted(set(str(x["degree_level"]) for x in items))
        result["has_equivalent_experience_path"] = any(bool(x.get("equivalent_experience")) for x in items)
        result["has_equivalent_credential"] = any(bool(x.get("equivalent_credential")) for x in items)
        result["equivalence_type_counts"] = dict(sorted(
            defaultdict(int, {
                kind: sum(x.get("equivalence_type", "none") == kind for x in items)
                for kind in ("credential_equivalent", "experience_alternative", "none")
            }).items()
        ))
        result["alternative_path_candidate_count"] = sum(bool(x.get("alternative_training_or_experience")) for x in items)
        result["qualification_relation_unresolved_count"] = sum(bool(x.get("qualification_relation_unresolved")) for x in items)
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
        "source_fingerprint_sha256": None,
        "normalized_text_fingerprint_sha256": None,
        "format_flags": {},
        "normalization_flags": {},
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
        normalized, format_flags = _normalize_with_flags(text)
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
            "source_fingerprint_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "normalized_text_fingerprint_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "format_flags": format_flags,
            "normalization_flags": format_flags,
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
