"""Integrate existing metadata/status evidence. Never calls a model or reads source ads.

Creates a new SQLite index and aggregate receipt; does not edit source ledgers.
Public output is bounded. All identity mappings and status-level projections stay private.
"""
import base64, collections, datetime, fcntl, hashlib, json, os, re, sqlite3, sys, time, urllib.parse, zlib
from pathlib import Path

R=Path.home()/'migration'; O=R/'integration_20261116/run001'
SCHEMA='fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e'
FIXED='794d76b2a6e913d7d08adab7e99bc96a3f57f8553c73518ae27b966a8fad86fb'
ISOLATION='641f2d3204a8f65f2483be485815ede04b57920227af4b867afd41cbd6de62b6'
RELATION='9ea1fcd0f61182d2d125b19d90af820f549e77351ff1064320613c311ae0d8a9'
NORMALIZER='336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd'
sys.path.insert(0,str(R/'code'))
from workflow import call

def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_bytes())
def write(p,d):
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
    os.chmod(p,0o600)
def blocked_path(p):return 'batch035' in p.lower() or '01a17beb-973b-74e2-adbb-20f8d004b1fc' in p.lower()
def rows(p):
    with p.open('rb') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def canonical(k):
    if isinstance(k,dict):k=[k[x] for x in ['JOB_HASH','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW']]
    assert isinstance(k,(list,tuple)) and len(k)==4,'canonical_key_shape'
    return json.dumps([str(x) for x in k],separators=(',',':'))

def main():
    os.umask(0o077);O.mkdir(parents=True,exist_ok=True)
    lock=(O/'INTEGRATION.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not (O/'STATUS_INDEX_PRIVATE.sqlite').exists(),'existing_run_preserved_no_duplicate_execution'
    t0=time.monotonic();errors=[];downloaded=0;sources={};cache=O/'metadata_cache';cache.mkdir(exist_ok=True)
    snapshots={}
    def watched(rel):
        p=R/rel;b=p.read_bytes();snapshots[rel]=sha(b);return json.loads(b)
    identities=watched('AZURE_RESEARCH_IDENTITIES_PRIVATE.json')['rows'];bytask={x['task']:x for x in identities}
    assert len(bytask)==len(identities)==1320
    astra=watched('astra/extraction/STATE_PRIVATE.json')
    bulkrel='opencode_kimi_20261115/run01/bulk_1309_20261115/'
    bulk=watched(bulkrel+'CANDIDATE_STATE_PRIVATE.json')
    assert len(bulk['handled'])==1309 and not bulk.get('production_promoted')
    state=watched('AZURE_RESEARCH_STATE.json')
    blocked_tasks={'batch052/packet_0095/1'}
    for task,v in bulk['exceptions'].items():
        if v.get('disposition')=='quarantined' or any(z in v.get('status','') for z in ['quarantin','content_filter']):blocked_tasks.add(task)
    eventpath=R/bulkrel/'QUARANTINE_EVENTS_PRIVATE.json'
    if eventpath.exists():
        for v in watched(bulkrel+'QUARANTINE_EVENTS_PRIVATE.json').get('events',[]):
            if v.get('disposition')=='quarantined' or v.get('retry_forbidden'):blocked_tasks.add(v['task'])
    for v in state.get('quarantine_register',[]):
        if v.get('task'):blocked_tasks.add(v['task'])
    protected={bytask[x]['context_sha256'] for x in blocked_tasks if x in bytask}
    assert len(protected)==42,'known_protection_union_changed'
    inventory=read(O/'DISCOVERY_PRIVATE.json')['metadata_inventory']
    index=collections.defaultdict(list)
    for m in inventory:
        if m['status']=='verified' and not blocked_path(m['path']):index[m['sha256']].append(m)
    configs={};migration={}
    for cluster in ['kunshan','wuzhen','huazhong']:
        db=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');migration[cluster]=db
    def lookup(digest):
        if digest in index:return index[digest][0]
        for cluster,c in migration.items():
            for path,root,rel,size,status,d in c.execute('SELECT path,root,rel,size,status,sha FROM files WHERE sha=?',(digest,)):
                if status=='verified' and not blocked_path(path):
                    m=dict(cluster=cluster,path=path,root=root,rel=rel,size=size,status=status,sha256=d);index[digest].append(m);return m
        return None
    def fetch(m):
        nonlocal downloaded
        assert not blocked_path(m['path']) and m['status']=='verified'
        assert m['size']<=150*1024*1024,'metadata_file_size_cap'
        p=cache/(m['sha256']+'.metadata')
        if p.exists():assert p.stat().st_size==m['size'] and file_sha(p)==m['sha256'];sources[m['sha256']]=m;return p
        assert downloaded+m['size']<=512*1024*1024,'metadata_download_cap'
        if m['cluster'] not in configs:configs[m['cluster']]=read(R/'private'/(m['cluster']+'.json'))
        c=configs[m['cluster']];url=c['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(c['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
        temp=p.with_suffix('.partial');h=hashlib.sha256();n=0
        with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response,temp.open('xb') as f:
            while True:
                b=response.read(1024*1024)
                if not b:break
                n+=len(b);assert n<=m['size'],'response_larger_than_verified_metadata';f.write(b);h.update(b)
        assert n==m['size'] and h.hexdigest()==m['sha256'],'metadata_transport_sha_mismatch'
        temp.rename(p);downloaded+=n;sources[m['sha256']]=m;return p
    def bysha(d):
        m=lookup(d);assert m is not None,'verified_metadata_artifact_missing';return fetch(m)
    for row in rows(bysha(ISOLATION)):protected.add(row['normalized_context_sha256'])
    db=sqlite3.connect(O/'STATUS_INDEX_PRIVATE.sqlite')
    db.executescript('''PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;
    CREATE TABLE context(h TEXT PRIMARY KEY);
    CREATE TABLE ad(k TEXT,h TEXT,source TEXT,PRIMARY KEY(k,h,source));
    CREATE TABLE event(h TEXT,asset TEXT,state TEXT,source TEXT,detail TEXT,PRIMARY KEY(h,asset,state,source));
    CREATE TABLE field(h TEXT,k TEXT,family TEXT,status TEXT,asset TEXT,source TEXT,PRIMARY KEY(h,k,family,asset,source));
    CREATE TABLE relation(candidate TEXT PRIMARY KEY,h TEXT,status TEXT,source TEXT);
    CREATE TABLE blocked(h TEXT PRIMARY KEY);
    CREATE TABLE provenance(sha TEXT PRIMARY KEY,metadata TEXT);
    ''')
    def add_context(h):
        assert isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h);db.execute('INSERT OR IGNORE INTO context VALUES(?)',(h,))
    def event(h,asset,status,source,detail=''):
        add_context(h);db.execute('INSERT OR IGNORE INTO event VALUES(?,?,?,?,?)',(h,asset,status,source,detail))
    def addad(k,h,source):add_context(h);db.execute('INSERT OR IGNORE INTO ad VALUES(?,?,?)',(canonical(k),h,source))
    for h in protected:add_context(h);db.execute('INSERT OR IGNORE INTO blocked VALUES(?)',(h,))

    # Original seven-family masks are imported without structured values or quotes.
    fixed_counts=collections.Counter();fixed_rows=0
    for row in rows(bysha(FIXED)):
        h=row['normalized_context_sha256'];k=canonical(row['canonical_key']);addad(row['canonical_key'],h,FIXED)
        family,status=row['field_family'],row['status'];fixed_counts[(family,status)]+=1;fixed_rows+=1
        db.execute('INSERT INTO field VALUES(?,?,?,?,?,?)',(h,k,family,status,'fixed10k',FIXED))
        if h not in protected:
            event(h,'fixed10k','accepted' if status in ['known','not_applicable','unknown_or_conflict','partial'] else 'saved_unverified',FIXED,'original_field_mask_scope_only')
    assert fixed_rows==70000 and len({x[0] for x in fixed_counts})==7
    assert all(sum(n for (f,s),n in fixed_counts.items() if f==fam)==10000 for fam in {x[0] for x in fixed_counts})

    # Read public receipts, selecting latest matched checkpoint by its pinned manifest.
    manifests={};preps={};receipts=collections.defaultdict(list);merged=[]
    for digest,ms in list(index.items()):
        m=ms[0]
        if 'corpus_pro_review_20261026' not in m['path']:continue
        if m['rel'].endswith('PACKET_MANIFEST_PRIVATE.jsonl'):
            rr=list(rows(fetch(m)));assert not any('full_document' in r for r in rr)
            manifests[digest]=(m,rr)
        elif m['rel'].endswith('PACKET_PREPARATION_PUBLIC.json'):
            o=read(fetch(m));mh=o.get('packet_manifest_sha256') or o.get('output_sha256',{}).get('packet_manifest_private')
            if mh:preps[mh]=(m,o)
        elif m['rel'].endswith('CHECKPOINT_RECEIPT_PUBLIC.json'):
            o=read(fetch(m));mh=o.get('inputs',{}).get('packet_manifest_sha256')
            if mh:receipts[mh].append((m,o))
        elif m['rel'].endswith('MERGED_RECEIPT_PUBLIC.json'):merged.append((m,read(fetch(m))))
    primary_packets=set()
    for cluster,c in migration.items():
        for path,status in c.execute("SELECT path,status FROM files WHERE path LIKE '%corpus_pro_review_20261026%' AND rel LIKE '%PRIMARY.jsonl'"):
            if blocked_path(path):continue
            match=re.search(r'(batch\d+)_?(packet_\d{4})_PRIMARY\.jsonl$',path)
            if match and status=='verified':primary_packets.add(match.groups())
    pro_by_hash={};batch_summaries=[];latest_refs=[]
    for mh,(m,rr) in sorted(manifests.items()):
        batch=re.search(r'batch\d+',m['path']).group(0)
        assert len({r['context_sha256'] for r in rr})==len(rr)
        options=sorted(receipts.get(mh,[]),key=lambda x:x[1].get('created_utc',''))
        chosen=options[-1] if options else None
        if chosen:
            cm,c=chosen;assert c['inputs']['schema_sha256']==SCHEMA,'Pro_schema_mismatch'
            packets={x['name']:x for x in c.get('packets',[])}
            assert sum(x.get('expected_records',0) for x in packets.values())==len(rr),'receipt_manifest_count_mismatch'
            assert len(packets)==(len(rr)+4)//5,'packet_order_contract_count'
        else:cm,c,packets=None,None,{}
        counts=collections.Counter()
        for i,r in enumerate(rr):
            h=r['context_sha256'];assert r['record_id']=='corpus-pro-'+h
            assert h not in pro_by_hash,'prepared_contexts_not_disjoint'
            pro_by_hash[h]=(batch,mh)
            for k in r['canonical_keys']:addad(k,h,mh)
            pn=f'packet_{i//5+1:04d}.jsonl';item=packets.get(pn,{})
            if h in protected:st='quarantined'
            elif item.get('status')=='accepted':st='accepted'
            elif (batch,pn[:-6]) in primary_packets or item.get('status')=='failed':st='saved_unverified'
            elif item.get('status')=='pending':st='unprocessed_asof_checkpoint'
            else:st='not_reconciled'
            event(h,'Pro',st,cm['sha256'] if cm else mh,batch);counts[st]+=1
        if c:
            assert sum(x.get('expected_records',0) for x in packets.values() if x.get('status')=='accepted')==c['counts']['accepted_contexts']
            latest_refs.append((mh,cm,c))
        batch_summaries.append({'batch':batch,'prepared':len(rr),'checkpoint_matched':bool(c),'states':dict(counts),'manifest_sha256':mh,'receipt_sha256':cm['sha256'] if cm else None})
    assert len(manifests)==72 and len(pro_by_hash)==48240,'known_Pro_manifest_scope_changed'

    # Status-only projection of the SHA-pinned accepted context ledgers.
    pro_refs_projected=0;reference_contexts=0
    for mh,cm,c in latest_refs:
        digest=c.get('outputs',{}).get('context_ledger_sha256');meta=lookup(digest) if digest else None
        if meta is None:
            errors.append({'kind':'accepted_context_ledger_missing','receipt_sha256':cm['sha256']});continue
        seen=set()
        for row in rows(fetch(meta)):
            h=row['context_sha256'];assert h in pro_by_hash and pro_by_hash[h][1]==mh and h not in seen;seen.add(h)
            if h in protected:continue
            dims={'document_status':row['document_status'],'technology_inventory_status':row['technology_inventory_status']}
            for family in ['experience_outcomes','entry_outcomes','responsibility_outcomes']:
                dims.update({family+'.'+k:v for k,v in row[family].items()})
            for f,status in dims.items():db.execute('INSERT INTO field VALUES(?,?,?,?,?,?)',(h,'',f,status,'Pro',digest))
        assert len(seen)==c['counts']['accepted_contexts'],'accepted_context_projection_count'
        pro_refs_projected+=1;reference_contexts+=len(seen)
    # Audited merged releases are separate status evidence, never overwritten by primary.
    merge_projected=0
    for m,c in merged:
        if c.get('status') not in ['complete','pass','accepted']:continue
        digest=c.get('outputs',{}).get('context_ledger_sha256');meta=lookup(digest) if digest else None
        if meta is None:continue
        for row in rows(fetch(meta)):
            h=row['context_sha256'];assert h in pro_by_hash
            if h in protected:continue
            for family in ['experience_outcomes','entry_outcomes','responsibility_outcomes']:
                for f,status in row[family].items():db.execute('INSERT OR IGNORE INTO field VALUES(?,?,?,?,?,?)',(h,'',family+'.'+f,status,'Pro_merged',digest))
            event(h,'Pro_merged','accepted',digest,'audited_overlay_preserved_separately')
        merge_projected+=1

    # Existing exact-context ad bindings add mappings, not new labels or new reads.
    binding_rows=0;binding_sources=0
    for mh,(m,p) in preps.items():
        digest=p.get('output_sha256',{}).get('reuse_ad_bindings_private')
        if not digest:continue
        meta=lookup(digest)
        if not meta:errors.append({'kind':'reuse_binding_metadata_missing','preparation_sha256':m['sha256']});continue
        for row in rows(fetch(meta)):
            h=row.get('context_sha256') or row.get('normalized_context_sha256')
            assert h and row.get('canonical_key') is not None,'reuse_binding_shape'
            addad(row['canonical_key'],h,digest);binding_rows+=1
        binding_sources+=1

    # Parent Astra/Kimi partition supersedes its historical unprocessed snapshot.
    astra_hashes={v['context_sha256'] for v in astra['accepted'].values()}
    for t,r in bytask.items():
        h=r['context_sha256']
        if h in protected:st='quarantined'
        elif h in astra_hashes:st='accepted'
        elif t in bulk['engineering_candidates']:
            v=bulk['engineering_candidates'][t];assert v['context_sha256']==h and v['record_id']==r['record_id'];st='saved_unverified'
        elif t in bulk['handled']:st='saved_unverified'
        elif r.get('execution_state')=='saved_unverified':st='saved_unverified'
        else:st='not_reconciled'
        event(h,'Azure_parent',st,snapshots[bulkrel+'CANDIDATE_STATE_PRIVATE.json'],bulk['handled'].get(t,{}).get('status',r.get('execution_state','')))
    # Supplemental relation ledger: only identity/status projected; no reinterpretation.
    relation_status=collections.Counter()
    for row in rows(bysha(RELATION)):
        h=row['context_sha256'];add_context(h);status=row['review_status'];relation_status[status]+=1
        db.execute('INSERT INTO relation VALUES(?,?,?,?)',(row['candidate_id'],h,status,RELATION))
    assert sum(relation_status.values())==2736

    # Deny-first, nonduplicative status view. An accepted context need not have all fields known.
    db.executescript('''CREATE VIEW final_status AS SELECT c.h,
    CASE WHEN EXISTS(SELECT 1 FROM blocked b WHERE b.h=c.h) THEN 'quarantined'
    WHEN EXISTS(SELECT 1 FROM event e WHERE e.h=c.h AND e.state='accepted') THEN 'accepted_original_scope'
    WHEN EXISTS(SELECT 1 FROM event e WHERE e.h=c.h AND e.state='saved_unverified') THEN 'saved_unverified'
    WHEN EXISTS(SELECT 1 FROM event e WHERE e.h=c.h AND e.state='unprocessed_asof_checkpoint') THEN 'unprocessed_asof_checkpoint'
    ELSE 'not_reconciled' END state FROM context c;
    CREATE INDEX event_h ON event(h); CREATE INDEX field_h ON field(h); CREATE INDEX ad_h ON ad(h);
    ''')
    counts=dict(db.execute('SELECT state,count(*) FROM final_status GROUP BY state'))
    states_by_asset={}
    for asset,st,n in db.execute('SELECT asset,state,count(DISTINCT h) FROM event GROUP BY asset,state'):states_by_asset.setdefault(asset,{})[st]=n
    field_counts={}
    for a,f,s,n in db.execute('SELECT asset,family,status,count(*) FROM field GROUP BY asset,family,status'):field_counts.setdefault(a,{}).setdefault(f,{})[s]=n
    unknown_contexts=db.execute("SELECT count(DISTINCT h) FROM field WHERE status IN ('unknown','unknown_or_conflict','unresolved','reviewed_partial','partial')").fetchone()[0]
    fixed_pro_overlap=db.execute("SELECT count(DISTINCT x.h) FROM event x JOIN event y ON x.h=y.h WHERE x.asset='fixed10k' AND y.asset='Pro'").fetchone()[0]
    source_changed=[rel for rel,d in snapshots.items() if file_sha(R/rel)!=d];assert not source_changed,'source_changed_during_integration'
    for digest,m in sources.items():db.execute('INSERT INTO provenance VALUES(?,?)',(digest,json.dumps(m)))
    db.commit();checks=db.execute('PRAGMA integrity_check').fetchall();assert checks==[('ok',)]
    ad_keys=db.execute('SELECT count(*) FROM (SELECT DISTINCT k FROM ad)').fetchone()[0]
    ad_context_bindings=db.execute('SELECT count(*) FROM (SELECT DISTINCT k,h FROM ad)').fetchone()[0]
    key_version_conflicts=db.execute('SELECT count(*) FROM (SELECT k FROM ad GROUP BY k HAVING count(DISTINCT h)>1)').fetchone()[0]
    contexts=db.execute('SELECT count(*) FROM context').fetchone()[0];assert sum(counts.values())==contexts
    queue=O/'PENDING_METADATA_ONLY_PRIVATE.jsonl'
    with queue.open('x') as f:
        for h,st in db.execute("SELECT h,state FROM final_status WHERE state IN ('unprocessed_asof_checkpoint','not_reconciled') ORDER BY h"):
            f.write(json.dumps({'context_sha256':h,'state':st,'inference_admitted':False,'reason':'membership/status reconciliation only; field-specific work contract and latest stored-output checks still required'})+'\n')
    db.close()
    report={'version':1,'status':'known_asset_identity_status_union_completed_not_full_delivery','observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-t0,3),'identity_type':'VM system-assigned managed identity for Blob reads; Unix linkup execution','metadata_files_sha_verified':len(sources),'metadata_bytes_downloaded_this_run':downloaded,'source_ledgers_unchanged':True,'database_integrity':'ok','known_union_unique_contexts':contexts,'unique_canonical_ad_keys':ad_keys,'distinct_ad_context_bindings':ad_context_bindings,'canonical_keys_with_multiple_body_versions_preserved':key_version_conflicts,'context_state_partition':counts,'context_states_by_asset_not_additive':states_by_asset,'reviewed_unknown_or_partial_contexts_overlapping_states':unknown_contexts,'fixed10k_field_rows':fixed_rows,'fixed10k_Pro_context_overlap':fixed_pro_overlap,'pro_manifest_count':len(manifests),'pro_prepared_contexts':len(pro_by_hash),'latest_checkpoint_manifests':len(latest_refs),'accepted_context_ledgers_projected':pro_refs_projected,'accepted_Pro_contexts_in_projected_ledgers':reference_contexts,'merged_status_ledgers_projected':merge_projected,'exact_reuse_binding_rows_imported':binding_rows,'exact_reuse_binding_sources':binding_sources,'supplemental_relation_status_counts':dict(relation_status),'known_protected_contexts':len(protected),'batch035_content_not_opened':True,'metadata_gaps':errors,'field_status_counts':field_counts,'batch_statuses':batch_summaries,'current_pilot_parent_contexts':1320,'current_bulk_handled':1309,'new_model_calls':0,'new_production_accepted':0,'new_source_ad_reads':0,'full_requested_rows_estimate':500000000,'full_delivery_identity_union_complete':False,'global_remaining_new_model_contexts':None,'not_an_execution_queue':True,'remaining_scope_caveats':['Coverage is the union of discovered prepared/accepted/binding metadata, not all delivery records.','accepted_original_scope means accepted under its original field/reference mask; it does not mean all semantic fields known or model-accuracy certification.','saved_unverified includes preserved exceptions and saved PRIMARY metadata, never an instruction to rerun them.','unprocessed_asof_checkpoint is not permission to infer; incomplete receipt coverage and later saved outputs require conservative admission.','Pro merged overlays stay separate; field disagreements are not resolved by recency or majority.','Full-delivery and normalized-text universes remain unresolved; no 500M-minus-US subtraction.'],'source_snapshot_sha256':snapshots,'database_sha256':file_sha(O/'STATUS_INDEX_PRIVATE.sqlite'),'pending_metadata_sha256':file_sha(queue),'normalizer_sha256':NORMALIZER,'schema_sha256':SCHEMA}
    write(O/'INTEGRATION_PUBLIC.json',report);write(O/'SOURCE_MANIFEST_PRIVATE.json',list(sources.values()))
    compact={k:report[k] for k in ['status','elapsed_seconds','metadata_files_sha_verified','metadata_bytes_downloaded_this_run','known_union_unique_contexts','unique_canonical_ad_keys','context_state_partition','fixed10k_Pro_context_overlap','pro_manifest_count','latest_checkpoint_manifests','accepted_context_ledgers_projected','accepted_Pro_contexts_in_projected_ledgers','merged_status_ledgers_projected','exact_reuse_binding_rows_imported','known_protected_contexts','database_sha256','new_model_calls','new_production_accepted']}
    compact['metadata_gap_count']=len(errors);compact['report_sha256']=file_sha(O/'INTEGRATION_PUBLIC.json')
    print(json.dumps(compact,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except Exception as e:
        # Exception text may contain row identifiers: never emit it.
        failure={'status':'integration_failed_preserve_partial','exception_type':type(e).__name__}
        import traceback
        (O/'FAILURE_PRIVATE.txt').write_text(traceback.format_exc())
        print(json.dumps(failure));raise SystemExit(2)
