"""Prepare isolated, unexecuted CRD Class-B repair requests; no vendor calls."""
import csv,hashlib,json
from pathlib import Path
O=Path(__file__).resolve().parent
A=O.parent.parent/'missing_data_round_20260914/databento_final_acquisition'
def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
receipt=json.loads((O/'identity_clock_receipt.json').read_text())
assert receipt['identity']['class_identity']=='HISTORICAL_CRSP_CLASS_B'
assert receipt['identity']['crd_associations']==12 and receipt['identity']['crd_cusip_agreement']==12
jobs=read(A/'core_grouped_jobs.csv')+read(A/'alternative_grouped_jobs.csv')
symbols={'XNAS.ITCH':'CRD.B','BATS.PITCH':'CRD.B','ARCX.PILLAR':'CRD B','XNYS.PILLAR':'CRD B'}
repairs=[]
for j in jobs:
    if 'CRD' not in j['symbols'].split(';'):continue
    repairs.append(dict(repair_id='CLASSB_'+j['job_id'],original_job_id=j['job_id'],dataset=j['dataset'],schema=j['schema'],original_symbol='CRD',proposed_symbol=symbols[j['dataset']],stype_in='raw_symbol',start=j['start'],end=j['end'],analysis_access=j['analysis_access'],status='PREPARED_NOT_VENDOR_RESOLVED_NOT_ORDERED'))
assert len(repairs)==192
with (O/'CRD_CLASS_B_REPAIR_REQUESTS.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(repairs[0]));w.writeheader();w.writerows(repairs)
queries=[]
for dataset,symbol in symbols.items():
    rs=[r for r in repairs if r['dataset']==dataset]
    from datetime import date,timedelta
    queries.append(dict(dataset=dataset,symbols=[symbol],stype_in='raw_symbol',stype_out='instrument_id',start_date=min(r['start'][:10] for r in rs),end_date=str(date.fromisoformat(max(r['end'][:10] for r in rs))+timedelta(days=1))))
(O/'FREE_SYMBOLOGY_QUERIES.json').write_text(json.dumps(queries,indent=2)+'\n')
(O/'repair_preparation_receipt.json').write_text(json.dumps(dict(status='PREPARED_NOT_EXECUTED',class_provenance='SCC date-valid CRSP shrcls B, same PERMNO and CUSIP for12associations',convention_source='https://databento.com/docs/standards-and-conventions/symbology',repair_windows=len(repairs),free_symbology_calls_prepared=len(queries),original_files_modified=False,download_calls=0,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_identity_receipt_sha256=hashlib.sha256((O/'identity_clock_receipt.json').read_bytes()).hexdigest()),indent=2)+'\n')
print('Prepared192 isolated Class-B windows and4 free symbology queries; zero downloads.')
