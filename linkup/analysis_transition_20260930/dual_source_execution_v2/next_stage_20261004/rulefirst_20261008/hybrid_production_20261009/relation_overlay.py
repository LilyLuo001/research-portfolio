"""Bounded root-authored relation annotations over frozen evidence; no API.

Annotations are pattern-specific candidates, NOT gold semantic labels. Original
v1.2 evidence remains unchanged. Offsets refer to its normalized Unicode source.
"""
import hashlib
import re
import hashlib
VERSION = 'relation-overlay-20261009-v1'

def rx(s): return re.compile(s, re.I)
def heading_key(s): return re.sub(r'[^a-z0-9 ]', '', s.lower()).strip()
HEADINGS = {
 'minimum qualifications':'required', 'required qualifications':'required',
 'minimum requirements':'required','what you will need':'required',
 'preferred qualifications':'preferred','preferred requirements':'preferred',
 'what would be nice to have':'preferred',
 'responsibilities':'duties','what you will do':'duties',
 'work youll do':'duties','what you get to do every day':'duties',
 'how you will make a difference':'duties',
 'benefits':'background','what we offer':'background',
 'compensation benefits  perks':'background','professional development':'background',
 'our people and culture':'background','our purpose':'background',
 'equal opportunity':'background','recruiting tips':'background',
 'wages  salary':'background','annual salary range':'background',
 'about the job':'job_summary','about the role':'job_summary',
 'about guidehouse':'background'
}
HEADINGS = {' '.join(k.split()):v for k,v in HEADINGS.items()}
PREF = rx(r'\b(?:preferred|preferably|desired|desirable|nice to have|a plus)\b')
REQ = rx(r'\b(?:required|requires?|must|mandatory|at least|minimum)\b')
NEG = rx(r'\b(?:no|not|never|without|neither)\b')
MENTOR_JUNIOR = rx(r'\b(?:mentor|mentoring|coach|coaching|train|training|guide|guidance|support)\b[^.!?;]{0,100}\bjunior\s+(?:engineers?|staff|employees?|colleagues?|developers?|analysts?|team members?)\b')
USE_BRIDGE = rx(r'\b(?:using|utilizing|via|with the use of)\s+(?:the\s+)?(?:[\w+.#-]+\s*(?:,|and|or|/)\s*)*$')
NEGATION_TAIL = rx(r'\b(?:no|not|never|without)\s+(?:\w+\s+){0,3}$')
DEGREE_ALT = rx(r'\b(?:bachelor(?:s|[\x27’]s)? degree|master(?:s|[\x27’]s)? degree|degree|diploma)\s+or\s+(?:an?\s+)?equivalent\s+(?:practical\s+|work\s+|professional\s+)?experience\b')
OTHER_PERSON = rx(r'\b(?:mentor|mentoring|coach|coaching|provide guidance|provide support)\b[^.!?;]{0,100}\b(?:junior|employees|staff|team|engineers|colleagues)\b')
TRAIN_RECEIVE = rx(r'\b(?:you (?:will|can) receive|you will be provided with|we (?:will )?provide (?:you with|new hires with)|training (?:will be|is) provided to (?:you|new hires))\b[^.!?;]{0,120}')

def physical_headings(text):
    out=[];offset=0
    for line in text.splitlines(True):
        stripped=line.strip();key=' '.join(heading_key(stripped).split())
        if key in HEADINGS:
            start=offset+len(line)-len(line.lstrip())
            out.append({'start':start,'end':start+len(stripped),'quote':stripped,'scope':HEADINGS[key]})
        offset+=len(line)
    return out

def apply(result):
    text=result.get('normalized_text','')
    if not isinstance(text,str) or hashlib.sha256(text.encode()).hexdigest()!=result.get('normalized_text_sha256'):
        raise ValueError('frozen normalized text SHA mismatch')
    heads=physical_headings(text);out=[]
    for i,e in enumerate(result.get('evidence',[])):
        s=e['quote'];a=e['start'];b=e['end']
        if (not isinstance(a,int) or not isinstance(b,int)
                or not (0<=a<=b<=len(text)) or text[a:b]!=s):
            raise ValueError('frozen evidence span mismatch')
        previous=[h for h in heads if h['start']<a]
        h=previous[-1] if previous else None
        # Heading scope is reported as a candidate: an unrecognized intervening
        # heading cannot be excluded by this bounded vocabulary.
        scope=h['scope'] if h else 'unknown'
        item={'evidence_index':i,'start':a,'end':b,'kind':e['kind'],
              'annotations':[], 'candidate_heading':h,
              'heading_scope_status':('recognized_preceding_heading_not_exhaustive'
                                      if h else 'no_recognized_preceding_heading')}
        def add(rule,**fields):item['annotations'].append(dict(rule=rule,**fields))
        if scope=='background':add('preceding_background_heading',interpretation='Do not count as applicant requirement/duty without further evidence')
        if e['kind']=='experience':
            p=bool(PREF.search(s));r=bool(REQ.search(s))
            if p and r:strength='mixed_unresolved'
            elif p:strength='preferred_candidate'
            elif r:strength='required_candidate'
            elif scope in ('required','preferred'):strength=scope+'_heading_candidate'
            else:strength='unspecified'
            add('experience_strength_components',strength=strength,scope='local_clause_only',original_strength=e.get('strength'))
            if DEGREE_ALT.search(s):
                add('explicit_degree_or_equivalent_experience',relation='OR',experience_years='not_inferred',other_experience_clauses='remain_separate_constraints')
            if PREF.search(s) and rx(r'\b(?:work|professional|total|overall) experience\b').search(s):
                add('general_and_preference_may_have_different_scope',status='needs_relation_review',action='Do not assign the whole clause one preferred/required label')
        if e['kind']=='entry' and e.get('rule')=='entry_junior_text_mention':
            if MENTOR_JUNIOR.search(s):
                add('junior_refers_to_people_assisted',entry_eligibility='not_established_by_this_phrase',mentoring_responsibility='candidate' if scope!='background' and not NEG.search(s) else 'unresolved')
            else:add('junior_mention_without_applicant_binding',entry_eligibility='unresolved')
        if e['kind']=='technology':
            term=e.get('term','');occ=list(re.finditer(re.escape(term),s,re.I)) if term else []
            # Multiple repeated mentions cannot be matched to this frozen term
            # instance because v1.2 stores clause offsets, not mention offsets.
            if len(occ)==1:
                before=s[:occ[0].start()];m=USE_BRIDGE.search(before)
                if m and not NEGATION_TAIL.search(before[:m.start()]) and not e.get('negated'):
                    add('explicit_using_named_tool',relationship='use_of_named_tool',role_status='candidate',not_inferred='development_of_named_tool',context_status='background_only' if scope=='background' else 'requires_applicant_or_duty_binding')
        if OTHER_PERSON.search(s):
            add('mentoring_other_people',status='background_only' if scope=='background' else 'candidate_responsibility',not_inferred='employer_trains_applicant')
        if TRAIN_RECEIVE.search(s):add('explicit_training_for_applicant',status='candidate_training_offer',not_inferred='applicant_trains_others')
        if item['annotations']:out.append(item)
    return {'version':VERSION,'source_text_sha256':result.get('source_text_sha256'),
            'normalized_text_sha256':result.get('normalized_text_sha256'),'annotations':out,
            'interpretation':'Bounded deterministic relation candidates; no new semantic gold, no historical text inference, no no-hit-as-absence.'}
