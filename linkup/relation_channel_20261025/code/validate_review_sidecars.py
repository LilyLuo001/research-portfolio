#!/usr/bin/env python3
"""Scheduled structural/evidence-offset QA only, never semantic acceptance.

Accept one complete packet sidecar or all packets. No missing/duplicate/extra
candidate permitted in the selected immutable packet membership. Never train.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from prepare_pro_packets import OBJECTS, checked, rows, sha, write


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('packet-root', 'manifest-sha256', 'sidecar', 'sidecar-sha256', 'packet-id', 'output'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('actual scheduled SCNet job required')
    root, output = Path(a.packet_root), Path(a.output)
    if output.exists():
        raise RuntimeError('create-only output exists')
    manifest = json.loads(checked(root / 'PACKET_MANIFEST_PUBLIC.json', a.manifest_sha256).read_text())
    checked(root / 'REVIEW_PROTOCOL.json', manifest['protocol_sha256'])
    selected = {p['packet_id'] for p in manifest['packets'] if a.packet_id == 'all' or p['packet_id'] == a.packet_id}
    if not selected:
        raise RuntimeError('unknown packet selection')
    for packet in manifest['packets']:
        if packet['packet_id'] in selected:
            checked(root / packet['filename'], packet['sha256'])
    mapping, seen_all = {}, set()
    for r in rows(checked(root / 'CANDIDATE_PACKET_MAP_PRIVATE.jsonl', manifest['mapping_sha256'])):
        cid = r['candidate_id']
        if cid in seen_all:
            raise RuntimeError('duplicate immutable mapping candidate')
        seen_all.add(cid)
        if r['packet_id'] in selected:
            mapping[cid] = r
    if len(seen_all) != manifest['total_candidates']:
        raise RuntimeError('immutable map membership cardinality violation')
    expected_n = sum(p['candidates'] for p in manifest['packets'] if p['packet_id'] in selected)
    if len(mapping) != expected_n:
        raise RuntimeError('selected packet membership cardinality violation')
    texts = {}

    def evidence(items, original, required=False, must_contain_numeric=False):
        if not isinstance(items, list) or required and not items:
            raise RuntimeError('nonempty evidence list required')
        text = texts[original['context_sha256']]
        contains = False
        for e in items:
            if not isinstance(e, dict):
                raise RuntimeError('evidence must be an offset/quote object')
            start, end, quote = e.get('start'), e.get('end'), e.get('quote')
            if type(start) is not int or type(end) is not int or not isinstance(quote, str) or not quote.strip():
                raise RuntimeError('nonempty exact evidence with integer offsets required')
            if not 0 <= start < end <= len(text) or text[start:end] != quote:
                raise RuntimeError('evidence does not equal original text at offsets')
            contains |= start <= original['entity_start'] and original['entity_end'] <= end
        if must_contain_numeric and not contains:
            raise RuntimeError('relation evidence must contain this original numeric mention')

    accepted, seen, counts = [], set(), Counter()
    for r in rows(checked(Path(a.sidecar), a.sidecar_sha256)):
        cid = r.get('candidate_id')
        if cid not in mapping or cid in seen:
            raise RuntimeError('duplicate or out-of-packet review candidate')
        original = mapping[cid]
        c, s = original['context_sha256'], original['split']
        if (r.get('context_sha256'), r.get('split')) != (c, s):
            raise RuntimeError('original context or split changed')
        if c not in texts:
            path = root / 'full_contexts' / (c + '.txt')
            text = checked(path, c).read_bytes().decode('utf-8')
            if hashlib.sha256(text.encode()).hexdigest() != c:
                raise RuntimeError('original full text changed during decode')
            texts[c] = text
        status, relations = r.get('review_status'), r.get('relations')
        if not isinstance(relations, list):
            raise RuntimeError('relations list required; never inferred from absence')
        if status == 'resolved':
            if not relations:
                raise RuntimeError('resolved requires explicit supported object relations')
            for relation in relations:
                if not isinstance(relation, dict) or relation.get('object') not in OBJECTS:
                    raise RuntimeError('only unchanged original object classes allowed')
                evidence(relation.get('evidence'), original, required=True, must_contain_numeric=True)
        elif status == 'explicit_non_experience':
            if relations or not isinstance(r.get('reason'), str) or not r['reason'].strip():
                raise RuntimeError('explicit non-experience requires no object relations and a reason')
            evidence(r.get('evidence'), original, required=True, must_contain_numeric=True)
        elif status == 'unknown':
            if relations or not isinstance(r.get('unknown_reason'), str) or not r['unknown_reason'].strip():
                raise RuntimeError('unknown requires no forced relations and an insufficiency reason')
            evidence(r.get('evidence', []), original)
        else:
            raise RuntimeError('invalid review status')
        if status == 'resolved' and 'evidence' in r:
            evidence(r['evidence'], original)
        seen.add(cid)
        counts[(s, status)] += 1
        accepted.append(r)  # Preserve exact submitted judgments; no relabeling.
    if seen != set(mapping):
        raise RuntimeError('selected packet sidecar is incomplete')
    output.mkdir(parents=True, mode=0o700)
    path = output / 'STRUCTURALLY_VALIDATED_REVIEW_PRIVATE.jsonl'
    write(path, accepted, True)
    write(output / 'SIDECAR_VALIDATION_PUBLIC.json', dict(scheduler_job_id=os.environ['SLURM_JOB_ID'],
        code_sha256=sha(__file__), packet_manifest_sha256=a.manifest_sha256,
        sidecar_input_sha256=a.sidecar_sha256, validated_sidecar_sha256=sha(path),
        selected_packets=sorted(selected), candidates=len(accepted),
        counts=[dict(split=s, review_status=status, candidates=n) for (s, status), n in sorted(counts.items())],
        structural_checks_passed=True, semantic_quality_accepted=False, training_run=False,
        negatives_inferred=0, original_reference_labels_modified=False,
        boundary='Identity, original splits, unchanged object enums, exact evidence offsets and completeness only. Explicit_non_experience is a Pro agent judgment, never an automatically usable training negative.'))


if __name__ == '__main__':
    main()
