"""Validate staged batch002 against immutable sources and reproduce mappings/audit pack.
Private alias IDs and staged source packs are required inputs, not inferred model labels.
"""
import hashlib,json,random,datetime
from pathlib import Path
P=Path(__file__).resolve().parent
B=P/'private/batch002'
PREV=P.parent/'production_standard_20261008'
def load(p): return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,indent=2)+'\n')
def jsonl(p,rs): p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rs))
def main():
    sources=load(B/'COMBINED_SOURCE_PRIVATE.jsonl')
    queue=load(PREV/'private/full_queue/UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl')
    done={r['source_text_sha256'] for r in load(PREV/'private/batch001/FINAL_CANDIDATES_PRIVATE.jsonl')}
    selected=sorted((r for r in queue if r['exact_text_sha256'] not in done),key=lambda r:r['exact_text_sha256'])[:128]
    actual=[hashlib.sha256(r['original_text'].encode()).hexdigest() for r in sources]
    assert actual==[r['exact_text_sha256'] for r in selected]
    assert len(sources)==len(set(actual))==128 and not(set(actual)&done)
    assert len({r['record_id'] for r in sources})==128
    for g in range(4):
        gd=B/f'group_{g+1:02d}'
        grouped=[]
        for k in range(4): grouped+=load(gd/f'blocks/block_{k+1:02d}_of_04_PRIVATE.jsonl')
        assert grouped==sources[g*32:(g+1)*32]
        order=json.loads((gd/'ORDER_PRIVATE.json').read_text())
        ids=[r['record_id'] for r in grouped]
        if order!=ids:
            assert order==actual[g*32:(g+1)*32], 'Unrecognized sidecar mismatch'
            dump(gd/'ORDER_SOURCE_HASHES_PRIVATE.json',order)
            dump(gd/'ORDER_PRIVATE.json',ids)
        assert json.loads((gd/'ORDER_PRIVATE.json').read_text())==ids
    mapping={}
    for r in load(PREV/'private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl'):
        mapping.setdefault(r['exact_text_sha256'],[]).append(r)
    old=B/'UNBLIND_MANIFEST_PRIVATE.jsonl'
    if not (B/'UNBLIND_INITIAL_PARTIAL_METADATA_PRIVATE.jsonl').exists():
        (B/'UNBLIND_INITIAL_PARTIAL_METADATA_PRIVATE.jsonl').write_bytes(old.read_bytes())
    manifest=[]
    for i,(r,h) in enumerate(zip(sources,actual),1):
        members=mapping[h]
        manifest.append({'record_id':r['record_id'],'processing_position_1based':i,'exact_text_sha256':h,'represented_fixed_sample_rows':len(members),'represented_rows':members})
    jsonl(old,manifest)
    audit=json.loads((B/'AUDIT_SELECTION_PRIVATE.json').read_text())
    assert audit['indices_0based']==sorted(random.Random(audit['seed']).sample(range(len(sources)),16))
    assert audit['sha256']==[actual[i] for i in audit['indices_0based']]
    ad=B/'audit';ad.mkdir(exist_ok=True)
    audited=[sources[i] for i in audit['indices_0based']]
    jsonl(ad/'SOURCE16_PRIVATE.jsonl',audited)
    dump(ad/'ORDER_PRIVATE.json',[r['record_id'] for r in audited])
    for k in range(4):jsonl(ad/f'block_{k+1:02d}_of_04_PRIVATE.jsonl',audited[k*4:(k+1)*4])
    prior=json.loads((P/'BATCH002_EXECUTION_RECEIPT.json').read_text())
    prior.update({'validated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actual_processing_order':'ascending exact-text SHA among not-yet-completed texts, first128; NOT original randomized queue order','processing_order_amendment':'Root accepts prepared SHA-order batch before label inspection to avoid discarding ongoing work; inferential sample unchanged.','private_alias_ids':'Frozen in staged sources; verified unique; not claimed original queue IDs.','source_metadata':'Full authoritative canonical keys, cells and ALL original weights restored in unblind manifest; initial partial metadata retained privately.','represented_original_rows':sum(r['represented_fixed_sample_rows'] for r in manifest),'audit_algorithm':'Python random.Random(seed).sample(range(128),16), then sorted','audit_seed':audit['seed'],'source_character_counts':{'total':sum(len(r['original_text']) for r in sources),'groups':[sum(len(r['original_text']) for r in sources[k*32:(k+1)*32]) for k in range(4)]}})
    prior['private_artifact_sha256']={f:sha(B/f) for f in ['COMBINED_SOURCE_PRIVATE.jsonl','UNBLIND_MANIFEST_PRIVATE.jsonl','AUDIT_SELECTION_PRIVATE.json','audit/SOURCE16_PRIVATE.jsonl']}
    dump(P/'BATCH002_EXECUTION_RECEIPT.json',prior)
    print(json.dumps({'validated_sources':len(sources),'represented_ad_rows':prior['represented_original_rows'],'audit_rows':len(audited),'full_metadata_restored':True}))
if __name__=='__main__': main()
