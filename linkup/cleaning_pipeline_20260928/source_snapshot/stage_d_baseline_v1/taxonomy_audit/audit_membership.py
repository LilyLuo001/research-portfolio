"""Membership audit of the existing USA cohort aggregates; no raw rescan."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'official_onet2019_occupations.csv'
INPUT = ROOT.parent / 'results/quarter_full_code.parquet'
official = list(csv.DictReader(SOURCE.open(encoding='utf-8-sig')))
codes = {r['O*NET-SOC 2019 Code'] for r in official}
assert len(official) == len(codes) == 1016, 'Incomplete official taxonomy download'
totals, unknown = Counter(), Counter()
observed = set()
flagged = []
for row in pq.read_table(INPUT).to_pylist():
    code, n = row['onet_code'], row['record_count']
    if row['code_status'] != 'valid':
        totals[row['code_status']] += n
    elif code in codes:
        totals['official_2019_member'] += n
        observed.add(code)
    else:
        totals['nonmember_nonempty'] += n
        unknown[code] += n
    row['taxonomy_membership'] = ('official_2019_member' if code in codes else
        row['code_status'] if row['code_status'] != 'valid' else
        'nonmember_placeholder_99' if code == '99-9999.00' else 'nonmember_vintage_unresolved')
    flagged.append(row)
assert sum(totals.values()) == 253210047
pq.write_table(pa.Table.from_pylist(flagged), ROOT / 'quarter_full_code_flagged.parquet', compression='zstd')
report = {
    'retrieved_date': '2026-09-27',
    'source_url': 'https://www.onetcenter.org/taxonomy/2019/list/2019_Occupations.csv?fmt=csv',
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'input_sha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
    'official_unique_codes': len(codes), 'observed_official_codes': len(observed),
    'records_by_membership': dict(totals), 'nonmember_codes': dict(unknown),
    'limits': 'Code membership only. Does not establish job classification accuracy, historical taxonomy vintage, or contemporary availability of snapshot codes.'
}
(ROOT / 'membership_report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
