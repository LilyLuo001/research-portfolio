"""Report durable outputs, not inferred background execution or percentage accuracy."""
import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def load(path):
    return [json.loads(s) for s in path.read_text().splitlines()]

def main():
    staged=json.loads((ROOT/'STAGING_RECEIPT.json').read_text())
    prior=ROOT.parent/'batch002_execution/CUMULATIVE_CHECKPOINT_RECEIPT.json'
    completed_before=json.loads(prior.read_text())['counts']['completed_unique_exact_texts']
    result=[];new_final=0;raw_total=0
    for batch in staged['batches']:
        p=ROOT/'private'/batch['batch'];groups=[]
        for group in sorted(p.glob('group_*')):
            pred=group/'PREDICTIONS_FIRST_RAW_PRIVATE.jsonl'
            n=0;state='no_durable_primary_output'
            if pred.exists():
                try:
                    n=len(load(pred));expected=len(load(group/'SOURCE_PRIVATE.jsonl'))
                    state='full_row_count_not_semantic_acceptance' if n==expected else 'partial_row_count'
                except (ValueError,OSError):
                    state='unreadable_output'
            groups.append({'group':group.name,'raw_rows':n,'state':state})
        raw=sum(g['raw_rows'] for g in groups);raw_total+=raw
        final=p/'FINAL_CANDIDATES_PRIVATE.jsonl'
        final_n=len(load(final)) if final.exists() else 0
        accepted=ROOT/'receipts'/batch['batch']/'ROOT_ACCEPTANCE.json'
        if final_n and accepted.exists():
            assert final_n==batch['source_count']
            new_final+=final_n
        else:
            final_n=0
        if raw or final_n or batch['batch'] in ('batch003','batch004'):
            result.append({'batch':batch['batch'],'staged_rows':batch['source_count'],'primary_raw_rows':raw,'root_accepted_rows':final_n,'groups':groups})
    out={'as_of_utc':datetime.now(timezone.utc).isoformat(),'observed_batches':result,'previously_completed_unique':completed_before,'new_root_accepted_unique':new_final,'cumulative_root_accepted_unique':completed_before+new_final,'raw_primary_rows_this_run':raw_total,'remaining_not_root_accepted':staged['remaining_unique_texts']-new_final,'limitation':'Durable file progress only. This is not a live worker/cluster scheduler state; staged files do not mean inference is running. Raw rows do not mean accepted or accurate measurements.'}
    path=ROOT/'PROGRESS.json';path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('observed_batches','limitation')}))

if __name__=='__main__':
    main()
