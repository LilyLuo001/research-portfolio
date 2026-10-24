#!/usr/bin/env python3
"""Stage the same pinned checkpoint, with one bounded same-revision mirror fallback."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit

ROOT = Path('/work/home/lilysharp/private/year_object_relation_20261024')
REVISION = 'e73636d4f797dec63c3081bb6ed5c7b0bb3f2089'
WEIGHT_SHA = '9d83baaafea92d36de26002c8135a427d55ee6fdc4faaa6e400be4c47724a07e'
FILES = ['config.json', 'tokenizer_config.json', 'sentencepiece.bpe.model', 'tokenizer.json', 'pytorch_model.bin']
ORIGINS = ('https://huggingface.co', 'https://hf-mirror.com')
# Fits the existing 30-minute allocation, with time reserved for receipts.
TRANSPORT_BUDGET_SECONDS = 1650


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def write_receipt(path, value):
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    os.chmod(temp, 0o600)
    temp.replace(path)


def origin_only(url):
    # Redirect URLs can contain signed query credentials. Retain origin only.
    parsed = urlsplit(url)
    return parsed.scheme + '://' + parsed.hostname if parsed.hostname else None


def main():
    if not os.environ.get('SLURM_JOB_ID'): raise RuntimeError('scheduler required')
    os.umask(0o077)
    started = time.monotonic()
    job = os.environ['SLURM_JOB_ID']
    token = job + '_' + str(time.time_ns())
    public_dir = ROOT/'public'
    public_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt = public_dir/('MODEL_STAGE_ATTEMPT_' + token + '_PUBLIC.json')
    public = dict(repo_id='FacebookAI/xlm-roberta-base', revision=REVISION,
        official_weight_sha256=WEIGHT_SHA, required_files=FILES, job_id=job,
        created_utc=datetime.now(timezone.utc).isoformat(), code_sha256=sha(__file__),
        status='staging_not_trained', per_file={}, installed_software=0, paid_API_calls=0,
        transport_policy=dict(origins=list(ORIGINS), attempts_per_origin=1,
            total_transport_budget_seconds=TRANSPORT_BUDGET_SECONDS, per_attempt_max_seconds=1200))

    def persist():
        public['elapsed_seconds'] = time.monotonic() - started
        write_receipt(receipt, public)
        write_receipt(public_dir/'MODEL_STAGE_PUBLIC.json', public)

    persist()
    try:
        preparation = json.loads((ROOT/'inputs_v1/PREPARATION_PUBLIC.json').read_text())
        if not preparation['frozen_support_gate'] or not all(x['train50_final50_pass'] for x in preparation['frozen_support_gate']):
            raise RuntimeError('fixed class-support precondition not met; no checkpoint download')
        dest = ROOT/'models/xlm-roberta-base'
        manifest = ROOT/'models/MODEL_MANIFEST_PRIVATE.json'
        dest.mkdir(parents=True, exist_ok=True, mode=0o700)
        evidence = ROOT/'models/staging_evidence'/token
        evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
        for name in FILES:
            target, partial = dest/name, dest/(name+'.part')
            item = public['per_file'][name] = dict(attempts=[])
            file_started = time.monotonic()
            if partial.exists():
                partial.rename(evidence/(name+'.prior.part'))
                item['prior_partial_preserved'] = True
            if target.exists():
                if name == 'pytorch_model.bin' and sha(target) != WEIGHT_SHA:
                    raise RuntimeError('existing weight digest mismatch')
                item.update(status='reused_existing_local_file', requested_transport_origin=None,
                    origin_status='not_recorded_by_prior_stage_code', sha256=sha(target), bytes=target.stat().st_size,
                    elapsed_seconds=time.monotonic()-file_started)
                persist()
                continue
            for attempt, origin in enumerate(ORIGINS, 1):
                remaining = int(TRANSPORT_BUDGET_SECONDS - (time.monotonic()-started))
                if remaining < 1: raise TimeoutError('bounded staging budget exhausted')
                began = time.monotonic()
                entry = dict(requested_transport_origin=origin, attempt=attempt)
                item['attempts'].append(entry)
                url = origin+'/FacebookAI/xlm-roberta-base/resolve/'+REVISION+'/'+name
                try:
                    # Capture only effective URL; never expose raw curl errors,
                    # proxy headers, signed query strings, or credentials.
                    result = subprocess.run(['curl', '-4', '--fail', '--location', '--silent',
                        '--connect-timeout', '15', '--max-time', str(min(1200, remaining)),
                        '--output', str(partial), '--write-out', '%{url_effective}', url],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        timeout=min(1200, remaining)+10, check=False)
                    entry['curl_exit_code'] = result.returncode
                    entry['final_transport_origin'] = origin_only(result.stdout.decode('utf-8', 'replace'))
                    if result.returncode:
                        entry['failure_type'] = 'CurlExit%d' % result.returncode
                    elif name == 'pytorch_model.bin' and sha(partial) != WEIGHT_SHA:
                        entry['failure_type'] = 'OfficialWeightSHA256Mismatch'
                    else:
                        partial.rename(target)
                        os.chmod(target, 0o600)
                        entry['status'] = 'downloaded_and_integrity_checked' if name == 'pytorch_model.bin' else 'downloaded_same_pinned_revision'
                        item.update(status='staged', requested_transport_origin=origin,
                            final_transport_origin=entry['final_transport_origin'], sha256=sha(target), bytes=target.stat().st_size)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    entry['failure_type'] = type(exc).__name__
                entry['elapsed_seconds'] = time.monotonic()-began
                if partial.exists():
                    partial.rename(evidence/(name+'.attempt%d.part' % attempt))
                    entry['partial_preserved'] = True
                item['elapsed_seconds'] = time.monotonic()-file_started
                persist()
                if target.exists(): break
            if not target.exists(): raise RuntimeError('bounded official and mirror transport failed')
        cfg = json.loads((dest/'config.json').read_text())
        if cfg.get('model_type') != 'xlm-roberta' or cfg.get('hidden_size') != 768 or cfg.get('num_hidden_layers') != 12:
            raise RuntimeError('wrong fixed architecture')
        if sha(dest/'pytorch_model.bin') != WEIGHT_SHA: raise RuntimeError('weight integrity failed')
        pin = dict(repo_id='FacebookAI/xlm-roberta-base', revision=REVISION, files={name:sha(dest/name) for name in FILES})
        manifest.write_text(json.dumps(pin, indent=2)+'\n')
        os.chmod(manifest, 0o600)
        public.update(pin, status='pinned_checkpoint_staged_not_trained', files_bytes={name:(dest/name).stat().st_size for name in FILES})
        persist()
    except BaseException as exc:
        # Failure details are deliberately type-only; source URLs may be signed.
        public.update(status='staging_failed_no_training', failure_type=type(exc).__name__)
        persist()
        raise RuntimeError('pinned staging failed; sanitized public receipt retained') from None


if __name__ == '__main__': main()
