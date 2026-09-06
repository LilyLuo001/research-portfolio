#!/usr/bin/env python3
"""Check V3 request coverage and delivered evidence integrity, not scientific validity.

Usage:
  python validate_revision_delivery.py --seed requirements_seed.json \
      --status /path/to/requirements_status.json --root /path/to/delivery

Exit codes: 0 = structural checks and requested completion mode passed;
            1 = invalid/missing/tampered evidence or requirement coverage;
            2 = valid ledger but requested completion mode not reached.

A hash or a self-reported VERIFIED status cannot establish that an estimate,
method, execution receipt, or reviewer claim is substantively truthful. The
scientific checks in EXECUTION_PROMPT_V3.md and human/independent review remain
necessary. The tool never executes commands stored in receipts.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

STATUSES = {
    'NOT_STARTED', 'SPECIFIED', 'IMPLEMENTED_UNRUN', 'RUN_UNVALIDATED', 'VERIFIED',
    'PREMISE_CORRECTED', 'BLOCKED_INPUT', 'BLOCKED_COMPUTE',
    'INAPPLICABLE_PROPOSED', 'INAPPLICABLE_APPROVED',
    'DEFERRED_PROPOSED', 'DEFERRED_APPROVED',
}
ACCOUNTED = {
    'VERIFIED', 'PREMISE_CORRECTED', 'BLOCKED_INPUT', 'BLOCKED_COMPUTE',
    'INAPPLICABLE_APPROVED', 'DEFERRED_APPROVED',
}
RESOLVED = {'VERIFIED', 'PREMISE_CORRECTED', 'INAPPLICABLE_APPROVED'}
IMMUTABLE = ('title', 'source_refs', 'prompt_section', 'kind', 'priority',
             'acceptance_checks', 'depends_on', 'minimum_verified_evidence_roles', 'empirical')
EMPIRICAL_MODES = {'empirical_reestimate', 'analysis_simulation',
                   'aggregate_analysis', 'numerical_analysis'}
SHA256 = re.compile(r'^[0-9a-f]{64}$')


def load_json(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as stream:
        return json.load(stream)


def indexed(document: Any) -> dict[str, dict[str, Any]]:
    values = document.get('requirements') if isinstance(document, dict) else None
    if not isinstance(values, list):
        raise ValueError('Document must contain a requirements list.')
    result: dict[str, dict[str, Any]] = {}
    for row in values:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str):
            raise ValueError('Every requirement needs a string id.')
        if row['id'] in result:
            raise ValueError('Duplicate requirement ID: ' + row['id'])
        result[row['id']] = row
    return result


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def safe_file(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or '..' in rel.parts:
        raise ValueError('Evidence path must be a contained relative path.')
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('Symlink evidence is not permitted.')
    resolved = cursor.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('Evidence must be a regular file inside the delivery root.')
    return resolved


def valid_receipt(value: Any, empirical: bool) -> None:
    if not isinstance(value, dict):
        raise ValueError('Run receipt must be a JSON object.')
    for key in ('command', 'start_utc', 'end_utc', 'exit_code', 'mode', 'code_hash'):
        if key not in value:
            raise ValueError('Run receipt missing ' + key)
    if value['exit_code'] != 0 or not value['command']:
        raise ValueError('A VERIFIED run receipt must show a successful nonempty command.')
    start = datetime.fromisoformat(str(value['start_utc']).replace('Z', '+00:00'))
    end = datetime.fromisoformat(str(value['end_utc']).replace('Z', '+00:00'))
    if start.tzinfo is None or end.tzinfo is None or end < start:
        raise ValueError('Run timestamps must have time zones and valid ordering.')
    if not value['code_hash']:
        raise ValueError('Missing executed-code hash or commit.')
    if empirical and (value['mode'] not in EMPIRICAL_MODES or not value.get('spec_id')):
        raise ValueError('An empirical task requires an analysis run mode and spec_id, not only an exhibit rebuild.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--status', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mode', choices=['accounted', 'core', 'complete'], default='complete')
    args = parser.parse_args()
    try:
        seed = indexed(load_json(args.seed))
        rows = indexed(load_json(args.status))
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError('Delivery root is not a directory.')
    except (OSError, ValueError, TypeError) as exc:
        print('INPUT ERROR:', exc, file=sys.stderr)
        return 1

    errors: list[str] = []
    for rid, base in seed.items():
        if rid not in rows:
            errors.append(rid + ': required row was omitted.')
            continue
        for key in IMMUTABLE:
            if rows[rid].get(key) != base.get(key):
                errors.append(f'{rid}: protected specification field changed: {key}. Record an amendment instead.')

    for rid, row in rows.items():
        status = row.get('status')
        if status not in STATUSES:
            errors.append(f'{rid}: unknown status {status!r}.')
            continue
        if not row.get('source_refs') or not row.get('acceptance_checks'):
            errors.append(rid + ': missing source mapping or acceptance checks.')
        for dep in row.get('depends_on', []):
            if dep not in rows:
                errors.append(f'{rid}: missing dependency {dep}.')
            elif status == 'VERIFIED' and rows[dep].get('status') not in RESOLVED:
                errors.append(f'{rid}: marked VERIFIED before dependency {dep} was resolved.')
        if status in ACCOUNTED or status.endswith('_PROPOSED'):
            if not row.get('summary') or not row.get('response_locations'):
                errors.append(rid + ': disposition needs an actual summary and response location.')
        if status.startswith('BLOCKED_'):
            blocker = row.get('blocker')
            if not isinstance(blocker, dict) or any(not blocker.get(k) for k in
                ('missing_requirement', 'attempts', 'claim_impact', 'next_step')):
                errors.append(rid + ': blocker lacks missing requirement, attempts, claim impact, or next step.')
        if status.endswith('_APPROVED'):
            approval = row.get('approval')
            if not isinstance(approval, dict) or any(not approval.get(k) for k in
                ('approved_by', 'approved_at', 'reason', 'evidence_path')):
                errors.append(rid + ': approved disposition lacks documented authorization.')
            else:
                try:
                    safe_file(root, approval['evidence_path'])
                except (OSError, ValueError, TypeError) as exc:
                    errors.append(f'{rid}: invalid approval artifact: {exc}')
        evidence = row.get('evidence', [])
        if not isinstance(evidence, list):
            errors.append(rid + ': evidence must be a list.')
            continue
        roles: set[str] = set()
        for item in evidence:
            try:
                if not isinstance(item, dict):
                    raise ValueError('Evidence record must be an object.')
                role = item['role']
                path = safe_file(root, item['path'])
                expected = item['sha256']
                if not SHA256.fullmatch(expected) or digest(path) != expected:
                    raise ValueError('Missing or mismatched SHA-256 hash.')
                if path.stat().st_size == 0:
                    raise ValueError('An empty file is not completion evidence.')
                roles.add(role)
                if status == 'VERIFIED' and role == 'run_receipt':
                    valid_receipt(load_json(path), bool(row.get('empirical')))
            except (KeyError, OSError, ValueError, TypeError) as exc:
                errors.append(f'{rid}: evidence error: {exc}')
        if status == 'VERIFIED':
            needed = set(row.get('minimum_verified_evidence_roles', []))
            if not needed:
                errors.append(rid + ': VERIFIED task has no evidence-role specification.')
            if needed - roles:
                errors.append(f'{rid}: missing evidence roles: {sorted(needed - roles)}')
            review = row.get('review')
            if not isinstance(review, dict) or not review.get('reviewer') or not review.get('report_path'):
                errors.append(rid + ': VERIFIED task needs a named review role and report path (self-review must be labeled).')
            else:
                try:
                    safe_file(root, review['report_path'])
                except (OSError, ValueError, TypeError) as exc:
                    errors.append(f'{rid}: review report missing: {exc}')
        elif status == 'PREMISE_CORRECTED' and not {'source_evidence', 'verification_report'} <= roles:
            errors.append(rid + ': corrected premise requires source and verification evidence.')
        elif status in ACCOUNTED and not evidence:
            errors.append(rid + ': accounted disposition has no delivered evidence.')

    counts = Counter(r.get('status', 'MISSING') for r in rows.values())
    accounted = not errors and all(r.get('status') in ACCOUNTED for r in rows.values())
    core = not errors and all(r.get('status') in RESOLVED for r in rows.values()
                              if r.get('priority') == 'blocking')
    executed = not errors and all(r.get('status') == 'VERIFIED' for r in rows.values()
                                  if r.get('empirical'))
    fully_resolved = not errors and all(r.get('status') in RESOLVED for r in rows.values())
    print(json.dumps({'requirement_count': len(rows), 'status_counts': dict(counts),
        'all_requests_accounted_for_structurally': accounted,
        'core_requirements_structurally_resolved': core,
        'all_requested_empirical_tasks_reported_verified': executed,
        'all_requirements_structurally_resolved': fully_resolved,
        'scientific_validity': 'NOT DETERMINED BY THIS VALIDATOR',
        'submission_readiness': 'REQUIRES SCIENTIFIC, AUTHOR, AND DELIVERY REVIEW',
        'errors': errors}, indent=2))
    if errors:
        return 1
    passed = accounted if args.mode == 'accounted' else (core if args.mode == 'core' else fully_resolved and executed)
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
