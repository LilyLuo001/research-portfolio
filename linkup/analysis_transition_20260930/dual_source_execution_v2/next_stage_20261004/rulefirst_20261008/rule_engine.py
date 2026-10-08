"""Root-authored bounded rule-first measurements, not latent seniority labels.

Only frozen V5 HTML normalization and heading segmentation are reused. All
evidence coordinates refer to retained normalized_text, NOT raw HTML. Source
SHA and normalization version make the original recoverable. No LLM calls.
"""
import hashlib
import re
import legacy_v5_frozen as legacy

VERSION = 'rulefirst-20261008-v1.2'
OBJECTS = ('general_work', 'occupation_task', 'industry_domain', 'tool')
EXCLUDED = {'company', 'benefits', 'equal_opportunity', 'application_policy'}

def rx(s): return re.compile(s, re.I)

# Extend heading vocabulary without altering the frozen normalizer file.
legacy._HEADING_RULES = (('required', rx(r'^must[- ]haves?\s*:?$')),) + legacy._HEADING_RULES
legacy._INLINE_HEADING_RULES = (('required', r'must[- ]haves?'),) + legacy._INLINE_HEADING_RULES

# Project vocabulary; presence is NOT technology adoption or causal exposure.
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
NEG = rx(r'\b(?:no|not|never|without|not required to)\s+(?:\w+\s+){0,3}$')
TASKS = {
 'execution_assistance': rx(r'\b(?:assist(?:s|ing)?|support(?:s|ing)?)\s+(?:the |a |an |our |with )?(?:manager|team|senior|supervisor|account manager|daily|routine)\b|\b(?:data entry|routine processing|follow established procedures)\b'),
 'people_supervision': rx(r'\b(?:supervise|supervising|manage|managing|lead|leading)\s+(?:a |the |our )?(?:team|staff|employees|personnel|direct reports)\b|\b(?:hire|evaluate)\s+(?:and \w+\s+)?(?:staff|employees)\b'),
 'independent_responsibility': rx(r'\b(?:exercise (?:independent|professional) judgment|independent decision[- ]making|make independent decisions|work independently|independently (?:manage|lead|decide|design)|own (?:the |a )?(?:budget|project|product|strategy))\b'),
 'client_ownership': rx(r'\b(?:manage|own|lead)\s+(?:the |a |key |strategic )?(?:client|customer)\s+(?:relationships?|accounts?|portfolio)|\bprimary point of contact\s+for\s+(?:the |our )?(?:clients?|customers?)\b'),
 'client_contact_only': rx(r'\b(?:interact|communicate|liaise) with (?:clients?|customers?)\b|\b(?:answer|respond to)\s+(?:customer|client)\s+(?:calls|queries|inquiries)\b'),
}

def _number(s): return float(NUMWORDS[s.lower()]) if s.lower() in NUMWORDS else float(s)

def duration(m):
    lo,hi=_number(m['lo']),_number(m['hi']) if m['hi'] else None
    prefix=(m['prefix'] or '').lower()
    unit=m['unit'].lower()
    kind='stated_unspecified'
    if hi is not None: kind='range'
    elif prefix in ('up to','at most','no more than','maximum of'): kind='maximum'; hi,lo=lo,None
    elif prefix=='exactly': kind='exact'
    elif prefix in ('at least','a minimum of','minimum of','minimum','more than','over') or m['plus']: kind='minimum'
    factor=1/12 if unit.startswith('month') else 1
    return {'kind':kind,'lower_years':lo*factor if lo is not None else None,'upper_years':hi*factor if hi is not None else None,'strict_lower':prefix in ('more than','over'),'original_unit':unit}

def clauses(text):
    for line,base,section in legacy._line_records(text):
        # Preserve exact character coordinates; no paraphrasing or fuzzy repair.
        last=0
        for split in re.finditer(r';\s*|(?<=[.!?])\s+(?=[A-Z])',line):
            piece=line[last:split.start()]
            if piece.strip():
                lead=len(piece)-len(piece.lstrip()); yield piece.strip(),base+last+lead,section
            last=split.end()
        piece=line[last:]
        if piece.strip():
            lead=len(piece)-len(piece.lstrip()); yield piece.strip(),base+last+lead,section

def _strength(s,section):
    pref,req=bool(PREFERRED.search(s)),bool(REQUIRED.search(s))
    if pref and req: return 'mixed'
    if pref: return 'preferred'
    if req: return 'required'
    return section if section in ('required','preferred') else 'unspecified'

def _scope(s):
    if DEGREE.search(s) and rx(r'\bor\b|in lieu of|instead of|substitut|equivalent combination').search(s): return 'education_alternative'
    if rx(r'\b(?:either|unless|depending on|alternatively)\b|\bif you\b').search(s): return 'other_conditional'
    return 'unconditional_explicit_clause'

def _objects(s):
    result=[]
    for k,p in [('tool',TOOL),('industry_domain',DOMAIN),('occupation_task',TASK)]:
        if p.search(s): result.append(k)
    # General is explicit unrestricted experience; not the default for bare years.
    general=GENERAL.search(s)
    if not result and general:
        # An unfamiliar specialty after 'professional experience' is unresolved,
        # not unrestricted general experience. Explicitly restrict the tail.
        tail=s[general.end():].strip(' .,:;')
        if not tail or rx(r'^(?:is |are )?(?:required|preferred|desired|necessary|mandatory)(?:\s|[.!?]|$)').search(tail):
            result=['general_work']
    return result

def extract(text):
    if not isinstance(text,str) or not text.strip():
        return {'version':VERSION,'status':'invalid_text','evidence':[],'flags':{},'review_reasons':['empty_or_nonstring_text']}
    normalized,normflags=legacy._normalize_with_flags(text)
    evidence=[]; reasons=set(); flags={}; excluded=0; n_exp=0
    # One development correction: alternatives may span several bullet lines.
    # Do not pretend to resolve their branches by assigning every stated year
    # amount to every applicant. Retain all evidence with a conservative flag.
    multiline_alternative = any(
        DEGREE.search(normalized[max(0,m.start()-1400):m.end()+1400])
        and YEARS.search(normalized[max(0,m.start()-1400):m.end()+1400])
        for m in re.finditer(r'(?im)^\s*(?:[-*]\s*)?OR\s*$', normalized))
    if multiline_alternative:
        reasons.add('multiline_qualification_alternative')
        flags['multiline_qualification_alternative']=True
    # Government recruitment exports sometimes append the entire application
    # questionnaire, including all answer choices. Those are not requirements.
    questionnaire = rx(r'\bWhich of the following (?:best )?describes\b|\bHow would you rate your\b').search(normalized)
    questionnaire_start = questionnaire.start() if questionnaire else len(normalized)+1
    if questionnaire:
        flags['application_questionnaire_tail_excluded']=True
    def add(kind,rule,s,start,section,**extra):
        assert normalized[start:start+len(s)]==s
        item={'kind':kind,'rule':rule,'quote':s,'start':start,'end':start+len(s),'section':section}
        item.update(extra); evidence.append(item); return item
    for s,start,section in clauses(normalized):
        exps=list(EXP.finditer(s)); years=list(YEARS.finditer(s))
        if start+len(s)>questionnaire_start:
            excluded+=1
            continue
        if section in EXCLUDED:
            if exps or any(p.search(s) for p in TECH.values()): excluded+=1
            continue
        strength=_strength(s,section); scope=_scope(s)
        ne=NOEXP.search(s)
        if ne:
            waiver_objects=_objects(ne.group(0)) or ['general_work']
            add('entry','explicit_no_experience',s,start,section,strength='explicit_waiver',scope=scope,objects=waiver_objects)
            flags['explicit_experience_waiver']=True
            # No Python experience is not an unrestricted entrance invitation.
            if waiver_objects==['general_work']: flags['explicit_no_experience']=True
        if NEWGRAD.search(s):
            if rx(r'\b(?:not|no)\s+(?:open to |for )?(?:new|recent|fresh) graduates?\b').search(s):
                reasons.add('negated_graduate_language')
            else:
                add('entry','graduate_targeting_language',s,start,section)
                flags['graduate_language']=True
        if ENTRY.search(s):
            add('entry','entry_junior_text_mention',s,start,section)
            flags['entry_junior_text']=True
        for tech,p in TECH.items():
            for match in p.finditer(s):
                before=s[max(0,match.start()-90):match.start()]
                negated=bool(NEG.search(before))
                role='mention_only'
                if rx(r'\b(?:develop|build|train|fine[- ]tune|design)(?:ing|s)?\b').search(before): role='development_cue'
                elif rx(r'\b(?:deploy|implement|integrate)(?:ing|s)?\b').search(before): role='implementation_cue'
                elif rx(r'\b(?:use|using|utilize|utilizing|apply|applying|leverage|leveraging)\b').search(before): role='use_cue'
                add('technology','lexical_'+tech,s,start,section,technology=tech,term=match.group(0),role_cue=role,negated=negated)
                if not negated: flags['tech_'+tech]=True
        if DEGREE.search(s):
            add('education','degree_phrase',s,start,section,strength=strength,scope=scope)
            flags['education_phrase']=True
            if scope=='education_alternative': flags['education_experience_alternative']=bool(exps)
        if exps and not ne:
            # Customer/user experience and company history are not work history.
            product=rx(r'\b(?:customer|user|shopping|guest|digital|dining) experience\b').search(s)
            company=rx(r'\b(?:we have|our company has|our firm has|we bring)\b|\b(?:years of age|years old|since \d{4})\b').search(s)
            if product and not (years or rx(r'\bexperience (?:in|with|as|of)\b').search(s)):
                excluded+=1; continue
            if company: excluded+=1; continue
            n_exp+=1
            objects=_objects(s)
            issues=[]
            assertion = (bool(years) or section in ('required','preferred','qualification_unspecified')
                or bool(rx(r'\bexperience\s+(?:in|with|as|of|using|working|leading|building|developing|guiding|providing)\b|\b(?:prior|previous|proven|professional|relevant|related|hands[- ]on|work|practical|technical|industry)\s+experience\b|\b(?:you|candidate|applicant|require|requires|required|preferred)\b').search(s)))
            if not assertion: issues.append('experience_assertion_unresolved')
            if not objects: issues.append('experience_object_unresolved')
            if len(objects)>1: issues.append('multiple_experience_objects')
            if len(exps)>1 or len(years)>1: issues.append('multiple_experience_or_duration_clauses')
            if strength=='mixed': issues.append('mixed_required_preferred')
            if scope!='unconditional_explicit_clause': issues.append('conditional_qualification')
            if multiline_alternative:
                issues.append('multiline_qualification_alternative')
                scope='document_multiline_alternative_unresolved'
            if rx(r'\b(?:for each|per year|per academic|equivalent to|credited as)\b').search(s): issues.append('duration_equivalence_or_ratio')
            if rx(r'\b(?:no|not|without)\b').search(s): issues.append('negation_requires_scope')
            bound=duration(years[0]) if len(years)==1 and len(exps)==1 and 'duration_equivalence_or_ratio' not in issues else None
            # An explicit span alone can be classified; it is not automatically required.
            status='explicit_rule_candidate' if not issues else 'needs_review'
            add('experience','experience_clause',s,start,section,objects=objects,strength=strength,scope=scope,duration=bound,outcome_status=status,review_reasons=issues)
            for issue in issues: reasons.add(issue)
            flags['experience_clause']=True
            if status=='explicit_rule_candidate':
                for obj in objects:
                    flags['experience_'+obj]=True
                    if strength=='required': flags['required_experience_'+obj]=True
            if bound: flags['explicit_experience_years']=True
        elif KNOW.search(s):
            add('knowledge','knowledge_not_prior_experience',s,start,section,objects=_objects(s),strength=strength)
            flags['knowledge_phrase']=True
        for family,p in TASKS.items():
            for match in p.finditer(s):
                # Past experience in management is not a promise of supervisory duties.
                if exps or section in ('required','preferred','qualification_unspecified'): continue
                before=s[:match.start()]
                if NEG.search(before) or rx(r'\b(?:assist|support|help)\b').search(before[-55:]) and family!='execution_assistance':
                    reasons.add('task_scope_ambiguous'); continue
                add('task','explicit_'+family,s,start,section,task_family=family)
                flags['task_'+family]=True
    if not normalized.strip(): reasons.add('empty_visible_text')
    if n_exp==0 and EXP.search(normalized) and not flags.get('explicit_no_experience'):
        reasons.add('experience_words_outside_classified_clauses')
    if flags.get('graduate_language') or flags.get('entry_junior_text') or flags.get('explicit_no_experience'):
        flags['entry_and_experience_cooccurrence']=bool(flags.get('experience_clause'))
        # Co-occurrence is not automatically a contradiction or an entry-level classification.
    return {'version':VERSION,'status':'processed','source_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'normalized_text_sha256':hashlib.sha256(normalized.encode()).hexdigest(),'normalized_text':normalized,'normalization':'frozen_v5_visible_text','normalization_flags':normflags,'coordinate_system':'normalized_unicode_codepoints','evidence':evidence,'flags':flags,'review_reasons':sorted(reasons),'excluded_context_clause_count':excluded,'experience_status':'needs_review' if reasons else ('explicit_rule_candidate' if n_exp else 'no_explicit_rule_match'),'interpretation':'Flags indicate rule-observed language, not validated absence, latent seniority, adoption, or causal effects.'}
