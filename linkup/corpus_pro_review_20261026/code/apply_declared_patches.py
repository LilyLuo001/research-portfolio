#!/usr/bin/env python3
"""Apply explicitly authored private corrections, preserving original reviews."""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
from checkpoint_reviews import write_json_new, write_jsonl_new
from validate_reviews import read_jsonl, sha256_file


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--batch-dir', type=Path, required=True)
    p.add_argument('--reviews-dir', type=Path, required=True)
    p.add_argument('--patches', type=Path, nargs='+', required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('scheduled compute required')
    prep = json.loads((a.batch_dir/'public/PACKET_PREPARATION_PUBLIC.json').read_text())
    originals, effective = {}, {}
    for packet in prep['packet_files']:
        name = a.batch_dir.name+'_'+Path(packet['name']).stem+'_PRIMARY.jsonl'
        source = a.reviews_dir/name
        records = read_jsonl(source)
        if len(records) != packet['records']:
            raise RuntimeError('incomplete primary '+name)
        originals[name] = {'sha256': sha256_file(source), 'rows': records}
        effective[name] = copy.deepcopy(records)
    applied = []
    for path in a.patches:
        for patch in read_jsonl(path):
            name = patch['primary_file']
            if name not in originals or originals[name]['sha256'] != patch['primary_sha256']:
                raise RuntimeError('original primary SHA mismatch')
            matches = [r for r in effective[name] if r['record_id'] == patch['record_id']]
            if len(matches) != 1 or matches[0]['context_sha256'] != patch['context_sha256']:
                raise RuntimeError('correction identity mismatch')
            parts = patch['pointer'].split('/')[1:]
            if not parts or parts[0] in ('record_id', 'context_sha256'):
                raise RuntimeError('protected correction pointer')
            value = matches[0]
            for part in parts[:-1]:
                key = part.replace('~1', '/').replace('~0', '~')
                value = value[int(key)] if isinstance(value, list) else value[key]
            key = parts[-1].replace('~1', '/').replace('~0', '~')
            key = int(key) if isinstance(value, list) else key
            if value[key] != patch['old']:
                raise RuntimeError('correction old-value mismatch')
            value[key] = patch['new']
            applied.append(patch)
    a.output_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, records in effective.items():
        write_jsonl_new(a.output_dir/name, records)
    provenance = {'job': os.environ['SLURM_JOB_ID'],
                  'original_files': {name: v['sha256'] for name, v in originals.items()},
                  'patch_sources': [{'path': str(p), 'sha256': sha256_file(p)} for p in a.patches],
                  'applied': applied,
                  'policy': 'Explicit old/new corrections only; original authoring unchanged; not new review.'}
    write_json_new(a.output_dir/'PATCH_PROVENANCE_PRIVATE.json', provenance)
    print(json.dumps({'files': len(effective), 'explicit_patch_operations': len(applied)}))


if __name__ == '__main__':
    main()
