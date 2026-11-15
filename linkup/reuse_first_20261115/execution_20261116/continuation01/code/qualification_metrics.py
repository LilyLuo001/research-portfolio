"""Deterministic conservative field gates; model-reference agreement is not gold accuracy.

Consume only cloud-side, SHA-bound, frozen-validator checked objects. This module
never calls a model or changes acceptance. Exact normalized semantic tuples are a
conservative agreement measure: equivalent free-text paraphrases can disagree.
No fuzzy matching, output-guided synonyms, resampling, or dropped failures.
"""
from collections import Counter
import json

DIMS={
 'experience':('general_work','occupation_task','industry_domain','tool_specific'),
 'entry':('explicit_no_experience','explicit_new_graduate','current_student_internship','explicit_junior_or_entry_label'),
 'responsibility':('independent_judgment','client_ownership','people_supervision','training_mentoring')}
FIELDS=('technology',)+tuple(f'{fam}.{dim}' for fam,dims in DIMS.items() for dim in dims)
SELECTORS={'experience':('experience_clauses','object'),'entry':('entry_items','target'),'responsibility':('responsibility_items','dimension')}
COLUMNS={
 'technology':('technology','family','role','developed_object'),
 'experience':('object','object_detail','strength','conditionality','years_min','years_max','years_relation'),
 'entry':('target','conditionality'),
 'responsibility':('dimension','subject','relation','conditionality')}

def unwrap_validated_carrier(carrier,schema):
 """Known frozen-validator envelope only; no arbitrary schema repair."""
 fields=set(schema['properties']);extra=set(carrier)-fields
 if extra!={'trusted_assignment','evidence_resolution','validation_version'}:
  raise ValueError('not_exact_known_validator_envelope')
 if set(schema.get('required',[]))-set(carrier):raise ValueError('missing_original_review_fields')
 return {k:v for k,v in carrier.items() if k in fields}

def normalize(x):
 if isinstance(x,float) and x.is_integer():return int(x)
 if isinstance(x,str):return ' '.join(x.split())
 if isinstance(x,list):return [normalize(v) for v in x]
 if isinstance(x,dict):return {k:normalize(v) for k,v in x.items()}
 return x

def key(x):return json.dumps(normalize(x),sort_keys=True,ensure_ascii=False,separators=(',',':'))

def alternatives(review,item):
 group=item.get('alternative_group');branch=item.get('alternative_branch')
 if group is None and branch is None:return None
 matches=[g for g in review['qualification_alternatives'] if g['group']==group]
 if len(matches)!=1:raise ValueError('invalid_alternative_group')
 g=matches[0];branches=[b for b in g['branches'] if b['branch']==branch]
 if len(branches)!=1:raise ValueError('invalid_alternative_branch')
 # Canonicalize arbitrary IDs/order, but retain selected branch and all conditions.
 conditions=sorted(key(b['condition']) for b in g['branches'])
 return {'relation':g['relation'],'all_branch_conditions':conditions,'selected_condition':branches[0]['condition']}

def extract(review,field,valid):
 if not valid or review is None or review.get('document_status')!='reviewed_full':return 'unknown',set(),False
 family,*dimension=field.split('.')
 if family=='technology':
  outcome={'explicit_mentions_recorded':'present','not_mentioned_after_full_review':'not_mentioned','unknown':'unknown'}[review['technology_inventory_status']]
  items=review['technology_items']
 else:
  dim=dimension[0];outcome=review[family+'_outcomes'][dim];name,selector=SELECTORS[family];items=[x for x in review[name] if x[selector]==dim]
 tuples=set();resolved=True
 for item in items:
  semantic={c:item[c] for c in COLUMNS[family]}
  if family=='experience':semantic['alternative']=alternatives(review,item)
  # Enum-level unresolved relations cannot silently become known reference labels.
  if any(v=='unresolved' for v in semantic.values() if isinstance(v,str)):resolved=False
  if family=='experience' and semantic['alternative'] and semantic['alternative']['relation']=='unresolved':resolved=False
  tuples.add(key(semantic))
 return outcome,tuples,resolved

def rates(tp,fp,fn):
 return {'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,'tp':tp,'fp':fp,'fn':fn}

def evaluate(cases,gate):
 """All predeclared heldout cases, including missing/invalid/protected outcomes.

Cases: case/split/reference/reference_valid/candidate/candidate_valid. External
runner must verify immutable frame SHA, complete 500-case accounting, independent
references, source identity, quote checks and exclusion policy before calling.
 """
 assert len({c['case'] for c in cases})==len(cases),'duplicate_case'
 assert all(c['split'] in ('heldout','development') for c in cases)
 held=[c for c in cases if c['split']=='heldout'];assert held,'empty_heldout'
 output={}
 for field in FIELDS:
  cm=Counter();support=Counter();rel=Counter();relation_known=0;candidate_known=0;unknown=0;reference_ambiguous=0
  for c in held:
   ro,rt,rr=extract(c.get('reference'),field,c.get('reference_valid',False));co,ct,cr=extract(c.get('candidate'),field,c.get('candidate_valid',False))
   candidate_known+=co!='unknown'
   if ro=='unknown':unknown+=1;continue
   support[ro]+=1;cm[ro,co]+=1
   if not rr:reference_ambiguous+=1;continue
   relation_known+=1
   if co=='unknown' or not cr:ct=set()
   rel['tp']+=len(rt&ct);rel['fp']+=len(ct-rt);rel['fn']+=len(rt-ct)
  classes={label:rates(cm[label,label],sum(n for (r,p),n in cm.items() if p==label and r!=label),sum(n for (r,p),n in cm.items() if r==label and p!=label)) for label in ('present','not_mentioned')}
  macro=sum(x['f1'] or 0 for x in classes.values())/2;outcome=classes['present'];relation=rates(rel['tp'],rel['fp'],rel['fn'])
  known=sum(support.values());reasons=[]
  if known/len(held)<gate['known_reference_coverage_min']:reasons.append('reference_coverage_below_gate')
  if known<gate['minimum_known_cases_per_field']:reasons.append('insufficient_known_cases')
  if support['present']<gate['minimum_positive_cases_per_field']:reasons.append('insufficient_positive_cases')
  if support['not_mentioned']<gate['minimum_negative_cases_per_field']:reasons.append('insufficient_negative_cases')
  for name,minimum in [('precision','precision_min'),('recall','recall_min')]:
   if outcome[name] is None or outcome[name]<gate[minimum]:reasons.append('outcome_'+name+'_below_gate')
  if macro<gate['macro_f1_min']:reasons.append('outcome_macro_f1_below_gate')
  if relation_known/len(held)<gate['known_reference_coverage_min']:reasons.append('resolved_relation_coverage_below_gate')
  for name,minimum in [('precision','precision_min'),('recall','recall_min'),('f1','macro_f1_min')]:
   if relation[name] is None or relation[name]<gate[minimum]:reasons.append('complete_relation_'+name+'_below_gate')
  output[field]={'heldout_cases':len(held),'known_reference_cases':known,'unknown_reference_cases':unknown,'reference_relation_ambiguous_cases':reference_ambiguous,'resolved_relation_cases':relation_known,'candidate_known_cases_all':candidate_known,'support':dict(support),'confusion_matrix':[{'reference':r,'candidate':p,'n':n} for (r,p),n in sorted(cm.items())],'positive_outcome':outcome,'class_metrics':classes,'outcome_macro_f1':macro,'complete_relation':relation,'machine_reference_field_gate_pass':not reasons,'blocking_reasons':reasons}
 return {'fields':output,'heldout_cases':len(held),'development_cases_excluded_from_gate':len(cases)-len(held),'measurement':'conservative_exact_normalized_complete_tuple_machine_reference_agreement','machine_agreement_is_not_gold_accuracy':True,'population_generalization_certified':False,'production_admission':False,'production_requires_external_complete_protocol_and_nonduplicate_queue':True}
