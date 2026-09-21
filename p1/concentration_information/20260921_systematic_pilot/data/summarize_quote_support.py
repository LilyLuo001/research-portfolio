"""Summarize permitted booleans only; never equate file cells with events."""
import csv,json,sys
from pathlib import Path
from collections import defaultdict

root=Path(sys.argv[1])
data=json.loads((root/'data/QUOTE_SUPPORT_RESULTS.json').read_text())
groups=defaultdict(list)
for r in data['rows']:
    groups[r['variant'],r['symbol'],r['dataset'],r['file_path']].append(r)
summary=defaultdict(lambda: {'candidate_files':0,'mapped_files':0,'one_file_all_six_observed_noncrossed':0,'one_file_all_six_in_header_and_noncrossed':0})
contract=json.loads((root/'DIAGNOSTIC_CONTRACT.json').read_text())
datasets=sorted({r['dataset'] for r in data['rows']})
for v in contract['variants']:
    for symbol in ['SPY','QQQ']:
        for dataset in datasets: summary[v['variant'],symbol,dataset]
for (v,s,d,p),rs in groups.items():
    x=summary[v,s,d]; x['candidate_files']+=1
    x['mapped_files']+=all(r['mapping_ids_count']==1 for r in rs)
    valid=len(rs)==6 and all(r['observed_state'] and r['noncrossed_snapshot'] is True for r in rs)
    x['one_file_all_six_observed_noncrossed']+=valid
    x['one_file_all_six_in_header_and_noncrossed']+=valid and all(r['baseline_lookback_in_header'] if r['horizon_minutes']==0 else r['target_in_header_interval'] for r in rs)
out=[dict(variant=v,symbol=s,dataset=d,**x,interpretation='SINGLE_FILE_DIAGNOSTIC_NOT_LIVE_QUOTE_OR_BASKET_CERTIFICATION') for (v,s,d),x in sorted(summary.items())]
with (root/'QUOTE_SUPPORT_TABLE.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
print(json.dumps({'table_rows':len(out),'variant_symbol_pairs_with_any_single_file_all_six_in_header_noncrossed':len({(r['variant'],r['symbol']) for r in out if r['one_file_all_six_in_header_and_noncrossed']>0}), 'not_an_analysis_sample_size':True}))
