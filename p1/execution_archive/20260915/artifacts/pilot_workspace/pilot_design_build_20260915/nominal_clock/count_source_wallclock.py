"""Aggregate only displayed clock strings in an explicit nominal time band.

Not a market session, timezone adjudication or final population filter.
No source row, security ID or response value is exported.
"""
from pathlib import Path
from datetime import time
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT/'missing_data_round_20260914/union_v2_earnings_inputs/selected_event_metadata.csv'
FIELDS = ['association_id', 'wave_id', 'tier', 'sample_period', 'announcement_times_all', 'sue_analyst_min2_coverage', 'permno']


def parse_time(value):
    try:
        return time.fromisoformat(str(value).strip())
    except ValueError:
        return None


def main():
    data = pd.read_csv(SOURCE, usecols=FIELDS, dtype=str)
    assert len(data) == 852 and data.association_id.nunique() == 852
    data['parsed'] = data.announcement_times_all.map(parse_time)
    data['band'] = data.parsed.map(lambda x: x is not None and time(9, 30) <= x <= time(15, 0))
    data['min2'] = data.sue_analyst_min2_coverage.str.lower().map({'true': True, 'false': False})
    assert not data['min2'].isna().any()
    rows = []
    for (wave, tier, period), part in data.groupby(['wave_id', 'tier', 'sample_period']):
        band = part.loc[part.band]
        rows.append(dict(wave_id=wave, tier=tier, sample_period=period, acquisition_associations=len(part), parseable_clock_strings=int(part.parsed.notna().sum()), nominal_0930_1500_associations=len(band), nominal_0930_1500_stocks=band.permno.nunique(), nominal_0930_1500_with_min2=int(band.min2.sum()), population='UNION_V2_ACQUISITION_ONLY', meaning='SOURCE_DISPLAY_CLOCK_BAND_NOT_VERIFIED_RTH60'))
    table = pd.DataFrame(rows)
    table.to_csv(OUT/'nominal_clock_band_by_wave_tier_period.csv', index=False)
    coverage = []
    for wave, frame in table.groupby('wave_id'):
        missing = [f'{r.tier}/{r.sample_period}' for r in frame.itertuples() if r.nominal_0930_1500_associations == 0]
        coverage.append({'wave_id': wave, 'four_cells_nonempty_in_nominal_band': not missing, 'empty_nominal_cells': missing})
    receipt = {
        'status': 'EXECUTED_SOURCE_CLOCK_DIAGNOSTIC_NOT_SESSION_CENSUS',
        'source': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'allowed_columns': FIELDS, 'source_rows': len(data),
        'clock_window': '[09:30:00,15:00:00] source displayed local clock; no timezone attached',
        'nominal_band_associations': int(data.band.sum()),
        'nominal_band_by_period': data.groupby('sample_period').band.sum().astype(int).to_dict(),
        'nominal_band_with_min2': int((data.band & data.min2).sum()),
        'four_cell_diagnostic': coverage,
        'limitations': [
            'This nominal band is chosen to expose the candidate RTH60 support problem, not to certify actual exchange sessions',
            'No Eastern/UTC conversion, early-close calendar, first-public timestamp or uncertainty bound is assumed',
            'No observation is added to or excluded from a final population by this diagnostic',
            'Acquisition roster does not bound support in a broader eligible population',
            'Analyst count is not SUE compatibility or actual numeric variation',
        ],
        'financial_values_read': False, 'SCC_access': False,
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (OUT/'NOMINAL_CLOCK_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
