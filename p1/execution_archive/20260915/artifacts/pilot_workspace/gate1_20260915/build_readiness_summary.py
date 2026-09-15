"""Recompute metadata denominators without financial/quotation response values."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import time
from pathlib import Path

OUT=Path(__file__).resolve().parent
BASE=OUT.parent/'missing_data_round_20260914'
ACQ=BASE/'databento_final_acquisition'
INPUTS={}
def read(path, columns):
    INPUTS[str(path.relative_to(OUT.parent))]=hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(newline='') as f:
        return [{k:r[k] for k in columns} for r in csv.DictReader(f)]
def write(name,rs):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def yes(s):return s.lower()=='true'

events=read(BASE/'union_v2_earnings_inputs/selected_event_metadata.csv', ['association_id','wave_id','permno','sample_period','tier','pends','announcement_date','announcement_times_all','mapping_status','symbol_status','analyst_count_90d','announcement_cutoff','post_20_session_threshold'])
assert len({r['association_id'] for r in events})==len(events)
cal=read(BASE/'union_v2_event_calendar_actions/event_calendar_and_action_flags.csv',['association_id','announcement_date_is_observed_session','distribution_flag','price_factor_change_flag','share_factor_change_flag'])
rdq=read(BASE/'union_v2_compustat_rdq_crosscheck/event_rdq_crosscheck.csv',['association_id','rdq_status','rdq_equals_ibes_date'])
pool=read(BASE/'analysis_ready_acquisition/full_support_overlap_analyst_intersection.csv',['wave_id','permno','provisional_tier','proposed_overlap_clean','all_12_events_min2','clean_and_analyst12'])
roster=read(BASE/'analysis_ready_acquisition/PILOT_STOCKS_ACQUISITION_UNION_V2.csv',['wave_id','permno','tier','final_analysis_eligibility','split_basis_status','report_dates','denominator_date','announcement_cutoff'])
summary=[]
for wave in sorted({e['wave_id'] for e in events}):
    for tier in ['HIGH','LOW']:
        es=[e for e in events if e['wave_id']==wave and e['tier']==tier]
        ps=[p for p in pool if p['wave_id']==wave and p['provisional_tier'].upper()==tier]
        summary.append(dict(wave_id=wave,tier=tier,acquired_stock_wave=len({e['permno'] for e in es}),associations=len(es),pre=sum(e['sample_period']=='PRE' for e in es),post=sum(e['sample_period']=='POST' for e in es),analyst_min2_associations=sum(int(e['analyst_count_90d'])>=2 for e in es),full_pool_stock_wave=len(ps),proposed_clean_all12_min2=sum(yes(p['clean_and_analyst12']) for p in ps)))
write('support_by_wave_tier.csv',summary)
clock=Counter()
for e in events:
    ts=e['announcement_times_all'].split(';')
    try:
        parsed=[time.fromisoformat(t) for t in ts]
        clock['one_parseable_time' if len(parsed)==1 else 'multiple_parseable_times']+=1
    except ValueError:clock['missing_or_unparseable']+=1

headers=read(OUT/'job_symbol_header_audit.csv',['job_id','dataset','symbol','file_status','mapping_status'])
hd={(r['job_id'],r['symbol']):r for r in headers}
coremap=read(ACQ/'core_grouped_job_map.csv',['job_id','atomic_request_id','symbol'])
atom={r['atomic_request_id']:r for r in coremap}
em=read(ACQ/'event_request_map.csv',['request_id','association_id','sample_period','symbol_role','leg'])
event_flags=defaultdict(list); legcounts=Counter(); gaps=[]
for e in em:
    m=atom[e['request_id']]; h=hd[(m['job_id'],m['symbol'])]
    ok=h['file_status']=='HEADER_CONTRACT_MATCH' and h['mapping_status']=='DATE_VALID_UNIQUE'
    event_flags[e['association_id']].append(ok)
    legcounts[(e['sample_period'],e['symbol_role'],e['leg'],str(ok))]+=1
    if not ok:
        gaps.append(dict(association_id=e['association_id'],sample_period=e['sample_period'],symbol_role=e['symbol_role'],leg=e['leg'],job_id=m['job_id'],symbol=m['symbol'],file_status=h['file_status'],mapping_status=h['mapping_status']))
if gaps:write('core_mapping_gap_locators.csv',gaps)
unresolved=Counter((h['dataset'],h['symbol'],h['file_status'],h['mapping_status']) for h in headers if not(h['file_status']=='HEADER_CONTRACT_MATCH' and h['mapping_status']=='DATE_VALID_UNIQUE'))
write('unresolved_symbol_summary.csv',[dict(dataset=k[0],symbol=k[1],file_status=k[2],mapping_status=k[3],job_symbol_instances=v) for k,v in sorted(unresolved.items())])
write('core_logical_leg_mapping_support.csv',[dict(sample_period=k[0],symbol_role=k[1],leg=k[2],header_mapping_pass=k[3],logical_legs=v) for k,v in sorted(legcounts.items())])
assert set(event_flags)=={e['association_id'] for e in events}
assert all(len(v)==8 for v in event_flags.values())
write('feed_header_summary.csv',[dict(dataset=d,job_symbol_rows=sum(h['dataset']==d for h in headers),mapped=sum(h['dataset']==d and h['file_status']=='HEADER_CONTRACT_MATCH' and h['mapping_status']=='DATE_VALID_UNIQUE' for h in headers),unresolved=sum(h['dataset']==d and not(h['file_status']=='HEADER_CONTRACT_MATCH' and h['mapping_status']=='DATE_VALID_UNIQUE') for h in headers)) for d in sorted({h['dataset'] for h in headers})])
keys=Counter((e['permno'],e['announcement_date']) for e in events)
stock_waves=defaultdict(set)
for e in events:stock_waves[e['permno']].add(e['wave_id'])
receipt=dict(status='DATA_READINESS_ASSESSMENT_NOT_LEGACY_GATE1_PASS',associations=len(events),stock_wave_units=len(roster),unique_permnos=len(stock_waves),waves=len({e['wave_id'] for e in events}),periods=dict(Counter(e['sample_period'] for e in events)),unique_permno_release_date_keys=len(keys),reused_key_extra_associations=sum(n-1 for n in keys.values()),stocks_in_multiple_waves=sum(len(ws)>1 for ws in stock_waves.values()),unique_announcement_dates=len({e['announcement_date'] for e in events}),clock_parse_counts=dict(clock),certified_release_timezone='NOT_ESTABLISHED',session_and_RTH60='UNKNOWN_NOT_ZERO',endpoint_quote_coverage='NOT_ASSESSED',source_mapping_status=dict(Counter(e['mapping_status'] for e in events)),date_valid_symbol_status=dict(Counter(e['symbol_status'] for e in events)),analyst_min2_associations=sum(int(e['analyst_count_90d'])>=2 for e in events),observed_session_dates=sum(yes(e['announcement_date_is_observed_session']) for e in cal),distribution_flag_associations=sum(yes(e['distribution_flag']) for e in cal),rdq_status=dict(Counter(e['rdq_status'] for e in rdq)),rdq_same_date=sum(yes(e['rdq_equals_ibes_date']) for e in rdq),core_logical_legs=len(em),core_all8_header_mapping_supported_associations=sum(all(v) for v in event_flags.values()),core_header_mapping_incomplete_associations=sum(not all(v) for v in event_flags.values()),final_eligibility=dict(Counter(r['final_analysis_eligibility'] for r in roster)),split_basis_status=dict(Counter(r['split_basis_status'] for r in roster)),holdings_reports_strictly_pre_cutoff=sum(all(d<r['announcement_cutoff'] for d in r['report_dates'].split(';')) for r in roster),denominator_strictly_pre_cutoff=sum(r['denominator_date']<r['announcement_cutoff'] for r in roster),pre_dates_strictly_before_cutoff=sum(e['announcement_date']<e['announcement_cutoff'] for e in events if e['sample_period']=='PRE'),post_dates_at_or_after_recorded_20session_threshold=sum(e['announcement_date']>=e['post_20_session_threshold'] for e in events if e['sample_period']=='POST'),economic_event_deduplication='NOT_CERTIFIED_DATE_KEYS_ONLY',financial_or_quote_values_read=False,input_hashes=INPUTS,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
receipt.pop('financial_or_quote_values_read')
receipt['raw_eps_forecast_price_quote_return_sources_opened']=False
receipt['existing_metadata_containers_hashed_and_csv_parsed_before_column_projection']=True
receipt['liquidity_or_ownership_values_analyzed_or_returned']=False
(OUT/'readiness_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='input_hashes'},indent=2))
