"""End-to-end fake Blob/Parquet test; no real data or network is accessed."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import pyarrow as pa
import pyarrow.parquet as pq

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('fresh',HERE/'cloud_prepare_fresh_inputs.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def write(p,x,lines=False):
    p.parent.mkdir(parents=True,exist_ok=True)
    b=(''.join(json.dumps(v)+'\n' for v in x) if lines else json.dumps(x)).encode()
    p.write_bytes(b);return m.digest(b)


def parquet(rows):
    b=io.BytesIO();pq.write_table(pa.Table.from_pylist(rows),b,row_group_size=250);return b.getvalue()


class Response(io.BytesIO):
    status=206
    def __init__(self,data,a,z,total):
        super().__init__(data);self.headers={'Content-Range':f'bytes {a}-{z-1}/{total}','ETag':'"fixture-stable"'}


with tempfile.TemporaryDirectory(prefix='linkup-fresh-fixture-') as tmp:
    r=Path(tmp);probe=r/'confirmation_stage5_20261118/frame_probe_v1';b=r/'integration_20261116/run001'
    body=['<p>Complete synthetic job '+str(i)+'.</p>' for i in range(1000)]
    body[104]=body[103];body[105]=''
    normalizer=Path('/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/corpus_pro_review_20261026/code/legacy_v5_frozen.py')
    nm=m.module(normalizer,m.NORMALIZER_SHA,'fixture_normalizer')._normalize_with_flags
    h=lambda i:m.digest(nm(body[i])[0].encode())
    raw=parquet([{'JOB_HASH':'j'+str(i),'DESCRIPTION':body[i],'NEVER_REQUESTED':'secret-fixture'} for i in range(1000)])
    base_rows=[dict(zip(m.KEY,['j'+str(i),'raw.parquet',i,i])) for i in range(1000)]
    base=parquet(base_rows)
    references=[{**dict(zip(m.KEY,['old'+str(i),'old.parquet',i,i])),'normalized_context_sha256':m.digest(('old-ref'+str(i)).encode())} for i in range(10000)]
    references[0]={**base_rows[100],'normalized_context_sha256':h(100)}
    references[1]['normalized_context_sha256']=h(102)
    ref=parquet(references);m.REFERENCE_SHA=m.digest(ref)
    blobs={'raw.parquet':raw,'base.parquet':base,'ref.parquet':ref}
    def call(url,audience,headers):
        data=blobs[url.rsplit('/',1)[1]]
        a,z=map(int,headers['Range'][6:].split('-'));z+=1
        assert not headers.get('If-Match') or headers['If-Match']=='"fixture-stable"'
        return Response(data[a:z],a,z,len(data))
    sys.modules['workflow']=types.SimpleNamespace(call=call)
    for cluster in ['kunshan','wuzhen','huazhong']:
        write(r/'private'/(cluster+'.json'),{'container_sas':'https://fixture.invalid/container?not-a-real-secret','snapshot':'fake-snapshot'})
        p=r/cluster/'LEDGER_PRIVATE.sqlite';p.parent.mkdir()
        c=sqlite3.connect(p);c.execute('create table files(path text,root text,rel text,size int,status text,sha text)')
        if cluster=='kunshan':
            for name,data in blobs.items():c.execute('insert into files values(?,?,?,?,?,?)',('/old/'+name,'/old',name,len(data),'verified',m.digest(data)))
        c.commit();c.close()
    ip=b/'revision003/STATUS_INDEX_PRIVATE.sqlite';ip.parent.mkdir(parents=True)
    c=sqlite3.connect(ip);c.executescript('create table final_status(h text,state text);create table blocked(h text);')
    c.execute('insert into final_status values(?,?)',(h(101),'not_reconciled'));c.commit();c.close()
    for p in [r/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json',r/'execution_20261116/run001/qualification_frame_v1/FRAME_PRIVATE.json',r/'reuse_first_20261115/run01/benchmark20/SELECTION_PRIVATE.json']:
        write(p,[])
    write(b/'DISCOVERY_PRIVATE.json',{'metadata_inventory':[]})
    oldsha=write(probe/'KNOWN_CONTEXT_EXCLUSION_UNION_PRIVATE.json',{'context_sha256':[h(101)]})
    window={'cursor_gate_blockers':[],'start_cursor':{'shard_ordinal':0,'row_offset':100},'end_cursor_exclusive':{'shard_ordinal':0,'row_offset':250},
       'context_exclusion_union_sha256':oldsha,'batch_predecessor':73,
       'base_register_entry':{'shard_id':'fixture','ad_sha256':m.digest(base),'ad_bytes':len(base),'ad_rows':1000},
       'catalog_entry':{'ad_rows':1000},'description_source_binding':{'source_sha256_from_cached_receipts':m.digest(raw),'source_bytes':len(raw),'source_basename':'raw.parquet','accounting_source_path':'raw.parquet'}}
    windowsha=write(probe/'FINITE_SOURCE_WINDOW_PRIVATE.json',window)
    scorer=HERE.parent/'protocol/field_score.py'
    args=types.SimpleNamespace(root=str(r),output='fresh_fixture',normalizer=str(normalizer),scorer=str(scorer),scorer_sha=m.digest(scorer.read_bytes()),window_sha=windowsha)
    stdout=io.StringIO()
    with contextlib.redirect_stdout(stdout):m.prepare(args)
    report=json.loads(stdout.getvalue());out=r/'fresh_fixture'
    frame=json.loads((out/'FRAME_PRIVATE.json').read_text())
    inputs=[json.loads(x) for x in (out/'INPUTS_PRIVATE.jsonl').read_text().splitlines()]
    assert report['canonical_window_rows']==150
    assert report['fresh_complete_unique_contexts']==145
    assert report['rejected_without_replacement']=={'previous_canonical_identity':1,'previously_known_or_exposed_context_SHA':2,'duplicate_within_fixed_window':1,'empty_after_pinned_normalization':1}
    assert report['old_reference_whole_SHA_verified'] and report['live_exposure_recheck_pass']
    assert not {h(100),h(101),h(102)} & {x['context_sha256'] for x in frame}
    assert all(x['protected'] is False and x['fresh_never_exposed'] is True and x['partition']=='confirmation' for x in frame)
    assert all(m.digest(x['row']['full_document'].encode())==x['row']['context_sha256'] for x in inputs)
    sc=m.module(scorer,args.scorer_sha,'fixture_units')
    assert all(f['source_units_sha256']==sc.digest_json(sc.source_units(x['row']['full_document'])) for f,x in zip(frame,inputs))
    assert len({x['context_sha256'] for x in frame})==145
    print(json.dumps({'synthetic_end_to_end':'pass','window_rows':150,'accepted':145,'not_replaced':5,
        'reference_and_exposure_exclusion':'pass','complete_context_and_unit_binding':'pass',
        'real_data_or_network_used':False}))
