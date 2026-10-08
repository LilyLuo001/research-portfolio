"""Freeze disjoint remaining execution batches without changing the fixed sample."""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent / 'batch002_execution/private/cumulative_checkpoint'
STANDARD = ROOT.parent / 'production_standard_20261008'

def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]

def write(path, value, lines=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in value) if lines else json.dumps(value, ensure_ascii=False, indent=2)+'\n'
    if path.exists():
        assert path.read_text() == text, f'Existing frozen artifact differs: {path.name}'
    else:
        path.write_text(text)
        path.chmod(0o600)

def main():
    remaining = read(PRIOR/'REMAINING_UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl')
    completed = {r['source_text_sha256'] for r in read(PRIOR/'COMPLETED_SOURCE_HASH_LEDGER_PRIVATE.jsonl')}
    assert len({r['exact_text_sha256'] for r in remaining}) == len(remaining)
    assert not completed.intersection(r['exact_text_sha256'] for r in remaining)
    metadata = {}
    for r in read(STANDARD/'private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl'):
        metadata.setdefault(r['exact_text_sha256'], []).append(r)
    batches = []
    for start in range(0, len(remaining), 128):
        num = 3+start//128
        name = f'batch{num:03d}'
        rows = remaining[start:start+128]
        src = [{'record_id':r['queue_record_id'], 'original_text':r['original_text']} for r in rows]
        assert all(hashlib.sha256(s['original_text'].encode()).hexdigest()==r['exact_text_sha256'] for s,r in zip(src,rows))
        p = ROOT/'private'/name
        write(p/'SOURCE_PRIVATE.jsonl', src, True)
        write(p/'ORDER_PRIVATE.json', [r['record_id'] for r in src])
        write(p/'UNBLIND_PRIVATE.jsonl', [{'record_id':s['record_id'], 'source_text_sha256':r['exact_text_sha256'], 'represented_rows':metadata[r['exact_text_sha256']]} for s,r in zip(src,rows)], True)
        for g in range(0,len(src),32):
            group = p/f'group_{g//32+1:02d}'
            subset = src[g:g+32]
            write(group/'SOURCE_PRIVATE.jsonl', subset, True)
            write(group/'ORDER_PRIVATE.json', [r['record_id'] for r in subset])
            for b in range(0,len(subset),8):
                write(group/f'block_{b//8+1:02d}_PRIVATE.jsonl',subset[b:b+8],True)
        seed = f'D45-{name}-audit-v1'
        indices = sorted(random.Random(seed).sample(range(len(src)), min(16,len(src))))
        audit = [src[i] for i in indices]
        write(p/'audit/SELECTION_PRIVATE.json', {'seed':seed,'indices_0based':indices})
        write(p/'audit/SOURCE_PRIVATE.jsonl', audit,True)
        write(p/'audit/ORDER_PRIVATE.json',[r['record_id'] for r in audit])
        for b in range(0,len(audit),4):
            write(p/f'audit/block_{b//4+1:02d}_PRIVATE.jsonl',audit[b:b+4],True)
        batches.append({'batch':name, 'source_count':len(src),'represented_ad_rows':sum(len(metadata[r['exact_text_sha256']]) for r in rows),'input_characters':sum(len(s['original_text']) for s in src),'audit_count':len(audit),'status_at_staging':'queued_not_inferred'})
    receipt={'status':'all_remaining_execution_inputs_frozen_not_all_started','processing_order':'original queue order excluding previously finalized exact-text hashes','batches':batches,'remaining_unique_texts':len(remaining),'remaining_ad_rows':sum(b['represented_ad_rows'] for b in batches),'completed_before_this_run':len(completed),'prompt_sha256':hashlib.sha256((STANDARD/'EXTRACTION_PROMPT.md').read_bytes()).hexdigest(),'source_queue_sha256':hashlib.sha256((PRIOR/'REMAINING_UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl').read_bytes()).hexdigest(),'privacy':'No ads, evidence, record identifiers or weights in public receipt'}
    write(ROOT/'STAGING_RECEIPT.json',receipt)
    print(json.dumps({'batches':len(batches),'unique_texts':len(remaining),'original_ads':receipt['remaining_ad_rows']}))

if __name__=='__main__':
    main()
