"""Pinned vocabulary derived from rulefirst-v1.2 and its frozen V5 base.

Assignments are copied verbatim; source hashes live in REUSE_MANIFEST.json.
No extraction, normalization, or semantic flags from the old engine are run.
"""
import re
from typing import Sequence, Tuple

def rx(s):
    return re.compile(s, re.I)


VERSION = 'rulefirst-20261008-v1.2'

OBJECTS = ('general_work', 'occupation_task', 'industry_domain', 'tool')

EXCLUDED = {'company', 'benefits', 'equal_opportunity', 'application_policy'}

TECH = {
 'genai': rx(r'\b(?:generative AI|generative artificial intelligence|large language models?|LLMs?|ChatGPT|GPT[- ]?[345]|Claude|prompt engineering|retrieval[- ]augmented generation)\b'),
 'predictive_ai': rx(r'\b(?:machine learning|deep learning|neural networks?|natural language processing|computer vision)\b'),
 'ai_unspecified': rx(r'\b(?:artificial intelligence|AI)\b'),
 'software': rx(r'\b(?:Python|Java(?:Script)?|SQL|Excel|Microsoft Office|SAP|Salesforce|Tableau|Power BI|MATLAB|SAS|ERP|CRM|AutoCAD|QuickBooks|C\+\+|C#|software|database systems?)\b'),
}

TOOL = rx(r'\b(?:Python|Java(?:Script)?|SQL|Excel|Microsoft Office|SAP|Salesforce|Tableau|Power BI|MATLAB|SAS|ERP|CRM|AutoCAD|QuickBooks|ChatGPT|GPT[- ]?[345]|LLMs?|large language models?|AI tools?|software tools?|software packages?)\b')

DOMAIN = rx(r'\b(?:healthcare|health care|hospitals?|banking|insurance|pharmaceutical|biotech(?:nology)?|retail|hospitality|restaurants?|construction industry|manufacturing industry|financial services|telecommunications|automotive industry|aerospace|real estate|oil and gas|government sector|public sector|IT services industry|software industr(?:y|ies)|industry|sector|client population)\b')

TASK = rx(r'\b(?:accounting|nursing|engineering|programming|coding|software development|development|sales|marketing|management|managing|supervis(?:ing|ory|ion)|teaching|research|analysis|analytical|design(?:ing)?|customer service|project management|operations|auditing|consulting|recruiting|relevant|related|similar role|job[- ]related)\b|\bexperience\s+(?:as an? |(?:in |with )?(?:performing|building|developing|designing|leading|managing)\b)')

GENERAL = rx(r'\b(?:total|overall|general|professional|work|working|employment)\s+experience\b')

EXP = rx(r'\bexperience\b')

KNOW = rx(r'\b(?:knowledge|familiarity|proficien(?:cy|t)|understanding)\b')

DEGREE = rx(r"\b(?:bachelor(?:['’]s)?|master(?:['’]s)?|doctorate|Ph\.?D\.?|degree|diploma|GED|high school)\b")

NUMBER = r'(?:\d{1,2}(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)'

YEARS = rx(r'\b(?:(?P<prefix>at least|a minimum of|minimum of|minimum|more than|over|up to|at most|no more than|maximum of|exactly)\s+)?(?P<lo>'+NUMBER+r')(?:\s*\(\d+\))?(?:\s*(?:-|–|—|to)\s*(?P<hi>'+NUMBER+r'))?\s*(?P<plus>\+|or more)?\s*(?P<unit>years?|yrs?|months?)\b')

NUMWORDS = dict(zip('zero one two three four five six seven eight nine ten eleven twelve'.split(),range(13)))

NUMWORDS.update(fifteen=15,twenty=20)

PREFERRED = rx(r'\b(?:preferred|preferably|desired|desirable|nice to have|a plus)\b')

REQUIRED = rx(r'\b(?:required|requires?|must|mandatory|minimum qualifications?|at least)\b')

NOEXP = rx(r'\b(?:no (?:(?:[\w+-]+)\s+){0,5}experience (?:is )?(?:required|necessary|needed)|experience(?: (?:in|with) (?:[\w+-]+\s+){1,4})? (?:is )?not (?:required|necessary|needed))\b')

NEWGRAD = rx(r'\b(?:new|recent|fresh) (?:college |university )?graduates?\b|\bgraduates? (?:are )?(?:welcome|encouraged to apply)\b')

ENTRY = rx(r'\b(?:entry[- ]level|junior)\b')

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
