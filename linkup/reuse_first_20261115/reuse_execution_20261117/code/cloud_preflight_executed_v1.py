"""Read existing cloud metadata/schema only, preserving original outputs."""
import base64
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import zlib


def main():
    os.umask(0o077)
    root=Path.home()/'migration'
    output=root/'reuse_execution_20261117/run001'
    output.mkdir(parents=True,exist_ok=True)
    receipt=output/'PREFLIGHT_PUBLIC.json'
    assert not receipt.exists(), 'existing_preflight_read_do_not_overwrite'
    state_path=root/'execution_20261116/run001/AZURE_RESEARCH_STATE.json'
    state=json.loads(state_path.read_text())
    assert not state['step4_released'] and not state['step6_released']
    dbpath=root/state['database_relative_to_migration']
    db=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON')
    schema={name:[{'name':r[1],'type':r[2]} for r in db.execute('PRAGMA table_info('+name+')')] for name in
            ['document','ad','field_mask','field_value','source','issue','protected','metadata_evidence','metadata_resolution']}
    counts={name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in schema}
    assets=[{'asset':a,'documents':n,'contexts':c,'original_accepted':v} for a,n,c,v in
            db.execute('SELECT asset,COUNT(*),COUNT(DISTINCT h),original_accepted FROM document GROUP BY asset,original_accepted')]
    masks=[{'asset':a,'family':f,'status':s,'rows':n} for a,f,s,n in
            db.execute('SELECT asset,family,status,COUNT(*) FROM field_mask GROUP BY asset,family,status')]
    # Return JSON shape names and types only, not any advertisement or label value.
    shapes={}
    for asset, in db.execute('SELECT DISTINCT asset FROM document'):
        structure=collections.defaultdict(set)
        def walk(x, prefix='', depth=0):
            if depth>6:return
            structure[prefix].add(type(x).__name__)
            if isinstance(x,dict):
                for k,v in x.items():walk(v,prefix+'.'+k if prefix else k,depth+1)
            elif isinstance(x,list):
                for item in x[:2]:walk(item,prefix+'[]',depth+1)
        for raw, in db.execute('SELECT document_json FROM document WHERE asset=? LIMIT 3',(asset,)):
            walk(json.loads(raw))
        shapes[asset]={k:sorted(v) for k,v in structure.items()}
    exclusions=json.loads((root/state['runtime_exclusions_relative_to_migration']).read_text())
    processes=[]
    known=['cloud_qualification_luna_worker.py','cloud_astra_audit_worker.py','cloud_astra_transport_recovery_worker.py','hold_reference_lane.py','reuse_execution_20261117']
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            b=p.read_bytes()
            matches=[s for s in known if s.encode() in b]
            if matches and int(p.parent.name)!=os.getpid():processes.append({'pid':int(p.parent.name),'matched_programs':matches})
        except (OSError,ValueError):pass
    db.close()
    report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'read_only_preflight_complete','cloud_user':os.environ.get('USER','unknown'),
        'state_sha256':hashlib.sha256(state_path.read_bytes()).hexdigest(),
        'database_relative_to_migration':str(dbpath.relative_to(root)),
        'database_bytes':dbpath.stat().st_size,'database_expected_sha256':state['database_sha256'],
        'available_disk_bytes':shutil.disk_usage(root).free,'cpu_count':os.cpu_count(),
        'schema':schema,'table_counts':counts,'document_assets':assets,'field_mask_statuses':masks,
        'document_shape_only':shapes,'runtime_exclusion_contexts':len(exclusions.get('context_sha256',[])),
        'related_processes':processes,'new_model_calls':0,'production_launched':False,
        'source_database_query_only':True,'raw_advertisement_files_read':0,'no_row_values_exported':True}
    receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    b=receipt.read_bytes()
    # Split transport is handled outside this code if the compact result is large.
    compressed=base64.b64encode(zlib.compress(b,9)).decode()
    if len(compressed)<3500:print(json.dumps({'report_zlib_b64':compressed,'sha256':hashlib.sha256(b).hexdigest()}))
    else:print(json.dumps({'status':report['status'],'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'requires_split_metadata_transport':True,'table_counts':counts,'document_assets':assets}))


if __name__=='__main__':main()
