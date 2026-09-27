"""Bounded cross-region extraction check. Standard library only; no gold labels."""
import argparse
import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one(row):
    from requirement_candidates import extract
    result = extract(row['DESCRIPTION'])
    text = result['normalized_text']
    for e in result['evidence']:
        assert 0 <= e['start'] <= e['end'] <= len(text)
        assert text[e['snippet_start']:e['snippet_end']] == e['snippet']
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return {'JOB_HASH': row['JOB_HASH'], 'candidate_sha256': hashlib.sha256(canonical.encode()).hexdigest(),
            'parse_errors': result['errors']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    identity = {'input_sha256': sha(a.input), 'parser_sha256': sha(Path(__file__).with_name('requirement_candidates.py')),
                'runner_sha256': sha(__file__)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = [json.loads(s) for s in Path(a.input).read_text().splitlines()]
    assert 0 < len(rows) <= 30000
    assert len({r['JOB_HASH'] for r in rows}) == len(rows)
    workers = min(a.workers, int(os.environ.get('SLURM_CPUS_PER_TASK', a.workers)))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, rows, chunksize=16))
    assert len(results) == len(rows)
    tmp = out / 'candidate_hashes.jsonl.tmp'
    tmp.write_text(''.join(json.dumps(r, sort_keys=True)+'\n' for r in results))
    tmp.replace(out / 'candidate_hashes.jsonl')
    errors = sum(bool(r['parse_errors']) for r in results)
    report = dict(identity, rows=len(rows), parse_error_rows=errors,
                  status='PASS' if errors == 0 else 'FAIL', semantic_accuracy_estimated=False,
                  output_sha256=sha(out / 'candidate_hashes.jsonl'))
    (out / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    if errors:
        raise RuntimeError('Parser errors in portability sample')
    (out / 'COMPLETE').write_text(sha(out / 'report.json')+'\n')


if __name__ == '__main__':
    main()
