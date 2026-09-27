import json,hashlib,sys
from pathlib import Path
from collections import defaultdict
import pyarrow.parquet as pq
B=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(B/'stage_c_v4'))
from requirement_candidates import _normalize as normalize_text
SEED='linkup-frozen-v4-blind-20260927-v1'
def rank(s):return hashlib.sha256((SEED+'\0'+s).encode()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')
def main():
 out=Path(__file__).parent/'blind_pack'
 if out.exists():raise RuntimeError('Immutable blind pack already exists')
 rows=pq.read_table(B/'reports/stage_c_pilot_review/sample_ads.parquet').to_pylist()
 usa=[r for r in rows if r['COUNTRY']=='USA']
 known=set(json.loads((B/'stage_c_v3/validation_pack/known_development_exclusions.json').read_text())['excluded_usa_hashes'])
 reviewed=json.loads((B/'stage_c_v4/development_exclusions_v4.json').read_text())['newly_used_JOB_HASH']
 known.update(reviewed)
 oldpack={r['JOB_HASH'] for r in pq.read_table(B/'stage_c_v3/validation_pack/validation_sample.parquet',columns=['JOB_HASH']).to_pylist()}
 excluded=known|oldpack
 fingerprints={r['JOB_HASH']:hashlib.sha256(normalize_text(r['DESCRIPTION']).encode()).hexdigest() for r in usa}
 excluded_templates={fingerprints[k] for k in excluded if k in fingerprints}
 known_employers={str(r['RECORD_COMPANY_ID']) for r in usa if r['JOB_HASH'] in known and r['RECORD_COMPANY_ID'] is not None}
 eligible=[r for r in usa if r['JOB_HASH'] not in excluded and fingerprints[r['JOB_HASH']] not in excluded_templates and str(r['RECORD_COMPANY_ID']) not in known_employers]
 groups=defaultdict(list)
 for r in eligible:groups[fingerprints[r['JOB_HASH']]].append(r)
 reps=[min(v,key=lambda r:rank('representative:'+r['JOB_HASH'])) for v in groups.values()]
 strata=defaultdict(list)
 for r in reps:strata[r['COHORT']].append(r)
 selected=[];frame={}
 for cohort,rr in sorted(strata.items()):
  assert len(rr)>=4,(cohort,len(rr))
  chosen=sorted(rr,key=lambda r:rank('selection:'+fingerprints[r['JOB_HASH']]))[:4]
  frame[cohort]={'eligible_templates':len(rr),'sampled_templates':len(chosen),'conditional_probability':len(chosen)/len(rr)}
  for r in chosen:selected.append(dict(r,NORMALIZED_SHA256=fingerprints[r['JOB_HASH']],CONDITIONAL_PROBABILITY=len(chosen)/len(rr)))
 assert len(selected)==24
 out.mkdir();(out/'texts').mkdir()
 for i,r in enumerate(selected,1):
  r['BLIND_ID']='B%02d'%i
  (out/'texts'/(r['BLIND_ID']+'.txt')).write_text(r['DESCRIPTION'])
 write(out/'ads.json',[{'BLIND_ID':r['BLIND_ID'],'DESCRIPTION':r['DESCRIPTION']} for r in selected])
 write(out/'metadata_private.json',[{k:v for k,v in r.items() if k!='DESCRIPTION'} for r in selected])
 write(out/'selection_report.json',{'seed':SEED,'source':'existing Kunshan 64-shard pilot; not full-corpus/national sample','USA_source_rows':len(usa),'eligible_ads':len(eligible),'eligible_templates':len(reps),'selected':len(selected),'frame':frame,'excluded_known_hashes':sorted(known),'excluded_prior_pack_hashes':sorted(oldpack),'known_employers_excluded':len(known_employers),'parser_predictions_used_for_selection':False,'independence':'Excludes recorded prior cases, the entire prior120 pack, exact normalized templates, and known development-case employers. Unrecorded inspection cannot be ruled out.','parser_sha256':hashlib.sha256((B/'stage_c_v4/requirement_candidates.py').read_bytes()).hexdigest(),'ads_sha256':hashlib.sha256((out/'ads.json').read_bytes()).hexdigest()})
 print(json.dumps({'selected':24,'eligible_ads':len(eligible),'eligible_templates':len(reps),'frame':frame}))
if __name__=='__main__':main()
