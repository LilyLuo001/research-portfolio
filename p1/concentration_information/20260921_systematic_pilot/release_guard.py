"""Deny response-bearing reads until an explicit reviewed release is present.

This guard performs local artifact checks only. It never scans raw archives.
Stage-A nonresponse projections have their own separately frozen contract.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REQUIRED={'population','clock','signal','actual_basket','quote_endpoints','common_support',
          'estimator','dependence_calibration','independent_review'}

def require_release(root=ROOT):
    receipt=root/'EMPIRICAL_RELEASE.json'
    if not receipt.exists():
        raise RuntimeError('PRIMARY_READ_BLOCKED: reviewed EMPIRICAL_RELEASE.json is absent')
    r=json.loads(receipt.read_text())
    if r.get('status')!='FROZEN_FOR_PRIMARY_ANALYSIS':
        raise RuntimeError('PRIMARY_READ_BLOCKED: release is not frozen')
    conditions=r.get('conditions',{})
    if any(conditions.get(key)!='PASS' for key in REQUIRED):
        raise RuntimeError('PRIMARY_READ_BLOCKED: required scientific/data conditions not passed')
    bindings=r.get('artifact_sha256',{})
    if not all(key in bindings for key in ['ANALYSIS_CONTRACT.yaml','INDEPENDENT_REVIEW.md','DATA_AND_SOURCE_MANIFEST.json']):
        raise RuntimeError('PRIMARY_READ_BLOCKED: missing mandatory artifact bindings')
    if not any(key.startswith('method/') and key.endswith('.py') for key in bindings):
        raise RuntimeError('PRIMARY_READ_BLOCKED: estimator code is not bound')
    for path,digest in bindings.items():
        f=(root/path).resolve()
        if not f.is_relative_to(root.resolve()) or not f.is_file():
            raise RuntimeError('PRIMARY_READ_BLOCKED: invalid artifact path')
        if hashlib.sha256(f.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('PRIMARY_READ_BLOCKED: artifact changed')
    return r

if __name__=='__main__':
    try: require_release()
    except (RuntimeError,ValueError,KeyError) as e:
        print(str(e)); raise SystemExit(2)
    print('REVIEWED_PRIMARY_RELEASE_PRESENT; this guard does not itself execute analysis')
