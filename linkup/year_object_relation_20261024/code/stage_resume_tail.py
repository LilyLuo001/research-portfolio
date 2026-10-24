#!/usr/bin/env python3
"""Scheduled one-attempt repair of the exact job47324377 final weight range."""
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from stage_pinned_model import ROOT, REVISION, WEIGHT_SHA, FILES, sha, range_headers, write_receipt

PRIOR_TOKEN = '47324377_1792854959395998082'
PRIOR_JOB = '47324377'
ORIGIN = 'https://hf-mirror.com'


def checked_headers(path, lo, hi, total):
    status, headers = range_headers(path)
    if status != 206 or headers.get('content-range') != ['bytes %d-%d/%d' % (lo, hi, total)]:
        raise RuntimeError('exact HTTP206 Content-Range required')
    if headers.get('content-encoding', ['identity']) != ['identity']:
        raise RuntimeError('identity encoding required')


def main():
    if not os.environ.get('SLURM_JOB_ID'): raise RuntimeError('scheduler required')
    os.umask(0o077)
    started = time.monotonic()
    job = os.environ['SLURM_JOB_ID']
    token = job + '_' + str(time.time_ns())
    evidence = ROOT/'models/staging_evidence'/token
    evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    public_dir = ROOT/'public'
    receipt_path = public_dir/('MODEL_STAGE_RESUME_' + token + '_PUBLIC.json')
    public = dict(status='bounded_tail_repair_not_trained', job_id=job, prior_job_id=PRIOR_JOB,
        repo_id='FacebookAI/xlm-roberta-base', revision=REVISION, official_weight_sha256=WEIGHT_SHA,
        strategy='verify15_original_ranges_and_preserved_prefix_then_one_exact_tail',
        requested_transport_origin=ORIGIN, attempts=1, tail_max_seconds=240,
        created_utc=datetime.now(timezone.utc).isoformat(), code_sha256=sha(__file__),
        transport_helper_code_sha256=sha(Path(__file__).with_name('stage_pinned_model.py')),
        installed_software=0, paid_API_calls=0, parts=[])

    def persist():
        public['elapsed_seconds'] = time.monotonic()-started
        write_receipt(receipt_path, public)
        write_receipt(public_dir/'MODEL_STAGE_PUBLIC.json', public)

    persist()
    process = None
    try:
        if REVISION != 'e73636d4f797dec63c3081bb6ed5c7b0bb3f2089' or WEIGHT_SHA != '9d83baaafea92d36de26002c8135a427d55ee6fdc4faaa6e400be4c47724a07e':
            raise RuntimeError('fixed pin changed')
        preparation = json.loads((ROOT/'inputs_v1/PREPARATION_PUBLIC.json').read_text())
        if not preparation['frozen_support_gate'] or not all(x['train50_final50_pass'] for x in preparation['frozen_support_gate']):
            raise RuntimeError('fixed support precondition failed')
        public['stage'] = 'verify_exact_prior_receipt'
        prior_path = public_dir/('MODEL_STAGE_ATTEMPT_' + PRIOR_TOKEN + '_PUBLIC.json')
        prior = json.loads(prior_path.read_text())
        public['prior_receipt_sha256'] = sha(prior_path)
        if prior.get('job_id') != PRIOR_JOB or prior.get('repo_id') != public['repo_id'] or prior.get('revision') != REVISION or prior.get('official_weight_sha256') != WEIGHT_SHA:
            raise RuntimeError('exact prior stage identity required')
        attempts = prior['per_file']['pytorch_model.bin']['attempts']
        if len(attempts) != 1 or attempts[0].get('requested_transport_origin') != ORIGIN:
            raise RuntimeError('exact prior mirror attempt required')
        attempt = attempts[0]
        probe = attempt['range_probe']
        total = attempt['total_bytes']
        if type(total) is not int or not 16 <= total <= (2 << 30) or probe.get('status') != 'validated_206_exact_range' or probe.get('total_bytes') != total or probe.get('bytes') != 1:
            raise RuntimeError('validated original total/probe required')
        public['stage'] = 'verify_original_probe_and_model_metadata'
        old = ROOT/'models/staging_evidence'/PRIOR_TOKEN/'weight_ranges'
        checked_headers(old/'probe.headers.private', 0, 0, total)
        if (old/'probe.part').stat().st_size != 1 or sha(old/'probe.part') != probe['sha256']:
            raise RuntimeError('original range probe integrity failed')
        records = attempt['parts']
        by_name = {r['part']: r for r in records}
        if len(records) != 16 or len(by_name) != 16 or set(by_name) != {'part%02d' % i for i in range(16)}:
            raise RuntimeError('exact original16 range records required')
        dest = ROOT/'models/xlm-roberta-base'
        target = dest/'pytorch_model.bin'
        if target.exists(): raise RuntimeError('weight target already exists; no repeat transport')
        existing = {str(p.relative_to(dest)) for p in dest.rglob('*') if p.is_file()}
        if existing != set(FILES)-{'pytorch_model.bin'}:
            raise RuntimeError('original four-file model inventory required')
        metadata_hashes = {}
        for name in FILES[:-1]:
            digest = sha(dest/name)
            if digest != prior['per_file'][name]['sha256']:
                raise RuntimeError('prior pinned metadata digest changed')
            metadata_hashes[name] = digest
        for i in range(16):
            public['stage'] = 'verify_original_part%02d' % i
            name = 'part%02d' % i
            record, body = by_name[name], old/(name+'.part')
            lo, hi = i*total//16, (i+1)*total//16-1
            expected = hi-lo+1
            if (record.get('start'), record.get('end'), record.get('expected_bytes')) != (lo, hi, expected):
                raise RuntimeError('original exact range partition changed')
            checked_headers(old/(name+'.headers.private'), lo, hi, total)
            size, digest = body.stat().st_size, sha(body)
            if i < 15:
                if record.get('status') != 'validated_206_exact_range' or record.get('bytes') != expected or size != expected or digest != record.get('sha256'):
                    raise RuntimeError('one of original15 validated ranges failed integrity')
            elif record.get('status') == 'validated_206_exact_range' or size != record.get('bytes') or not 0 < size < expected:
                raise RuntimeError('exact incomplete final prefix required')
            public['parts'].append(dict(part=name, start=lo, end=hi, bytes=size, sha256=digest,
                status='original_verified_complete' if i < 15 else 'original_verified_incomplete_prefix'))
        prefix = old/'part15.part'
        prefix_size = prefix.stat().st_size
        lo, hi = 15*total//16 + prefix_size, total-1
        expected = hi-lo+1
        public.update(total_bytes=total, prefix_bytes=prefix_size, tail_start=lo, tail_end=hi, tail_expected_bytes=expected)
        persist()
        public['stage'] = 'single_exact_tail_request'
        tail, header = evidence/'tail.part', evidence/'tail.headers.private'
        remaining = int(270-(time.monotonic()-started))
        if remaining < 1: raise TimeoutError('bounded repair budget exhausted')
        limit = min(240, remaining)
        public['tail_actual_limit_seconds'] = limit
        url = ORIGIN+'/FacebookAI/xlm-roberta-base/resolve/'+REVISION+'/pytorch_model.bin'
        began, written = time.monotonic(), 0
        process = subprocess.Popen(['curl', '-4', '--fail', '--location', '--silent',
            '--connect-timeout', '15', '--max-time', str(limit), '--range', '%d-%d' % (lo, hi),
            '--header', 'Accept-Encoding: identity', '--max-filesize', str(max(expected, 65536)),
            '--dump-header', str(header), '--output', '-', url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        with open(tail, 'xb') as stream:
            while True:
                block = process.stdout.read(min(1 << 20, expected-written+1))
                if not block: break
                if len(block) > expected-written: raise RuntimeError('tail response exceeds strict body cap')
                stream.write(block)
                written += len(block)
        public.update(tail_curl_exit_code=process.wait(timeout=5), tail_bytes=written,
            tail_elapsed_seconds=time.monotonic()-began)
        if public['tail_curl_exit_code']: raise RuntimeError('single tail curl failed')
        public['stage'] = 'verify_exact_tail_response'
        public['tail_http_status'] = range_headers(header)[0]
        checked_headers(header, lo, hi, total)
        if written != expected or tail.stat().st_size != expected:
            raise RuntimeError('exact tail byte count required')
        public['tail_sha256'] = sha(tail)
        # Original prefix/parts remain untouched. Complete part15 in a new file.
        public['stage'] = 'complete_new_last_part_preserving_prefix'
        completed = evidence/'part15.completed.bin'
        with open(completed, 'xb') as stream:
            for source_path in (prefix, tail):
                with open(source_path, 'rb') as source: shutil.copyfileobj(source, stream, 1 << 20)
        if completed.stat().st_size != by_name['part15']['expected_bytes']:
            raise RuntimeError('completed final part size mismatch')
        public['stage'] = 'assemble_new_artifact_and_verify_official_sha'
        assembled = evidence/'pytorch_model.bin.assembled.part'
        with open(assembled, 'xb') as stream:
            for source_path in [old/('part%02d.part' % i) for i in range(15)]+[completed]:
                with open(source_path, 'rb') as source: shutil.copyfileobj(source, stream, 1 << 20)
        public.update(assembled_bytes=assembled.stat().st_size, assembled_sha256=sha(assembled))
        public['official_sha256_match'] = public['assembled_sha256'] == WEIGHT_SHA
        if public['assembled_bytes'] != total or not public['official_sha256_match']:
            raise RuntimeError('official assembled weight integrity failed')
        public['stage'] = 'publish_verified_weight_and_fixed_manifest'
        if target.exists(): raise RuntimeError('concurrent weight target detected')
        assembled.rename(target)
        os.chmod(target, 0o600)
        pin = dict(repo_id=public['repo_id'], revision=REVISION, files=dict(metadata_hashes, **{'pytorch_model.bin':WEIGHT_SHA}))
        manifest = ROOT/'models/MODEL_MANIFEST_PRIVATE.json'
        manifest.write_text(json.dumps(pin, indent=2, sort_keys=True)+'\n')
        os.chmod(manifest, 0o600)
        public.update(pin, status='pinned_checkpoint_staged_not_trained', stage='completed',
            files_bytes={name:(dest/name).stat().st_size for name in FILES}, original_parts_and_prefix_preserved=True)
        persist()
    except BaseException as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        public.update(status='tail_repair_failed_no_training_no_retry', failure_type=type(exc).__name__)
        persist()
        raise RuntimeError('bounded tail repair failed; sanitized receipt and private evidence retained') from None
    finally:
        if process is not None and process.stdout is not None: process.stdout.close()


if __name__ == '__main__': main()
