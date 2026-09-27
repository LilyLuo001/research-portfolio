import collections, hashlib, json, re
from pathlib import Path
import pyarrow.parquet as pq
B=Path(__file__).parent
ads=pq.read_table(B/'sample_ads.parquet').to_pylist()
features=pq.read_table(B/'candidate_pilot/candidate_features.parquet').to_pylist()
by={r['JOB_HASH']:r for r in ads}
assert len(ads)==len(features)==len(by)==2926
parsed={r['JOB_HASH']:json.loads(r['CANDIDATE_JSON']) for r in features}
assert set(parsed)==set(by)
modules=['software','experience','education','tasks','ai']
summary={'input_ads':len(ads),'join_one_to_one':True,'unweighted_sample_only':True,'groups':{},'examples':[]}
for country in ['USA','nonUSA','unknown']:
 rows=[r for r in ads if r['COUNTRY_GROUP']==country]
 def stats(rows):
  return {'n':len(rows),'literal_backslash_n':sum('\\n' in (r['DESCRIPTION'] or '') for r in rows),
   'literal_unicode_escape':sum(bool(re.search(r'\\u[0-9a-fA-F]{4}',r['DESCRIPTION'] or '')) for r in rows),
   'no_actual_newline':sum('\n' not in (r['DESCRIPTION'] or '') for r in rows),
   'text_normalized_single_line':sum('\n' not in parsed[r['JOB_HASH']]['normalized_text'] for r in rows),
   'literal_newlines_but_normalized_single_line':sum('\\n' in (r['DESCRIPTION'] or '') and '\n' not in parsed[r['JOB_HASH']]['normalized_text'] for r in rows),
   'modules':{m:{'ads_with_candidates':sum(parsed[r['JOB_HASH']]['summary'][m]['candidate_count']>0 for r in rows),
    'ads_with_positive_requirement_candidates':sum(parsed[r['JOB_HASH']]['summary'][m]['requirement_candidate_count']>0 for r in rows)} for m in modules}}
 summary['groups'][country]=stats(rows)
 summary['groups'][country]['by_cohort']={c:stats([r for r in rows if r['COHORT']==c]) for c in sorted(set(r['COHORT'] for r in rows))}
# Selected, explicitly nonrandom illustrations inspected by the assistant.
case_keys=['3c0ed2df5ae4ea3db2b22329d5027824','4ef5a6dcc909318b760ba93cbcc8ec7e','9c33e37f48b459e7bdf0800e199b0a37','f9923855fc00fe4032eb594030c24f21']
for key in case_keys:
 a,x=by[key],parsed[key]
 ev=[e for e in x['evidence'] if e['module'] in ('experience','education','ai')]
 summary['examples'].append({'JOB_HASH':key,'SOURCE_FILE':a['SOURCE_FILE'],'SOURCE_ROW':a['SOURCE_ROW'],
 'cohort':a['COHORT'],'evidence':ev,'sampled_for':'qualitative failure-mode inspection; not accuracy estimate'})
summary['evidence_truncated_ads']=sum(x['evidence_truncated'] for x in parsed.values())
summary['unique_normalized_text_sha256']=len({hashlib.sha256(x['normalized_text'].encode()).hexdigest() for x in parsed.values()})
(B/'pilot_diagnostics.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
for country,g in summary['groups'].items():
 print(country,{k:v for k,v in g.items() if k not in ['modules','by_cohort']})
 print('cohorts', {c:{k:v for k,v in d.items() if k!='modules'} for c,d in g['by_cohort'].items()})
print('truncated',summary['evidence_truncated_ads'],'unique_norm',summary['unique_normalized_text_sha256'])
