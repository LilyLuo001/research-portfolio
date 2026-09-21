"""SCC-only record projection. No quote levels, sizes or returns are emitted."""
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path
import databento as db
from databento_dbn import UNDEF_PRICE,UNDEF_ORDER_SIZE,BBOMsg

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def instant(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
def ns(t): return int(t.timestamp()*1_000_000_000)
def file_digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()

def main():
    root=Path(sys.argv[1]); permit=json.loads((root/'DIAGNOSTIC_RELEASE.json').read_text())
    if permit.get('status')!='APPROVED_DIAGNOSTIC_ONLY': raise RuntimeError('no diagnostic release')
    for name,sha in permit['artifact_sha256'].items():
        if digest(root/name)!=sha: raise RuntimeError('changed diagnostic artifact')
    manifest=json.loads((root/'QUOTE_INPUT_MANIFEST.json').read_text()); contract=json.loads((root/'DIAGNOSTIC_CONTRACT.json').read_text())
    if manifest.get('status')!='METADATA_ONLY_NOT_DECODED' or manifest['contract_sha256']!=digest(root/'DIAGNOSTIC_CONTRACT.json'): raise RuntimeError('invalid manifest binding')
    if set(permit['artifact_sha256']) != {'QUOTE_INPUT_MANIFEST.json','DIAGNOSTIC_CONTRACT.json','quote_state_diagnostic.py'}: raise RuntimeError('incomplete diagnostic binding')
    rows=[]; summaries=[]; skipped=[]
    for source in manifest['files']:
        if source.get('status')!='HEADER_ONLY_CHECKED':
            skipped.append({'path':source['path'],'reason':source.get('status','MISSING_FILE'),'candidate_variants':source['candidate_variants']}); continue
        p=Path(source['path'])
        if p.stat().st_size!=source['bytes']: raise RuntimeError('file size changed')
        if file_digest(p)!=source['sha256']: raise RuntimeError('file content changed')
        store=db.DBNStore.from_file(p)
        m=store.metadata
        current_maps=json.loads(json.dumps({k:v for k,v in m.mappings.items() if k in {'SPY','QQQ'}},default=str))
        if str(m.schema)!='bbo-1s' or str(m.dataset)!=source['header_dataset'] or str(m.dataset)!=source['dataset'] or int(m.start)!=source['header_start_ns'] or int(m.end)!=source['header_end_ns'] or current_maps!=source['target_mappings']: raise RuntimeError('header changed')
        variants=[v for v in contract['variants'] if v['variant'] in source['candidate_variants']]
        # No ETF security is inferred from a current ticker: DBN date-effective maps only.
        mapping={}
        for v in variants:
            day=instant(v['anchor_utc']).date().isoformat()
            for symbol in ['SPY','QQQ']:
                ids={int(x['symbol']) for x in source['target_mappings'].get(symbol,[]) if str(x['start_date'])<=day<str(x['end_date'])}
                mapping[v['variant'],symbol]=ids
        target_ids=set().union(*mapping.values()) if mapping else set()
        specs=[]
        for v in variants:
            anchor=instant(v['anchor_utc']); lower=ns(anchor-timedelta(minutes=15))
            for symbol in ['SPY','QQQ']:
                for h in [0]+contract['endpoint_minutes']:
                    specs.append({'variant':v['variant'],'event_id':v['event_id'],'anchor_type':v['anchor_type'],'symbol':symbol,'horizon_minutes':h,'target_ns':ns(anchor+timedelta(minutes=h)),'lower_ns':lower,'ids':mapping[v['variant'],symbol]})
        states={}; counts=Counter(); publishers=set()
        for record in store:
            # Unrelated instruments' quote fields are never accessed.
            iid=int(record.instrument_id)
            if iid not in target_ids: continue
            if not isinstance(record,BBOMsg): raise RuntimeError('unexpected selected record schema')
            ts=int(record.ts_recv); pub=int(record.publisher_id)
            applicable=[(j,s) for j,s in enumerate(specs) if len(s['ids'])==1 and iid in s['ids'] and s['lower_ns']<=ts and (ts<s['target_ns'] if s['horizon_minutes']==0 else ts<=s['target_ns'])]
            if not applicable: continue
            level=record.levels[0]
            bid,ask,bs,az=map(int,(level.bid_px,level.ask_px,level.bid_sz,level.ask_sz))
            present=bid!=UNDEF_PRICE and ask!=UNDEF_PRICE and bs!=UNDEF_ORDER_SIZE and az!=UNDEF_ORDER_SIZE
            positive=present and min(bid,ask,bs,az)>0
            noncrossed=positive and ask>=bid
            signature=(bid,ask,bs,az,int(record.flags))
            counts['selected_records']+=1; publishers.add(pub)
            for j,s in applicable:
                key=(j,pub); previous=states.get(key)
                if previous is None or ts>previous['ts']:
                    states[key]={'ts':ts,'signature':signature,'ambiguous':False,'present':present,'positive':positive,'noncrossed':noncrossed,'locked':positive and ask==bid,'flags':int(record.flags)}
                elif ts==previous['ts'] and signature!=previous['signature']:
                    previous['ambiguous']=True
        for j,s in enumerate(specs):
            found=[state for (idx,pub),state in states.items() if idx==j]
            unique=len(found)==1 and len(s['ids'])==1
            state=found[0] if unique else None
            age=(s['target_ns']-state['ts'])/1e9 if state else None
            usable=state is not None and not state['ambiguous']
            rows.append({'event_id':s['event_id'],'variant':s['variant'],'anchor_type':s['anchor_type'],'dataset':source['header_dataset'],'file_path':str(p),
              'symbol':s['symbol'],'horizon_minutes':s['horizon_minutes'],'mapping_ids_count':len(s['ids']),'observed_publisher_streams':len(found),
              'observed_state':unique,'ambiguous_at_target':state['ambiguous'] if state else None,
              'target_in_header_interval':int(m.start)<=s['target_ns']<int(m.end),
              'baseline_lookback_in_header':int(m.start)<=s['lower_ns'] and (int(m.end)>=s['target_ns'] if s['horizon_minutes']==0 else int(m.end)>s['target_ns']),
              'present':state['present'] if usable else None,'positive':state['positive'] if usable else None,
              'noncrossed_snapshot':state['noncrossed'] if state and not state['ambiguous'] else None,
              'locked':state['locked'] if usable else None,'flags':state['flags'] if usable else None,
              'observed_interval_age_bin':'UNAVAILABLE' if age is None else ('LE_1S' if age<=1 else ('GT_1S_LE_60S' if age<=60 else 'GT_60S')),
              'continuous_live_quote_status':'NOT_CERTIFIED','actual_basket_support':'NOT_ASSESSED'})
        summaries.append({'path':str(p),'selected_records':counts['selected_records'],'publishers':sorted(publishers)})
    out={'status':'PARTIAL_FILE_CELL_DIAGNOSTIC' if skipped else 'FILE_CELL_DIAGNOSTIC_ONLY','candidate_file_count':len(manifest['files']),'processed_file_count':len(summaries),'skipped':skipped,'cross_file_merge':'NOT_PERFORMED; file-source cells are not unique event support','code_sha256':digest(Path(__file__)),'input_manifest_sha256':digest(root/'QUOTE_INPUT_MANIFEST.json'),
         'contract_sha256':digest(root/'DIAGNOSTIC_CONTRACT.json'),'release_sha256':digest(root/'DIAGNOSTIC_RELEASE.json'),
         'generated_at_utc':datetime.now(timezone.utc).isoformat(),'files':summaries,'rows':rows,
         'quote_levels_sizes_returns_exported':False,'missing_rows_are_not_missing_quotes':True}
    (root/'QUOTE_SUPPORT_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'files':len(summaries),'file_source_cells':len(rows),'skipped_files':len(skipped)}))

if __name__=='__main__': main()
