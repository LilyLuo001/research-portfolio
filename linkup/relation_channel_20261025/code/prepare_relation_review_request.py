#!/usr/bin/env python3
"""Prepare metadata-only permission request; never label or launch review.

Only two SHA-pinned existing metadata JSONL inputs are opened. Queue membership
uses their original masks/state/splits, never predictions, errors or text.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path

ITEM_SHA = '8227c3a784c330f18f14cb4e0a1f08d0a56a0ef59926a2d1b68a5c3ad21637ed'
STATE_SHA = 'b774fb5927c23fd22a9cd79aa7de683ec9f3ae979b749b6626ef4730aa8ea6f3'
SPLITS = ('train', 'final_previously_exposed', 'previous_holdout_reserved_not_final')
UNLABELED = 'unlabeled_candidate_no_negative'  # Exact existing producer enum.
AUTHORITY = 'AWAITING_EXPLICIT_NEW_RELATION_LABEL_AUTHORIZATION'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write(path, value, jsonl=False):
    with open(path, 'x', encoding='utf-8') as f:
        os.chmod(path, 0o600)
        if jsonl:
            for row in value:
                f.write(json.dumps(row, sort_keys=True) + '\n')
        else:
            json.dump(value, f, indent=2, sort_keys=True)
            f.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', required=True, help='Existing year inputs_v1 directory')
    p.add_argument('--output', required=True, help='New request directory')
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('actual scheduled SCNet Slurm job required')
    root, source = Path(a.output), Path(a.inputs)
    if root.exists():
        raise RuntimeError('output must be new')
    candidate_path = source / 'CANDIDATE_SUPERVISION_PRIVATE.jsonl'
    state_path = source / 'CONTEXT_STATES_PRIVATE.jsonl'
    if sha(candidate_path) != ITEM_SHA or sha(state_path) != STATE_SHA:
        raise RuntimeError('existing input SHA mismatch')
    states, ids, queues = {}, set(), defaultdict(list)
    counts, contexts = Counter(), defaultdict(set)
    for r in rows(state_path):
        c, s = r['context_sha256'], r['split']
        if c in states or s not in SPLITS:
            raise RuntimeError('duplicate context or invalid original split')
        eligible = r['inventory_eligible']
        masks_ok = all(r[k] in ('known', 'not_applicable') for k in ('year_family_status', 'object_family_status'))
        if not isinstance(eligible, bool) or eligible != masks_ok:
            raise RuntimeError('inventory eligibility disagrees with original masks')
        states[c] = (s, eligible)
    for r in rows(candidate_path):
        cid, c, s = r['candidate_id'], r['context_sha256'], r['split']
        if cid in ids or s not in SPLITS or c not in states or states[c][0] != s:
            raise RuntimeError('candidate identity/context/original split violation')
        ids.add(cid)
        counts[(s, 'all_existing_candidates')] += 1
        if r['supervision_state'] != UNLABELED:
            counts[(s, 'other_existing_supervision_states_not_requested')] += 1
            continue
        counts[(s, 'all_original_unlabeled')] += 1
        contexts[(s, 'all_original_unlabeled')].add(c)
        category = 'eligible_request' if states[c][1] else 'excluded_unaccepted_masks'
        counts[(s, category)] += 1
        contexts[(s, category)].add(c)
        if states[c][1]:
            queues[s].append(dict(candidate_id=cid, context_sha256=c, split=s,
                                 authority_status=AUTHORITY))
    for s in SPLITS:
        if counts[(s, 'all_original_unlabeled')] != counts[(s, 'eligible_request')] + counts[(s, 'excluded_unaccepted_masks')]:
            raise RuntimeError('unlabeled accounting failed')
    root.mkdir(parents=True, mode=0o700)
    outputs = {}
    for s in SPLITS:
        path = root / ('REQUEST_' + s + '_PRIVATE.jsonl')
        write(path, queues[s], jsonl=True)
        outputs[s] = dict(filename=path.name, sha256=sha(path), candidates=len(queues[s]))
    report = dict(authority_status=AUTHORITY, scheduler_job_id=os.environ['SLURM_JOB_ID'],
                  code_sha256=sha(__file__), candidate_input_sha256=ITEM_SHA, context_input_sha256=STATE_SHA,
                  exact_original_unlabeled_state=UNLABELED, queue_files=outputs,
                  counts_by_original_split={s: {k: counts[(s, k)] for k in ('all_existing_candidates', 'other_existing_supervision_states_not_requested', 'all_original_unlabeled', 'eligible_request', 'excluded_unaccepted_masks')} for s in SPLITS},
                  unique_contexts_by_original_split={s: {k: len(contexts[(s, k)]) for k in ('all_original_unlabeled', 'eligible_request', 'excluded_unaccepted_masks')} for s in SPLITS},
                  new_semantic_judgments=0, labels_created=0, negatives_inferred=0, review_launched=False,
                  sample_changed=False, batch070_queue=False,
                  purpose='Concrete existing-membership permission request only; no automatic review or training.')
    write(root / 'REVIEW_AUTHORIZATION_REQUEST_PUBLIC.json', report)


if __name__ == '__main__':
    main()
