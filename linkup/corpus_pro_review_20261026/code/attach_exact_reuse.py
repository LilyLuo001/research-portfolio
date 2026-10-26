#!/usr/bin/env python3
"""Bind existing full-input reference judgments to new ads; never infer labels."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from checkpoint_reviews import has_unknown_outcome, write_json_new, write_jsonl_new
from validate_reviews import read_jsonl, sha256_file


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--batch-dir', type=Path, required=True)
    p.add_argument('--reference-checkpoints', type=Path, nargs='+', required=True)
    p.add_argument('--output-root', type=Path, required=True)
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('scheduled compute required')
    prep = json.loads((a.batch_dir/'public/PACKET_PREPARATION_PUBLIC.json').read_text())
    bindings_path = a.batch_dir/'private/REUSE_AD_BINDINGS_PRIVATE.jsonl'
    if sha256_file(bindings_path) != prep['output_sha256']['reuse_ad_bindings_private']:
        raise RuntimeError('prepared reuse bindings changed')
    references, sources, all_old_keys = {}, [], set()
    for checkpoint in a.reference_checkpoints:
        receipt = checkpoint/'public/CHECKPOINT_RECEIPT_PUBLIC.json'
        if not receipt.is_file():
            receipt = checkpoint/'public/MERGED_RECEIPT_PUBLIC.json'
        meta = json.loads(receipt.read_text())
        if meta['status'] != 'complete':
            raise RuntimeError('reference checkpoint incomplete')
        data = checkpoint/'private/AD_LEVEL_PRO_REFERENCE_PRIVATE.jsonl'
        if sha256_file(data) != meta['outputs']['ad_level_reference_sha256']:
            raise RuntimeError('reference content changed')
        index = len(sources)
        sources.append({'receipt': str(receipt), 'receipt_sha256': sha256_file(receipt),
                        'ad_reference_sha256': sha256_file(data)})
        for row in read_jsonl(data):
            context = row['context_sha256']
            signature = {k: v for k, v in row.items() if k not in ('canonical_key', 'canonical_keys')}
            if context in references and references[context][1] != signature:
                raise RuntimeError('conflicting completed reference judgments')
            references.setdefault(context, (index, signature))
            all_old_keys.add(tuple(row['canonical_key']))
    accepted, pending, seen = [], [], set()
    for binding in read_jsonl(bindings_path):
        key = tuple(binding['canonical_key'])
        if key in seen or key in all_old_keys:
            raise RuntimeError('duplicate or previously completed reuse ad key')
        seen.add(key)
        context = binding['context_sha256']
        if context not in references:
            pending.append({**binding, 'status': 'pending_supported_reference_payload'})
            continue
        source_index, reference = references[context]
        accepted.append({**reference, 'canonical_key': list(key),
                         'exact_reuse_provenance': {'source_receipt_index': source_index,
                                                   'new_model_reading': False,
                                                   'complete_normalized_input_sha256': context}})
    a.output_root.mkdir(parents=True, exist_ok=False, mode=0o700)
    private, public = a.output_root/'private', a.output_root/'public'
    private.mkdir(mode=0o700); public.mkdir()
    target, unresolved = private/'AD_LEVEL_REUSED_REFERENCE_PRIVATE.jsonl', private/'PENDING_REUSE_PRIVATE.jsonl'
    write_jsonl_new(target, accepted); write_jsonl_new(unresolved, pending)
    receipt = {'status': 'complete' if not pending else 'pending_references',
               'slurm_job_id': os.environ['SLURM_JOB_ID'], 'new_semantic_readings': 0,
               'counts': {'prepared_bindings': len(seen), 'attached_ad_keys': len(accepted),
                          'pending_ad_keys': len(pending),
                          'attached_ad_keys_with_unknown': sum(has_unknown_outcome(r) for r in accepted)},
               'source_checkpoints': sources, 'bindings_sha256': sha256_file(bindings_path),
               'outputs': {'attached_sha256': sha256_file(target), 'pending_sha256': sha256_file(unresolved)},
               'code_sha256': sha256_file(Path(__file__)),
               'claim': 'Exact complete-input reuse only; original unknown/partial retained. No new judgment or semantic quality claim.'}
    write_json_new(public/'EXACT_REUSE_RECEIPT_PUBLIC.json', receipt)
    print(json.dumps(receipt['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
