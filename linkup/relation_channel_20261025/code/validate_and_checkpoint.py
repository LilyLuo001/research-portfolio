#!/usr/bin/env python3
"""Scheduled structural checkpoint of complete Pro agent review packets only.

Incoming filenames are exactly <original_packet_id>_REVIEW_PRIVATE.jsonl.
Accepted package bindings are create-only; same SHA reuses, changed SHA refuses.
No reference file is changed. Failed/incomplete incoming sidecars remain intact.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
from prepare_pro_packets import checked, rows, sha, write


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet-root', required=True)
    p.add_argument('--reviews', required=True)
    p.add_argument('--manifest-sha256', required=True)
    a = p.parse_args()
    job = os.environ.get('SLURM_JOB_ID')
    if not job or not job.isdigit():
        raise RuntimeError('actual scheduled SCNet job required')
    packets, reviews = Path(a.packet_root).resolve(), Path(a.reviews).resolve()
    manifest = json.loads(checked(packets / 'PACKET_MANIFEST_PUBLIC.json', a.manifest_sha256).read_text())
    if manifest['total_candidates'] != 2736:
        raise RuntimeError('authorized membership cardinality changed')
    catalog = {r['packet_id']: r for r in manifest['packets']}
    if len(catalog) != len(manifest['packets']):
        raise RuntimeError('duplicate original packet ID')
    incoming, accepted = reviews / 'incoming', reviews / 'accepted'
    attempts, snapshot = reviews / 'validation_attempts' / job, reviews / 'snapshots' / job
    if attempts.exists() or snapshot.exists():
        raise RuntimeError('checkpoint job paths must be new')
    for path in (incoming, accepted, attempts, snapshot):
        path.mkdir(parents=True, mode=0o700, exist_ok=path in (incoming, accepted))
    validator = Path(__file__).with_name('validate_review_sidecars.py')
    outcomes = []
    expected_names = {pid + '_REVIEW_PRIVATE.jsonl': pid for pid in catalog}
    # Unknown names are retained and explicitly accounted for, never guessed.
    extra_names = [p.name for p in incoming.iterdir() if p.is_file() and p.name not in expected_names]
    for pid, packet in catalog.items():
        source = incoming / (pid + '_REVIEW_PRIVATE.jsonl')
        binding = accepted / (pid + '.json')
        old = json.loads(binding.read_text()) if binding.exists() else None
        if not source.exists():
            outcomes.append(dict(packet_id=pid, state='accepted_source_not_in_incoming' if old else 'not_received'))
            continue
        digest = sha(source)
        if old:
            outcomes.append(dict(packet_id=pid, state='reused_same_sha' if old['sidecar_sha256'] == digest else 'rejected_changed_sha', sidecar_sha256=digest))
            continue
        out = attempts / pid
        try:
            # Provenance is explicit per candidate and describes what was read.
            for r in rows(source):
                if not all(isinstance(r.get(k), str) and r[k].strip() for k in ('reviewer', 'model')):
                    raise RuntimeError('missing_reviewer_or_model_provenance')
                scope = r.get('actual_read_scope')
                if not isinstance(scope, dict) or scope.get('kind') not in ('packet_excerpts', 'full_context'):
                    raise RuntimeError('missing_actual_read_scope_provenance')
                expected = packet['filename'] if scope['kind'] == 'packet_excerpts' else 'full_contexts/' + r['context_sha256'] + '.txt'
                if scope.get('source') != expected:
                    raise RuntimeError('actual_read_scope_source_mismatch')
            command = [sys.executable, str(validator), '--packet-root', str(packets),
                '--manifest-sha256', a.manifest_sha256, '--sidecar', str(source),
                '--sidecar-sha256', digest, '--packet-id', pid, '--output', str(out)]
            result = subprocess.run(command, capture_output=True, text=True)
            log = attempts / (pid + '_VALIDATOR_LOG_PRIVATE.txt')
            with open(log, 'x', encoding='utf-8') as f:
                os.chmod(log, 0o600)
                f.write(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError('validator_failed_or_packet_incomplete')
            if sha(source) != digest:
                raise RuntimeError('incoming_changed_during_validation')
            receipt = out / 'SIDECAR_VALIDATION_PUBLIC.json'
            v = json.loads(receipt.read_text())
            checked(out / 'STRUCTURALLY_VALIDATED_REVIEW_PRIVATE.jsonl', v['validated_sidecar_sha256'])
            write(binding, dict(packet_id=pid, sidecar_sha256=digest,
                manifest_sha256=a.manifest_sha256, validation_receipt=str(receipt),
                validation_receipt_sha256=sha(receipt), accepted_job_id=job))
            outcomes.append(dict(packet_id=pid, state='accepted_structurally', sidecar_sha256=digest))
        except Exception as exc:
            # Detailed error remains private. Never import failed rows into ledger.
            write(attempts / (pid + '_FAILURE_PRIVATE.json'), dict(error=str(exc), source=str(source), sidecar_sha256=digest))
            outcomes.append(dict(packet_id=pid, state='failed_retained_not_in_ledger', sidecar_sha256=digest))
    ledger, ids, contexts, counts, split_contexts = [], set(), set(), Counter(), {}
    passed = []
    for pid, packet in catalog.items():
        binding = accepted / (pid + '.json')
        if not binding.exists():
            continue
        b = json.loads(binding.read_text())
        if b['manifest_sha256'] != a.manifest_sha256 or b['packet_id'] != pid:
            raise RuntimeError('accepted package immutable manifest conflict')
        receipt = Path(b['validation_receipt'])
        v = json.loads(checked(receipt, b['validation_receipt_sha256']).read_text())
        if v['sidecar_input_sha256'] != b['sidecar_sha256'] or v['semantic_quality_accepted'] is not False:
            raise RuntimeError('accepted receipt identity conflict')
        sidecar = checked(receipt.parent / 'STRUCTURALLY_VALIDATED_REVIEW_PRIVATE.jsonl', v['validated_sidecar_sha256'])
        n = 0
        for r in rows(sidecar):
            cid, c, s = r['candidate_id'], r['context_sha256'], r['split']
            if cid in ids or s != packet['split']:
                raise RuntimeError('accepted ledger duplicate or original split conflict')
            ids.add(cid); contexts.add(c)
            split_contexts.setdefault(s, set()).add(c)
            counts[(s, r['review_status'])] += 1
            ledger.append(r); n += 1
        if n != packet['candidates']:
            raise RuntimeError('accepted complete package cardinality mismatch')
        passed.append(dict(packet_id=pid, split=packet['split'], candidates=n,
            sidecar_sha256=b['sidecar_sha256'], binding_sha256=sha(binding)))
    if len(ids) > 2736:
        raise RuntimeError('authorized total exceeded')
    private_ledger = snapshot / 'REVIEW_LEDGER_PRIVATE.jsonl'
    write(private_ledger, ledger, True)
    write(snapshot / 'CHECKPOINT_PUBLIC.json', dict(scheduler_job_id=job,
        code_sha256=sha(__file__), validator_code_sha256=sha(validator),
        packet_manifest_sha256=a.manifest_sha256, passed_packets=passed,
        verified_packets=len(passed), verified_candidates=len(ids), unique_contexts=len(contexts),
        total_authorized=2736, remaining_candidates=2736-len(ids),
        counts_by_original_split={s: dict(candidates=sum(n for (sp, _), n in counts.items() if sp == s),
            unique_contexts=len(split_contexts.get(s, set())), **{status: counts[(s, status)] for status in ('resolved', 'explicit_non_experience', 'unknown')}) for s in ('train', 'final_previously_exposed', 'previous_holdout_reserved_not_final')},
        counts_by_status={status: sum(n for (_, st), n in counts.items() if st == status) for status in ('resolved', 'explicit_non_experience', 'unknown')},
        ledger_sha256=sha(private_ledger), private_snapshot_path=str(snapshot),
        incoming_outcomes=outcomes, unknown_incoming_filenames_count=len(extra_names),
        unknown_field_policy='Completed packets containing unknown judgments are accepted structurally and not automatically requeued.',
        semantic_quality_accepted=False, original_reference_overwritten=False, training_run=False,
        boundary='Pro agent judgments; structural validation and immutable progress accounting only.'))


if __name__ == '__main__':
    main()
