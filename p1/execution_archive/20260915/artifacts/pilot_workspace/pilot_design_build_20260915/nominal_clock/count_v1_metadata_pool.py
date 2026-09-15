"""Version-pinned v1 metadata-only nominal-clock support, no new retrieval.

Uses the existing capped max-8-PRE/max-4-POST snapshot, not all historical events.
All output tables are aggregates. No market session or economic-event certification.
"""
from pathlib import Path
from datetime import time
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MD = ROOT/'missing_data_round_20260914'
OUT = Path(__file__).resolve().parent
KEYS = ['wave_id', 'permno', 'provisional_tier', 'event_side', 'pends', 'anndats']
SPECS = {
    'pool': ('EARNINGS_METADATA_POOL_8PRE_4POST.csv', 'f33bc3532b127554531380e80635c961a5a251ada51ca287b412c144ba0a6b3f', KEYS+['anntims']),
    'analyst': ('full_pool_analyst_coverage/event_analyst_coverage.csv', '95c720b62390e513742fc85bbb464712c75b98c3e1a5763c43ae1b64f1fd29e3', KEYS+['analyst_min2']),
    'supported': ('analysis_ready_acquisition/full_support_overlap_analyst_intersection.csv', '60c8ef59a7dfce9ac9444d7f7f775f46806ae12309bd3868129595a0d43f472a', ['wave_id', 'permno', 'provisional_tier', 'proposed_overlap_clean', 'all_12_events_min2']),
}


def load(name):
    file, expected, columns = SPECS[name]
    p = MD/file
    assert hashlib.sha256(p.read_bytes()).hexdigest() == expected, name
    return pd.read_csv(p, usecols=columns, dtype=str)


def flag(series):
    f = series.str.lower().map({'true': True, 'false': False})
    assert f.notna().all()
    return f


def parse(value):
    try:
        return time.fromisoformat(str(value).strip())
    except ValueError:
        return None


def main():
    pool, analyst, supported = load('pool'), load('analyst'), load('supported')
    assert len(pool) == len(analyst) == 29729
    assert not pool.duplicated(KEYS).any() and not analyst.duplicated(KEYS).any()
    assert not supported.duplicated(KEYS[:3]).any()
    data = pool.merge(analyst, on=KEYS, how='outer', validate='one_to_one', indicator=True)
    assert data['_merge'].eq('both').all()
    data = data.drop(columns='_merge')
    data['analyst_min2'] = flag(data.analyst_min2)
    supported['proposed_overlap_clean'] = flag(supported.proposed_overlap_clean)
    supported['all_12_events_min2'] = flag(supported.all_12_events_min2)
    data = data.merge(supported, on=KEYS[:3], how='left', validate='many_to_one', indicator=True)
    data['in_8_4_snapshot'] = data['_merge'].eq('both')
    data['clock'] = data.anntims.map(parse)
    data['band'] = data.clock.map(lambda x: x is not None and time(9, 30) <= x <= time(15))
    stage_filters = {
        'V1_ALL_CAPPED_EVENT_ROWS': pd.Series(True, index=data.index),
        'V1_8PRE_4POST_STOCKS': data.in_8_4_snapshot,
        'V1_8_4_OVERLAP_CLEAN': data.in_8_4_snapshot & data.proposed_overlap_clean.eq(True),
        'V1_8_4_OVERLAP_CLEAN_ALL12MIN2': data.in_8_4_snapshot & data.proposed_overlap_clean.eq(True) & data.all_12_events_min2.eq(True),
    }
    counts, stock_support = [], []
    for stage, keep in stage_filters.items():
        stage_data = data[keep]
        for (wave, tier, side), base in data.groupby(['wave_id', 'provisional_tier', 'event_side']):
            part = stage_data[(stage_data.wave_id == wave) & (stage_data.provisional_tier == tier) & (stage_data.event_side == side)]
            band = part[part.band]
            valid = band[band.analyst_min2]
            counts.append(dict(stage=stage, wave_id=wave, tier=tier, sample_period=side, snapshot_row_denominator=len(part), nominal_clock_rows=len(band), nominal_clock_rows_with_min2=len(valid), stocks_with_nominal_clock=band.permno.nunique(), stocks_with_nominal_clock_min2=valid.permno.nunique()))
        for (wave, tier), full_group in data.groupby(['wave_id', 'provisional_tier']):
            part = stage_data[(stage_data.wave_id == wave) & (stage_data.provisional_tier == tier)]
            band = part[part.band & part.analyst_min2]
            pre = set(band.loc[band.event_side == 'PRE', 'permno'])
            post = set(band.loc[band.event_side == 'POST', 'permno'])
            stock_support.append(dict(stage=stage, wave_id=wave, tier=tier, stock_denominator=part.permno.nunique(), nominal_min2_PRE_stocks=len(pre), nominal_min2_POST_stocks=len(post), nominal_min2_stocks_with_both_PRE_POST=len(pre & post), interpretation='AT_LEAST_ONE_EACH_SIDE_NOT_NUMERIC_RANK_OR_FINAL_ELIGIBILITY'))
    count_table = pd.DataFrame(counts)
    stock_table = pd.DataFrame(stock_support)
    count_table.to_csv(OUT/'v1_nominal_clock_event_counts.csv', index=False)
    stock_table.to_csv(OUT/'v1_nominal_clock_stock_support.csv', index=False)
    summary = {
        'status': 'V1_CAPPED_METADATA_NOMINAL_CLOCK_DIAGNOSTIC_EXECUTED',
        'source_rows': len(data), 'stock_wave_units': len(data[KEYS[:3]].drop_duplicates()),
        'parseable_clock_strings': int(data.clock.notna().sum()),
        'nominal_0930_1500_source_rows': int(data.band.sum()),
        'nominal_0930_1500_with_event_min2': int((data.band & data.analyst_min2).sum()),
        'stage_totals': count_table.groupby('stage')[['snapshot_row_denominator','nominal_clock_rows','nominal_clock_rows_with_min2']].sum().astype(int).to_dict('index'),
        'stock_support': stock_table.to_dict('records'),
        'input_manifest': {k: {'path': str(MD/v[0]), 'sha256': v[1], 'columns': v[2]} for k,v in SPECS.items()},
        'unknown_overlap_for_non_8_4_stocks_not_assumed_clean': True,
        'no_source_versions_pooled': True,
        'scientific_boundaries': [
            'Not a timezone conversion or verified market session census',
            'Not a complete history: original metadata snapshot caps selection at 8 PRE and 4 POST',
            'Rows are source-period candidates, not certified distinct public-release events',
            'No upper bound on another roster/window or the full conversion universe',
            'No new final population, clock, analyst/SUE or inference rule is adopted',
            'No raw financial fields, SCC, provider request, purchase or empirical outcome used',
        ],
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (OUT/'V1_NOMINAL_CLOCK_RECEIPT.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k: v for k,v in summary.items() if k not in ['input_manifest','stock_support']}, indent=2))
    print(stock_table.loc[stock_table.stage.eq('V1_8_4_OVERLAP_CLEAN')].to_string(index=False))


if __name__ == '__main__':
    main()
