"""Bind the frozen 500-case frame to existing full inputs; no model requests.

Reads bounded, SHA-verified existing prepared packets, not source corpus files.
Retains all selected cases, including unknowns; does not replace missing cases.
"""
import collections, concurrent.futures, datetime, hashlib, json, os, sqlite3, sys, urllib.parse
from pathlib import Path

R=Path.home()/'migration'; B=R/'execution_20261116/run001'; Q=B/'qualification500_v1'
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    os.umask(0o077)
    framepath=B/'qualification_frame_v1/FRAME_PRIVATE.json'
    assert sha(framepath)=='28821e74712ce7d102044cc6a002d25f9cae9218c089897150bda38085ce2ab8'
    frame=read(framepath); assert len(frame)==500
    idx=sqlite3.connect((R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
    blocked={h for h, in idx.execute('select h from blocked')}
    kroot=R/'opencode_kimi_20261115/run01/bulk_1309_20261115'
    kl=read(kroot/'CANDIDATE_STATE_PRIVATE.json')
    identities=read(R/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json')['rows']
    bytask={x['task']:x for x in identities}
    forbidden_tasks={t for t,v in kl['exceptions'].items() if v.get('retry_forbidden') or v.get('disposition')=='quarantined' or 'quarantin' in v.get('status','')}
    ev=kroot/'QUARANTINE_EVENTS_PRIVATE.json'
    if ev.exists():
        for x in read(ev).get('events',[]):
            if x.get('retry_forbidden') or x.get('disposition')=='quarantined': forbidden_tasks.add(x['task'])
    for t in bytask:
        if t.startswith('batch035/'): forbidden_tasks.add(t)
    forbidden_hashes={bytask[t]['context_sha256'] for t in forbidden_tasks if t in bytask}
    # The metadata frame did not enumerate ordinary retry-forbidden Kimi failures.
    # This explicit intersection check must pass before opening any selected input.
    assert not ({x['context_sha256'] for x in frame} & (blocked|forbidden_hashes)), 'frozen_frame_contains_forbidden_input_preserve_and_stop'
    assert not Q.exists(), 'partial_preparation_preserved_no_overwrite'
    Q.mkdir(); (Q/'input_cache').mkdir()
    pins={str(p.relative_to(R)):sha(p) for p in [framepath,kroot/'CANDIDATE_STATE_PRIVATE.json',R/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json',R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite']}
    plan=read(B/'stage2/REMAINING_SOURCE_LOCATORS_PRIVATE.json'); mapping=plan['mapping']
    jobs={}; locations={}; selected={x['context_sha256']:x for x in frame}
    for h,x in selected.items():
        if x['stratum']=='existing_Kimi_saved':
            candidates=[v for v in kl['engineering_candidates'].values() if v['context_sha256']==h]
            assert len(candidates)==1
            v=candidates[0]; vp=Path(v['path']); assert sha(vp)==v['validated_sha256']
            ip=vp.parent/'INPUT_PRIVATE.jsonl'; sums=read(ip.parent.parent/'SHA256SUMS.json')
            assert sha(ip)==sums[str(ip.relative_to(ip.parent.parent))]
            locations[h]={'path':str(ip),'line':0,'sha256':sha(ip),'reference_path':str(vp),'reference_sha256':sha(vp)}
        else:
            m=mapping[h]; assert m['batch']!='batch035'
            d=plan['input_packet_sha_by_manifest'].get(m['manifest_sha256'],{}).get(m['packet'])
            assert d, 'prepared_packet_pin_missing_no_replacement'
            locations[h]={'line':m['ordinal'],'sha256':d}
            cached=B/'stage2/revision002/cache'/(d+'.data')
            if cached.exists(): assert sha(cached)==d; locations[h]['path']=str(cached)
            else: jobs[d]=None
    configs={}
    for cluster in ['kunshan','wuzhen','huazhong']:
        c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
        needed=list(jobs)
        for start in range(0,len(needed),800):
            ds=needed[start:start+800]
            if not ds: continue
            for path,root,rel,size,status,d in c.execute('select path,root,rel,size,status,sha from files where sha in ('+','.join('?' for _ in ds)+')',ds):
                if status=='verified' and 'batch035' not in path.lower(): jobs[d]={'cluster':cluster,'root':root,'rel':rel,'size':size}
        c.close();configs[cluster]=read(R/'private'/(cluster+'.json'))
    assert all(jobs.values()), 'prepared_packet_not_located_no_replacement'
    assert sum(x['size'] for x in jobs.values())<=64*1024*1024, 'bounded_preparation_network_cap'
    sys.path.insert(0,str(R/'code')); from workflow import call
    def fetch(d):
        m=jobs[d]; cfg=configs[m['cluster']]
        url=cfg['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(cfg['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
        with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response: data=response.read(m['size']+1)
        assert len(data)==m['size'] and hashlib.sha256(data).hexdigest()==d
        (Q/'input_cache'/(d+'.data')).write_bytes(data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(fetch,sorted(jobs)))
    for h,x in locations.items():
        if 'path' not in x: x['path']=str(Q/'input_cache'/(x['sha256']+'.data'))
    inputs=[]; refs=[]; sizes=[]
    for n,item in enumerate(frame):
        h=item['context_sha256']; loc=locations[h]; p=Path(loc['path']); assert sha(p)==loc['sha256']
        # Skip unselected packet rows as bytes, without parsing their text.
        line=next(raw for i,raw in enumerate(p.open('rb')) if i==loc['line'])
        row=json.loads(line); assert row['context_sha256']==h and hashlib.sha256(row['full_document'].encode()).hexdigest()==h
        row={k:row[k] for k in ['record_id','context_sha256','full_document']}
        inputs.append({'case':f'case{n:04d}','stratum':item['stratum'],'split':item['split'],'row':row})
        sizes.append(len(row['full_document'].encode()))
        if 'reference_path' in loc:
            rv=json.loads(Path(loc['reference_path']).read_text().strip()); assert rv['context_sha256']==h
            refs.append({'case':f'case{n:04d}','source':'prior_independent_Kimi','review':rv,'source_sha256':loc['reference_sha256']})
    assert len(inputs)==500 and len(refs)==150
    (Q/'INPUTS_PRIVATE.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in inputs))
    (Q/'PRIOR_KIMI_REFERENCES_PRIVATE.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in refs))
    save(Q/'SOURCE_LOCATORS_PRIVATE.json',locations)
    frozen={'code/validate_reviews.py':'f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20','astra/extraction/FORMAL800_REVIEW_SCHEMA.json':'fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e','astra/extraction/REVIEW_INSTRUCTIONS.md':'f13e1c431b4018fb7d1e2f1dc985dece69f092a8713c7ef673497a0fbd728d26'}
    for rel,d in frozen.items(): assert sha(R/rel)==d
    (Q/'SCHEMA.json').write_bytes((R/'astra/extraction/FORMAL800_REVIEW_SCHEMA.json').read_bytes())
    (Q/'INSTRUCTIONS.md').write_bytes((R/'astra/extraction/REVIEW_INSTRUCTIONS.md').read_bytes())
    for rel,d in pins.items(): assert sha(R/rel)==d
    save(Q/'PINS_PRIVATE.json',{'source':pins,'runtime':frozen,'prepared':{n:sha(Q/n) for n in ['INPUTS_PRIVATE.jsonl','PRIOR_KIMI_REFERENCES_PRIVATE.jsonl','SCHEMA.json','INSTRUCTIONS.md']}})
    save(Q/'EXCLUSIONS_PRIVATE.json',{'context_sha256':sorted(blocked|forbidden_hashes),'tasks':sorted(forbidden_tasks)})
    report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'500_frozen_inputs_SHA_verified_no_inference_yet','selected_inputs':500,'unique_contexts':len(selected),'existing_independent_Kimi_references':150,'new_independent_Kimi_references_needed':350,'selected_input_bytes':sum(sizes),'max_input_utf8_bytes':max(sizes),'new_packet_files_read':len(jobs),'new_packet_bytes_read':sum(x['size'] for x in jobs.values()),'corpus_source_files_read':0,'protected_and_retry_forbidden_intersection':0,'frozen_frame_unchanged':True,'input_sha256':sha(Q/'INPUTS_PRIVATE.jsonl'),'model_calls':0,'new_production_accepted':0,'paper_paused':True,'runtime_not_started':True}
    save(Q/'PREPARATION_PUBLIC.json',report);print(json.dumps(report))
if __name__=='__main__':
    try: main()
    except Exception as e:
        import traceback
        B.mkdir(exist_ok=True);(B/'QUALIFICATION_INPUT_FAILURE_PRIVATE.txt').write_text(traceback.format_exc())
        print(json.dumps({'status':'qualification_input_preparation_failed_preserved','type':type(e).__name__}));raise SystemExit(2)
