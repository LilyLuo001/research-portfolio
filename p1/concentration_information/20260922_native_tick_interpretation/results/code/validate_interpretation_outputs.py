#!/usr/bin/env python3
"""Public aggregate-output checks; never opens SCC DBNs."""
import csv, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def rows(name):
    with (ROOT/name).open() as f: return list(csv.DictReader(f))
act=rows('ACTIVITY_DECOMPOSITION.csv'); direction=rows('DIRECTION_SOURCE_SUMMARY.csv'); resp=rows('WITHIN_BIN_RESPONSE_SUMMARY.csv')
assert len(act)==96 and len(direction)==36 and len(resp)==24640
assert {r['row_type'] for r in act}=={'WINDOW','MATCHED_RTH_MINUS_CONTROL'}
assert all(r['category']!='UNKNOWN_STOCK_OR_SPY' or r['background_pairs'] not in ('','nan') for r in act if r['row_type']=='WINDOW')
assert all(r['native_trades'] and float(r['native_share'])>=0 for r in direction)
assert {'NATIVE_ONLY','NATIVE_PLUS_MIDPOINT'}=={r['variant'] for r in resp}
assert {'B','S'}=={r['direction'] for r in resp}
assert {'WITHIN_WINDOW_5M','RTH_MINUS_CONTROL_COMMON_5M'}=={r['comparison'] for r in resp}
assert {'50us','200us','1000us','10000us','1s','5s','60s'}=={r['horizon_label'] for r in resp}
for r in act:
    if r['row_type']=='MATCHED_RTH_MINUS_CONTROL':
        e=float(r['excess_per_1000_stock_difference']); a=float(r['fixed_order_level_term_per_1000_stock']); b=float(r['fixed_order_activity_term_per_1000_stock'])
        assert math.isclose(e,a+b,abs_tol=1e-10), r
assert 'post_quote_age_ms' not in resp[0]
assert {'age_since_valid_bbo_message_ms','age_since_actual_bbo_change_ms'}.issubset({r['metric'] for r in resp})
cross=[r for r in resp if r['comparison']=='RTH_MINUS_CONTROL_COMMON_5M']
assert cross and all((r['rth_paired_n_sum'] and r['control_paired_n_sum'] and r['rth_unpaired_n_sum'] and r['control_unpaired_n_sum']) or (r['window']=='XOM_JAN' and r['support_bins']=='0' and r['estimate']=='') for r in cross)
xom=[r for r in cross if r['window']=='XOM_JAN']
assert len(xom)==2464 and all(r['support_bins']=='0' and r['estimate']=='' for r in xom)
print('PASS: aggregate cardinalities, native B/S separation, horizons, UNKNOWN correction, matched-bin rows, correctly named BBO ages, separate cross-day support, and arithmetic decomposition.')
