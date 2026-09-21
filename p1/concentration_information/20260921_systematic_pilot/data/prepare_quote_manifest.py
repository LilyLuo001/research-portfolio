"""SCC metadata-only locator, including partial intervals; no record iteration."""
import csv
import hashlib
import json
import sys
from datetime import datetime,timedelta
from pathlib import Path
import databento as db

PHYSICAL=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/databento_final_native/control/download_manifest.csv')
def instant(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
def ns(t): return int(t.timestamp()*1_000_000_000)
def file_digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()

def main():
    root=Path(sys.argv[1]); contract=json.loads((root/'DIAGNOSTIC_CONTRACT.json').read_text())
    variants=contract['variants']; sources={}; nrows=0
    with PHYSICAL.open() as f:
        for row in csv.DictReader(f):
            nrows+=1
            symbols=set(row['symbols'].split(';'))
            if not symbols.intersection({'SPY','QQQ'}) or row['schema']!='bbo-1s': continue
            start,end=instant(row['start']),instant(row['end'])
            matches=[v['variant'] for v in variants if start<instant(v['anchor_utc'])+timedelta(minutes=75) and end>instant(v['anchor_utc'])-timedelta(minutes=15)]
            if matches:
                sources[row['path']]={'path':row['path'],'dataset':row['dataset'],'source':'physical_manifest','job_id':row['job_id'],'expected_sha256':row.get('sha256'),'candidate_variants':matches}
    with (root/'LEGACY_DBN_MANIFEST.csv').open() as f:
        for row in csv.DictReader(f):
            sources.setdefault(row['dbn_path'],{'path':row['dbn_path'],'dataset':row['dataset'],'source':'legacy_nine_manifest','job_id':None,'candidate_variants':[v['variant'] for v in variants if v['event_id']==row['event_id']]})
    results=[]
    for row in sources.values():
        p=Path(row['path']); row['exists']=p.is_file()
        if not row['exists']: results.append(row); continue
        row['bytes']=p.stat().st_size
        try:
            store=db.DBNStore.from_file(p); m=store.metadata
            if str(m.schema)!='bbo-1s' or str(m.dataset)!=row['dataset']: raise ValueError('declared/header mismatch')
            row.update(header_dataset=str(m.dataset),header_schema=str(m.schema),header_start_ns=int(m.start),header_end_ns=int(m.end),
                       target_mappings={k:v for k,v in m.mappings.items() if k in {'SPY','QQQ'}})
            row['intervals']=[dict(variant=v['variant'],full_requested_window=int(m.start)<=ns(instant(v['anchor_utc'])-timedelta(minutes=15)) and int(m.end)>=ns(instant(v['anchor_utc'])+timedelta(minutes=75))) for v in variants if v['variant'] in row['candidate_variants']]
            row['sha256']=file_digest(p)
            if row.get('expected_sha256') and row['expected_sha256']!=row['sha256']: raise ValueError('manifest checksum mismatch')
            row['status']='HEADER_ONLY_CHECKED'
        except Exception as e: row.update(status='HEADER_ERROR',error_type=type(e).__name__)
        results.append(row)
    out={'status':'METADATA_ONLY_NOT_DECODED','physical_manifest':str(PHYSICAL),'physical_manifest_sha256':hashlib.sha256(PHYSICAL.read_bytes()).hexdigest(),
      'physical_rows':nrows,'contract_sha256':hashlib.sha256((root/'DIAGNOSTIC_CONTRACT.json').read_bytes()).hexdigest(),
      'locator_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'files':results}
    (root/'QUOTE_INPUT_MANIFEST.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
    print(json.dumps({'candidate_files':len(results),'header_checked':sum(r.get('status')=='HEADER_ONLY_CHECKED' for r in results),'output':str(root/'QUOTE_INPUT_MANIFEST.json')}))

if __name__=='__main__': main()
