"""Recompute Batch001 summaries from actual private outputs; no hardcoded scores."""
import hashlib
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent
BATCH = ROOT / 'private/batch001'
def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]
def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')
def main_value(finding):
    if finding['state'] == 'unknown': return None
    mentions = finding['mentions']
    if any(m['condition_mode']=='prior_experience' and m['strength']=='required' and m['qualification_scope']=='unconditional' for m in mentions): return 1
    if any('unknown' in (m['condition_mode'],m['strength'],m['qualification_scope']) for m in mentions): return None
    return 0
def keyed(source, predictions, order):
    src, pred = rows(source), rows(predictions)
    ids = json.loads(order.read_text())
    assert len(src)==len(pred)==len(ids)
    assert ids==[r['record_id'] for r in src] and len(set(ids))==len(ids)
    return dict(zip(ids,pred)),dict(zip(ids,src))
def main():
    aggregate=json.loads((ROOT/'BATCH001_FINAL_AGGREGATE.json').read_text())
    primary,source=keyed(BATCH/'LABEL_PACK_PRIVATE.jsonl',BATCH/'primary/PREDICTIONS_RAW_PRIVATE.jsonl',BATCH/'primary/ORDER_PRIVATE.json')
    audit,audit_source=keyed(BATCH/'audit/SOURCE6_PRIVATE.jsonl',BATCH/'audit/PREDICTIONS_RAW_PRIVATE.jsonl',BATCH/'audit/ORDER_PRIVATE.json')
    agree,joint=Counter(),0
    for rid,prediction in audit.items():
        assert audit_source[rid]['original_text']==source[rid]['original_text']
        left={f['object']:main_value(f) for f in primary[rid]['findings']}
        right={f['object']:main_value(f) for f in prediction['findings']}
        assert left.keys()==right.keys()
        for obj in left: agree[obj]+=int(left[obj]==right[obj])
        joint+=int(left==right)
    audit_summary={'rows':len(audit),'agreement_by_object':dict(agree),'joint':joint,'raw_semantic_comparison_separate_from_validation_errors':True,'accuracy_claim':False,'blinding':'Primary-label blind; reviewer previously prepared source pack and may have seen arm metadata.'}
    out={'eligible_rows':aggregate['eligible_rows'],'eligible_object_fields':aggregate['eligible_object_fields'],'objects':{}}
    for name,obj in aggregate['objects'].items():
        out['objects'][name]={'raw_main_presence':obj['raw_main_counts'],'final_main_presence':obj['final_main_counts'],'raw_outcome_status':obj['raw_outcome_status_counts'],'final_outcome_status':obj['final_outcome_status_counts']}
    out['independent_audit6']=audit_summary
    write(ROOT/'BATCH001_AUDIT_SUMMARY.json',out)
    final=rows(BATCH/'FINAL_CANDIDATES_PRIVATE.jsonl'); manifest=rows(BATCH/'UNBLIND_MANIFEST_PRIVATE.jsonl')
    queue=rows(ROOT/'private/full_queue/UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl')
    assert len(final)==len(manifest)==len(source)
    completed={r['source_text_sha256'] for r in final}
    assert len(completed)==len(final) and completed=={r['exact_text_sha256'] for r in manifest}
    progress={'done':len(completed),'remaining':len(queue)-len(completed),'completed_batch_represented_original_rows':sum(r['represented_fixed_sample_rows'] for r in manifest),'represented_original_sample_rows':len(rows(ROOT/'private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl')),'immutable_unique_exact_text_queue':len(queue),'status':'bounded_batch_complete_no_unattended_job_claim'}
    write(ROOT/'PRODUCTION_PROGRESS.json',progress)
    qa=json.loads((ROOT/'QA_FINAL_RELEASE.json').read_text());qa['independent_audit6']=audit_summary
    qa['final_field_status_counts']=dict(Counter(f['outcome_status'] for r in final for f in r['objects']))
    qa['queue']=progress
    qa['raw_outputs_byte_unchanged']='Exported-bound raw unchanged; primary had two logged quote-encoding repairs before binding. First-output bytes were not independently captured.'
    for r in final:
        assert hashlib.sha256(r['raw_output'].encode()).hexdigest()==r['raw_output_sha256']
        assert r['source_text_sha256']==hashlib.sha256(source[r['record_id']]['original_text'].encode()).hexdigest()
    write(ROOT/'QA_FINAL_RELEASE.json',qa)
if __name__=='__main__': main()
