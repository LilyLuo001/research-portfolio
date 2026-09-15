"""Custodian-only, retrieval-seed-only IBES metadata projection.

Schema verified from archived schema__ibes__actu_epsus.csv and harvest SQL.
Does not resolve economic-event identity, timezone, exchange closes, or tiers.
Use only after a custodian approves this exact projection and candidate list.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

RAW = Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw')
COLUMNS = ['ticker', 'cusip', 'pends', 'pdicity', 'anndats', 'anntims', 'actdats', 'acttims']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate-cusips', required=True, type=Path,
                   help='Custodian-approved CSV with cusip column; no automatic version choice.')
    p.add_argument('--output-dir', required=True, type=Path)
    p.add_argument('--custodian-authorization-reference', required=True)
    p.add_argument('--bridge-receipt', required=True, type=Path,
                   help='Receipt for the date-valid PERMNO--IBES bridge that made this CUSIP seed.')
    args = p.parse_args()
    if not args.custodian_authorization_reference.strip():
        p.error('Actual authorization reference required; this string is not access authority.')
    import pandas as pd
    import pyarrow.parquet as pq

    with args.candidate_cusips.open(newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ['cusip']:
            raise ValueError('Candidate list must contain only cusip.')
        candidates = {row['cusip'].strip() for row in reader}
    if not candidates or any(len(x) != 8 or not x.isalnum() for x in candidates):
        raise ValueError('Require approved nonempty eight-character CUSIP keys; no truncation or invented crosswalk.')
    bridge_receipt = json.loads(args.bridge_receipt.read_text())
    if bridge_receipt.get('candidate_cusips') != len(candidates):
        raise ValueError('Bridge receipt/CUSIP list mismatch; do not run a detached identifier seed.')
    if bridge_receipt.get('candidate_cusips_sha256') != sha(args.candidate_cusips):
        raise ValueError('Bridge receipt/CUSIP hash mismatch; do not run a substituted identifier seed.')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / 'ibes_announcement_metadata.csv'
    receipt_path = args.output_dir / 'ibes_projection_receipt.json'
    if output.exists() or receipt_path.exists():
        raise FileExistsError('Use a new output directory; existing outputs are preserved.')
    frames, inputs = [], []
    for year in range(2019, 2027):
        path = RAW / f'ibes_actuals_eps_{year}.parquet'
        if not path.exists():
            inputs.append({'path': str(path), 'status': 'MISSING_PARTITION'})
            continue
        schema = pq.read_schema(path)
        if any(c not in schema.names for c in COLUMNS):
            raise ValueError('Documented projection column missing; stop rather than broaden projection.')
        frame = pd.read_parquet(path, columns=COLUMNS)
        dates = pd.to_datetime(frame['anndats'], errors='coerce')
        selected = frame.loc[frame['cusip'].astype('string').str.strip().isin(candidates)
                             & dates.ge('2019-01-01') & dates.lt('2026-09-01')].copy()
        selected['source_partition'] = path.name
        frames.append(selected)
        inputs.append({'path': str(path), 'sha256': sha(path),
                       'projected_rows': len(frame), 'candidate_records': len(selected),
                       'invalid_announcement_dates': int(dates.isna().sum())})
    result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS + ['source_partition'])
    # Retain source-record duplication for later documented revision/event rules.
    result.to_csv(output, index=False)
    receipt = {'authorization_reference': args.custodian_authorization_reference,
               'query_sha256': sha(Path(__file__)), 'candidate_sha256': sha(args.candidate_cusips),
               'bridge_receipt_sha256': sha(args.bridge_receipt),
               'retrieval_seed_only': True,
               'inputs': inputs, 'output_sha256': sha(output), 'record_count': len(result),
               'columns': list(result.columns), 'economic_event_count': None,
               'timezone': 'UNVERIFIED', 'session_classification': 'NOT_RUN',
               'population_link': 'DATE_VALID_PIT_BRIDGE_CANDIDATE_CUSIP_MATCH; analysis eligibility NOT_ASSESSED',
               'forbidden_value_columns_projected': [],
               'filters': 'approved candidate CUSIPs; 2019-01-01 <= anndats < 2026-09-01; PRE/POST not inferred'}
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'output_records': len(result), 'economic_event_count': None}))


if __name__ == '__main__':
    main()
