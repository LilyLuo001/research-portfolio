#!/usr/bin/env python3
import collections, datetime as dt, hashlib, json, os
from pathlib import Path
ROOT=Path('/projectnb/econdept/qluo/linkup_rulefirst_20261008')
def load(p):
    with open(p,encoding='utf-8') as f:return [json.loads(x) for x in f if x.strip()]
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
unique=load(ROOT/'run/full/FULL7635_RULE_OUTPUTS_PRIVATE.jsonl')
represented=load(ROOT/'imported/production_standard_20261008/private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl')
if len(unique)!=7635 or len(represented)!=10000:raise SystemExit('frozen counts changed')
bysha={x['exact_text_sha256']:x for x in unique}
counts=collections.Counter(); review_clauses=review_chars=all_exp_clauses=0
for u in unique:
    if u.get('status')!='complete':continue
    ev=[x for x in u['result'].get('evidence',[]) if x.get('kind')=='experience']; all_exp_clauses+=len(ev)
    for x in ev:
        if x.get('outcome_status')=='needs_review':
            review_clauses+=1; review_chars+=len(x.get('quote',''))
for m in represented:
    arm=m['arm']; counts[(arm,'denominator')]+=1
    u=bysha[m['exact_text_sha256']]
    if u.get('status')!='complete':counts[(arm,'processing_error')]+=1;continue
    r=u['result']; ev=[x for x in r.get('evidence',[]) if x.get('kind')=='experience']
    if r.get('review_reasons') or any(x.get('outcome_status')=='needs_review' for x in ev):counts[(arm,'document_any_review')]+=1
    if any(x.get('duration') is not None for x in ev):counts[(arm,'document_any_explicit_numeric_experience')]+=1
    clear=[x for x in ev if x.get('duration') is not None and x.get('outcome_status')=='explicit_rule_candidate']
    if clear:counts[(arm,'document_at_least_one_clear_numeric_clause')]+=1
    if any(x.get('strength')=='required' for x in clear):counts[(arm,'document_required_clear_numeric_clause')]+=1
summary={'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'job_id':os.environ.get('JOB_ID'),'source':'existing frozen v1.2 full outputs; no re-extraction','represented_sample_counts':{a:{k:counts[(a,k)] for k in ('denominator','processing_error','document_any_review','document_any_explicit_numeric_experience','document_at_least_one_clear_numeric_clause','document_required_clear_numeric_clause')} for a in 'ABC'},'unique7635_experience_clause_workload':{'all_experience_clauses':all_exp_clauses,'needs_review_clauses':review_clauses,'needs_review_quote_characters':review_chars,'boundary':'Characters are exact rule-evidence quote lengths, not measured tokens or a model budget guarantee.'},'interpretation':'Diagnostic workload counts only. Review status does not invalidate every field in a document; flag omission is not validated absence.'}
public=ROOT/'run/full/POSTRUN_DIAGNOSTIC_PUBLIC.json';public.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
ret=ROOT/'return';ret.mkdir(exist_ok=True,mode=0o700)
files=[]
for base in ('code','control','imported','logs','run'):
    for p in sorted((ROOT/base).rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
manifest=ret/'BU_RETURN_MANIFEST_PRIVATE.json';manifest.write_text(json.dumps({'root':str(ROOT),'files':files},indent=2,sort_keys=True)+'\n');os.chmod(manifest,0o600)
receipt={'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'ready_for_transport_no_cleanup_authorized','job_id':os.environ.get('JOB_ID'),'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'manifest_sha256':sha(manifest),'diagnostic_public_sha256':sha(public)}
(ret/'RETURN_READY_PUBLIC.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
