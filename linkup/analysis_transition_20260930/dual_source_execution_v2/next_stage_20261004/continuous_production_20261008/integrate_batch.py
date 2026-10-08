"""Join completed reader blocks using the frozen exporter and audit comparison.

This wrapper performs no inference, semantic repair or automatic adjudication.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'production_standard_20261008'))
sys.path.insert(0,str(ROOT.parent/'batch002_execution'))
import export_candidates as exporter
import process_batch002 as common

def read(path):
    return exporter.strict_jsonl(path, path.name)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path,value,lines=False):
    text=exporter.serialize_jsonl(value) if lines else json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    exporter.atomic_write(path,text,0o600 if 'private' in path.parts else 0o644)

def export(src,pred,order,destination,public):
    sources=read(src)
    wrapped=exporter.adapt_reader_outputs(sources,pred,order)
    rows=exporter.export_rows(sources,wrapped)
    dump(destination/'WRAPPED_PRIVATE.jsonl',wrapped,True)
    dump(destination/'CANDIDATES_PRIVATE.jsonl',rows,True)
    receipt=exporter.build_public_receipt(rows,digest(src),digest(pred))
    dump(public,receipt)
    return sources,rows,receipt

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('batch')
    args=parser.parse_args()
    if not __import__('re').fullmatch(r'batch\d{3}',args.batch):
        parser.error('batch must match batchNNN')
    p=ROOT/'private'/args.batch
    public=ROOT/'receipts'/args.batch
    sources=read(p/'SOURCE_PRIVATE.jsonl')
    staged=json.loads((ROOT/'STAGING_RECEIPT.json').read_text())
    expected=next(b for b in staged['batches'] if b['batch']==args.batch)
    assert len(sources)==expected['source_count']
    bindings=read(p/'UNBLIND_PRIVATE.jsonl')
    assert len(bindings)==len(sources)
    assert all(s['record_id']==m['record_id'] and hashlib.sha256(s['original_text'].encode()).hexdigest()==m['source_text_sha256'] for s,m in zip(sources,bindings))
    predictions=[];group_sources=[];provenance=[]
    for group in sorted(p.glob('group_*')):
        original=read(group/'SOURCE_PRIVATE.jsonl')
        common.verify_order_and_hashes(group,original)
        chosen,pro=common.select_predictions(group,original)
        predictions.extend(chosen);group_sources.extend(original)
        provenance.append({'group':group.name,**pro})
    assert group_sources==sources and len(predictions)==len(sources)
    selected=p/'SELECTED_PREDICTIONS_PRIVATE.jsonl'
    exporter.atomic_write(selected,''.join(line+'\n' for line in predictions),0o600)
    _,rows,receipt=export(p/'SOURCE_PRIVATE.jsonl',selected,p/'ORDER_PRIVATE.json',p/'primary',public/'PRIMARY.json')
    risk,details=common.risk_summary(sources,predictions,rows)
    comparison=[];audit_status='not_yet_run'
    ad=p/'audit'
    if (ad/'PREDICTIONS_FIRST_RAW_PRIVATE.jsonl').exists():
        audit_sources=read(ad/'SOURCE_PRIVATE.jsonl')
        audit_lines,ap=common.select_predictions(ad,audit_sources)
        audit_selected=ad/'SELECTED_PREDICTIONS_PRIVATE.jsonl'
        exporter.atomic_write(audit_selected,''.join(line+'\n' for line in audit_lines),0o600)
        _,arows,areceipt=export(ad/'SOURCE_PRIVATE.jsonl',audit_selected,ad/'ORDER_PRIVATE.json',ad/'export',public/'AUDIT.json')
        agreement,comparison=common.compare_audit(sources,rows,audit_sources,arows)
        dump(public/'AUDIT_COMPARISON.json',agreement)
        dump(ad/'PROVENANCE_PRIVATE.json',ap)
        audit_status='integrated_not_ground_truth'
    targets=common.targeted_candidates(details,comparison,[])
    dump(p/'PROVENANCE_PRIVATE.json',provenance)
    dump(p/'RISKS_PRIVATE.json',details)
    dump(p/'AUDIT_COMPARISONS_PRIVATE.json',comparison)
    dump(p/'TARGETED_REVIEW_PRIVATE.json',targets)
    dump(public/'INTEGRATION.json',{'batch':args.batch,'rows':len(rows),'audit_status':audit_status,'root_adjudication_status':'pending','targeted_cases':len(targets),'risk_counts':risk,'first_model_outputs_unchanged':True,'prompt_unchanged':True,'source_sha256':digest(p/'SOURCE_PRIVATE.jsonl'),'candidate_sha256':digest(p/'primary/CANDIDATES_PRIVATE.jsonl')})
    print(json.dumps({'batch':args.batch,'rows':len(rows),'audit_status':audit_status,'targeted_cases':len(targets)}))

if __name__=='__main__':
    main()
