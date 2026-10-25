#!/usr/bin/env python3
"""Scheduled, read-only packet preparation for the authorized 2736 candidates.

Numeric duration mention -> applicant experience object relation, not technology
role or responsibility subject annotation. No previous labels/predictions shown.
"""
import argparse
from collections import Counter, OrderedDict
import hashlib
import json
import os
from pathlib import Path

SPLITS = ('train', 'final_previously_exposed', 'previous_holdout_reserved_not_final')
QUEUES = dict(zip(SPLITS, (
    '22c265ffe0daea6a28ae6a72821fc2600f6f42aaa17b6dfff9586f9d2e756de4',
    '27e033003a6455bf91e93a82ed3b0ac9d1248db5969a6831712f2ef0d629a63c',
    '6a25444c32c63f5b7d5bb8b2b969f83ff9de5d8b0eaa5a7313208e2b36705174')))
CANDIDATES_SHA = 'f331e446648b0842fa04860efa170ba58eb9eba0a01444623b83fe7af2f11ac7'
STATES_SHA = 'b774fb5927c23fd22a9cd79aa7de683ec9f3ae979b749b6626ef4730aa8ea6f3'
TEXTS_SHA = 'e76b1cc9b8ede15ba11fcba8fb026517a8c18b2c9bc69139c254fb5d6e4039ed'
OBJECTS = ('general_work', 'industry_domain', 'occupation_task', 'tool_specific')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def checked(path, digest):
    if sha(path) != digest:
        raise RuntimeError('input digest mismatch: ' + str(path))
    return path


def rows(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write(path, value, lines=False):
    with open(path, 'x', encoding='utf-8') as f:
        os.chmod(path, 0o600)
        if lines:
            for row in value:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
        else:
            json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write('\n')


def intervals(text, candidates):
    spans = []
    for r in candidates:
        start = min(r['entity_start'], r['clause_start']) if r['clause_start'] is not None else r['entity_start']
        end = max(r['entity_end'], r['clause_end']) if r['clause_end'] is not None else r['entity_end']
        # Display-only neighboring text, never new candidate extraction or labels.
        low, high = max(0, start - 300), min(len(text), end + 300)
        nl = text.rfind('\n', max(0, low - 200), low)
        nr = text.find('\n', high, min(len(text), high + 200))
        spans.append((nl + 1 if nl >= 0 else low, nr if nr >= 0 else high))
    merged = []
    for low, high in sorted(spans):
        if merged and low <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(high, merged[-1][1]))
        else:
            merged.append((low, high))
    return [dict(start=low, end=high, text=text[low:high]) for low, high in merged]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('request-dir', 'inputs', 'recovered', 'output'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--contexts-per-packet', type=int, default=24, choices=range(20, 26))
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('actual scheduled SCNet job required')
    root = Path(a.output)
    if root.exists():
        raise RuntimeError('create-only output already exists')
    request, inputs, recovered = Path(a.request_dir), Path(a.inputs), Path(a.recovered)
    wanted, ordered = {}, OrderedDict()
    for s in SPLITS:
        for index, r in enumerate(rows(checked(request / ('REQUEST_' + s + '_PRIVATE.jsonl'), QUEUES[s]))):
            cid, c = r['candidate_id'], r['context_sha256']
            if cid in wanted or r['split'] != s:
                raise RuntimeError('queue duplicate or split violation')
            wanted[cid] = dict(candidate_id=cid, context_sha256=c, split=s, original_queue_index=index)
            if c in ordered and ordered[c]['split'] != s:
                raise RuntimeError('same context in multiple splits')
            ordered.setdefault(c, dict(split=s, ids=[]))['ids'].append(cid)
    if len(wanted) != 2736:
        raise RuntimeError('authorized existing candidate cardinality changed')
    states = {}
    for r in rows(checked(inputs / 'CONTEXT_STATES_PRIVATE.jsonl', STATES_SHA)):
        c = r['context_sha256']
        if c in states:
            raise RuntimeError('duplicate existing context state')
        states[c] = r
    candidates = {}
    seen = set()
    for r in rows(checked(inputs / 'CANDIDATES_PRIVATE.jsonl', CANDIDATES_SHA)):
        cid = r['candidate_id']
        if cid in seen:
            raise RuntimeError('duplicate existing candidate')
        seen.add(cid)
        if cid not in wanted:
            continue
        q, c = wanted[cid], r['context_sha256']
        state = states[c]
        if (q['context_sha256'], q['split']) != (c, r['split']) or state['split'] != r['split'] or not state['inventory_eligible']:
            raise RuntimeError('original queue/context/split/mask mismatch')
        # Deliberate whitelist: no original labels, old evidence objects or model input.
        candidates[cid] = dict(q, **{k: r[k] for k in (
            'entity_start', 'entity_end', 'term', 'clause_start', 'clause_end', 'clause_state')})
    if set(candidates) != set(wanted):
        raise RuntimeError('authorized candidate missing')
    texts = {}
    for r in rows(checked(recovered / 'CONTEXTS_PRIVATE.jsonl', TEXTS_SHA)):
        c = r['context_sha256']
        if c not in ordered:
            continue
        text = r['complete_context']
        if c in texts or hashlib.sha256(text.encode()).hexdigest() != c:
            raise RuntimeError('duplicate or changed full context')
        texts[c] = text
    if set(texts) != set(ordered):
        raise RuntimeError('requested full context unavailable')
    root.mkdir(parents=True, mode=0o700)
    (root / 'full_contexts').mkdir(mode=0o700)
    mapping, public = [], []
    for c, text in texts.items():
        path = root / 'full_contexts' / (c + '.txt')
        with open(path, 'x', encoding='utf-8') as f:
            os.chmod(path, 0o600)
            f.write(text)
    for s in SPLITS:
        contexts = [c for c, item in ordered.items() if item['split'] == s]
        for offset in range(0, len(contexts), a.contexts_per_packet):
            packet_id = s + '_%04d' % (offset // a.contexts_per_packet + 1)
            packet_rows = []
            for c in contexts[offset:offset + a.contexts_per_packet]:
                text = texts[c]
                xs = [candidates[cid] for cid in ordered[c]['ids']]
                for x in xs:
                    low, high = x['entity_start'], x['entity_end']
                    if not (0 <= low < high <= len(text)) or text[low:high] != x['term']:
                        raise RuntimeError('original numeric term/offset mismatch')
                    expected_id = hashlib.sha256((c + '|%d|%d' % (low, high)).encode()).hexdigest()
                    if expected_id != x['candidate_id']:
                        raise RuntimeError('original numeric candidate identity changed')
                    cs, ce = x['clause_start'], x['clause_end']
                    if (cs is None) != (ce is None) or cs is not None and not (0 <= cs <= low < high <= ce <= len(text)):
                        raise RuntimeError('original clause offsets invalid')
                    x['original_clause'] = text[cs:ce] if cs is not None else None
                    mapping.append(dict(wanted[x['candidate_id']], packet_id=packet_id,
                        entity_start=low, entity_end=high, full_context_file='full_contexts/' + c + '.txt'))
                packet_rows.append(dict(context_sha256=c, split=s, candidates=xs,
                    excerpts=intervals(text, xs), full_context_file='full_contexts/' + c + '.txt',
                    full_context_sha256=c))
            path = root / (packet_id + '_PRIVATE.jsonl')
            write(path, packet_rows, True)
            public.append(dict(packet_id=packet_id, split=s, filename=path.name, sha256=sha(path),
                contexts=len(packet_rows), candidates=sum(len(r['candidates']) for r in packet_rows)))
    write(root / 'CANDIDATE_PACKET_MAP_PRIVATE.jsonl', mapping, True)
    protocol = dict(task='Judge whether each frozen numeric duration constrains applicant experience, then all supported original experience objects.',
        original_objects=list(OBJECTS), statuses=['resolved', 'explicit_non_experience', 'unknown'],
        instructions=[
            'Read original clause and neighboring excerpts; request full_context_file whenever needed. Offsets are Python Unicode character indices, half-open.',
            'For resolved, relations is a nonempty list of {object,evidence:[{start,end,quote}]}; allow multiple objects, each with exact evidence containing this numeric mention.',
            'Explicit_non_experience means this numeric duration does not constrain applicant experience; require exact original evidence, relations=[], and a reason. Never infer it from an unmatched old reference.',
            'Unknown requires relations=[] and unknown_reason; include available exact evidence where useful. Preserve uncertainty rather than forcing an object.',
            'Each review row retains candidate_id, context_sha256, split, review_status; no added candidates or split changes.',
            'No training, automatic negative conversion, semantic quality certification, or rewrite of previous reference labels.'],
        sidecar_fields=['candidate_id', 'context_sha256', 'split', 'review_status', 'relations', 'evidence', 'reason', 'unknown_reason'])
    write(root / 'REVIEW_PROTOCOL.json', protocol)
    write(root / 'PACKET_MANIFEST_PUBLIC.json', dict(scheduler_job_id=os.environ['SLURM_JOB_ID'],
        code_sha256=sha(__file__), input_sha256=dict(queues=QUEUES, candidates=CANDIDATES_SHA, states=STATES_SHA, texts=TEXTS_SHA),
        total_candidates=len(wanted), total_contexts=len(ordered), packets=public,
        mapping_sha256=sha(root / 'CANDIDATE_PACKET_MAP_PRIVATE.jsonl'),
        protocol_sha256=sha(root / 'REVIEW_PROTOCOL.json'), labels_created=0, training_run=False,
        counts_by_original_split={s: dict(candidates=sum(q['split'] == s for q in wanted.values()), contexts=sum(v['split'] == s for v in ordered.values())) for s in SPLITS},
        ordering='Original queue order within each context; contexts ordered by first queue appearance; same context never split. Original queue index retained.',
        scope='Authorized existing numeric duration to experience-object relation review only. Packet preparation is not a semantic judgment.'))


if __name__ == '__main__':
    main()
