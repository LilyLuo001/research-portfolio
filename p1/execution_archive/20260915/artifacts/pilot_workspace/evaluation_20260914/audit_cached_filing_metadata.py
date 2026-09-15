"""Read genInfo only for the five planned packages' cached SEC XMLs."""
import csv, hashlib, json, xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

BASE=Path('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1')
CACHE=Path('/Users/lilyluo/research-portfolio/p1/t2_free/cache/nport')
OUT=Path(__file__).resolve().parent
WAVES={'W002','W013','W016','W021','W025'}
with (BASE/'exposure/exposure_universe_gate0_pass.csv').open() as f:
 selected=[{k:r[k] for k in ['wave_id','pre_series_id','pre_series_name','pre_cik','pre_report_date','pre_accession']}
           for r in csv.DictReader(f) if r['wave_id'] in WAVES]
ciks={str(int(float(r['pre_cik']))) for r in selected}
series={r['pre_series_id'] for r in selected}
entries=defaultdict(list); files_seen=0; errors=[]
for cik in sorted(ciks):
 for p in sorted(CACHE.glob(cik+'_*.xml')):
  files_seen+=1
  try:
   with p.open('rb') as f:
    for event,elem in ET.iterparse(f,events=('end',)):
     if elem.tag.split('}')[-1]=='genInfo':
      fields={e.tag.split('}')[-1]:(e.text or '').strip() for e in elem.iter()}
      sid=fields.get('seriesId')
      if sid in series: entries[sid].append({'path':str(p),'report_date':fields.get('repPdDate'),
       'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
      break
  except Exception as e: errors.append({'path':str(p),'error':type(e).__name__})
result=[]
for r in selected:
 items=entries[r['pre_series_id']]
 dates=sorted({e['report_date'] for e in items if e['report_date']})
 # Only Bridgeway has a date-specific primary announcement source pinned this run.
 cutoff='2022-08-26' if r['wave_id']=='W016' else None
 before=[e for e in items if cutoff and e['report_date'] and e['report_date']<cutoff]
 result.append({**r,'cached_filings':len(items),'min_cached_report_date':dates[0] if dates else None,
 'max_cached_report_date':dates[-1] if dates else None,'verified_announcement_cutoff':cutoff,
 'cached_reports_before_cutoff':len(before) if cutoff else None,
 'latest_cached_report_before_cutoff':max((e['report_date'] for e in before),default=None),
 'all_geninfo_sources':items,'ownership_reconstruction':'NOT_RUN'})
obj={'status':'EXECUTED_GENINFO_ONLY','scope':'FIVE_ORIGINALLY_PLANNED_PACKAGES',
 'input_gate0_sha256':hashlib.sha256((BASE/'exposure/exposure_universe_gate0_pass.csv').read_bytes()).hexdigest(),
 'cik_cache_files_inspected':files_seen,'errors':errors,'series':result,
 'holdings_rows_inspected':False,'financial_values_returned':False,
 'note':'File hashing is byte integrity, not inspection of holding values. Cached coverage is not complete SEC universe coverage.'}
(OUT/'cached_filing_metadata_receipt.json').write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps({**{k:v for k,v in obj.items() if k!='series'},'series':[{k:v for k,v in r.items() if k!='all_geninfo_sources'} for r in result]},indent=2))
