#!/usr/bin/env python3
from pathlib import Path
import hashlib, json
import pandas as pd

BASE=Path('/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot')
OUT=BASE/'step4_readiness_early_stop_20260915'
NOM=BASE/'pilot_uncapped_metadata_20260915/corrected_v2/scc/full/nominal_support_before_vs_cached_min2.csv'
NOM_RECEIPT=BASE/'pilot_uncapped_metadata_20260915/corrected_v2/scc/full/nominal_support_receipt.json'
CORRECTED_RECEIPT=BASE/'pilot_uncapped_metadata_20260915/corrected_v2/EXECUTION_RECEIPT.json'
LEG=BASE/'gate1_20260915/support_by_wave_tier.csv'
GAP=BASE/'source_wave_gap_resolution_20260915/EXECUTION_RECEIPT.json'
W006=BASE/'source_wave_gap_resolution_20260915/w006_attribution_receipt.json'
ADJ=BASE/'source_wave_gap_resolution_20260915/adjusted_detail_w002_high_receipt.json'
PACKAGE=BASE/'package_provenance_inventory_20260915/package_readiness_ledger.csv'
CLOCK=BASE/'source_clock_evidence_20260915/CLOCK_EVIDENCE_RECEIPT.json'
CAL=BASE/'exchange_calendar_20260915/CALENDAR_RECEIPT.json'
PRIMARY=BASE/'primary_package_checks_20260915/FINDINGS.md'
MAIN=['W002','W013','W021','W025']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

d=pd.read_csv(NOM,dtype=str)
for c in ['stocks_with_nominal_pre_and_post_before_cached_min2','stocks_with_nominal_pre_and_post_cached_min2_both']:
    d[c]=pd.to_numeric(d[c],errors='raise').astype(int)
legacy=pd.read_csv(LEG,dtype=str); legacy['proposed_clean_all12_min2']=pd.to_numeric(legacy['proposed_clean_all12_min2'],errors='raise').astype(int)
rows=[]
for w in MAIN:
    r={'wave_id':w,'unapproved_heuristic_two_stocks_per_tier_threshold':2}
    for tier in ['high','low']:
        allr=d[(d.wave_id==w)&d.provisional_tier.str.lower().eq(tier)&d.overlap_status.eq('ALL_OVERLAP_STATUSES')]
        clean=d[(d.wave_id==w)&d.provisional_tier.str.lower().eq(tier)&d.overlap_status.eq('PROPOSED_CLEAN_TRUE')]
        r[f'{tier}_all_status_nominal_both_no_min2']=int(allr.stocks_with_nominal_pre_and_post_before_cached_min2.sum())
        r[f'{tier}_all_status_nominal_both_cached_min2']=int(allr.stocks_with_nominal_pre_and_post_cached_min2_both.sum())
        r[f'{tier}_proposed_clean_nominal_both_no_min2']=int(clean.stocks_with_nominal_pre_and_post_before_cached_min2.sum())
        r[f'{tier}_proposed_clean_nominal_both_cached_min2']=int(clean.stocks_with_nominal_pre_and_post_cached_min2_both.sum())
        q=legacy[(legacy.wave_id==w)&legacy.tier.str.lower().eq(tier)]
        r[f'{tier}_legacy_clean_all12_min2_full_pool']=int(q.proposed_clean_all12_min2.sum())
    r['all_status_no_min2_two_per_tier_diagnostic']=r['high_all_status_nominal_both_no_min2']>=2 and r['low_all_status_nominal_both_no_min2']>=2
    r['all_status_cached_min2_two_per_tier_diagnostic']=r['high_all_status_nominal_both_cached_min2']>=2 and r['low_all_status_nominal_both_cached_min2']>=2
    r['proposed_clean_no_min2_two_per_tier_diagnostic']=r['high_proposed_clean_nominal_both_no_min2']>=2 and r['low_proposed_clean_nominal_both_no_min2']>=2
    r['all_status_no_min2_nonempty_both_tiers']=r['high_all_status_nominal_both_no_min2']>0 and r['low_all_status_nominal_both_no_min2']>0
    r['all_status_cached_min2_nonempty_both_tiers']=r['high_all_status_nominal_both_cached_min2']>0 and r['low_all_status_nominal_both_cached_min2']>0
    r['proposed_clean_no_min2_nonempty_both_tiers']=r['high_proposed_clean_nominal_both_no_min2']>0 and r['low_proposed_clean_nominal_both_no_min2']>0
    r['final_population_clock_common_calendar_support']='NOT_RUN_INPUTS_NOT_FROZEN'
    rows.append(r)
out=pd.DataFrame(rows)
out.to_csv(OUT/'early_stop_support_table.csv',index=False)

ledger=pd.DataFrame([
 ['package_constituents_and_Aw','PARTIAL','Holdings precede recorded bounds for five packages; W002 source confirms four conversions but not predecessor-linked earliest verified announcement.','Freeze source-backed constituent package and earliest independently verified public announcement with uncertainty interval; no global no-earlier-news certificate required.'],
 ['implementation_Iw','PARTIAL','W006 JPM has COB 2022-05-06 completion; W032 retains proposed 11-15, asset-acquisition COB 12-06, and completion 12-09 date types.','Apply the pre-specified legal/operation-date rule to source-specific supported intervals; boundary crossers remain UNKNOWN.'],
 ['pre_announcement_holdings_and_denominator','AVAILABLE_PROVISIONAL_SPLIT_BASIS','All 4,191 saved exposure rows have report-date denominator provenance; 12 predecessor series strictly precede recorded cutoffs.','Validate split/corporate-action basis and multi-series aggregation against the frozen package definition.'],
 ['pro_rata_multi_series','NOT_CERTIFIED','Existing wave aggregation sums predecessor holdings; no signed constituent-level ETF-class pro-rata rule.','Version the constituent-to-successor share allocation/pro-rata metadata before approving tiers for W002/W025.'],
 ['competing_conversion','NOT_CERTIFIED','Recovered99 other-wave sidecar is date-bucket linkage. W006 attribution is 11 DFA-only and 1 both DFA/JPM among 12 pairs.','PI freezes package unit and concurrent-event/exclusion rule; then rerun the already executable SCC metadata join at fund/package level.'],
 ['release_source_clock','PARTIAL_NOT_FULL_APPLICABILITY','Small public comparison supports Eastern/DST for compared rows; XNYS calendar is certified; W002-high four-key applicability remains unknown.','Obtain source-supported timestamp semantics/uncertainty intervals and reclassify uncapped keys against the existing XNYS calendar.'],
 ['analyst_metadata','LOWER_BOUND_ONLY','Separate adjusted-detail family still gives W002-high PRE 0/3 and POST 0/1 observed-min2 keys.','Do not exclude on <2 until source completeness is certified; exact observed >=2 remains a valid lower bound.'],
 ['stock_by_wave_common_calendar_design','NOT_RUN','Legacy/date-bucket diagnostics exist; final population, clock and package rule are not frozen.','After the above inputs are fixed, construct frozen PRE-stock × observed common calendar cells with no extrapolation and test actual rank.'],
 ['quotes_power_effects','NOT_RUN_DEPENDENCIES_NOT_READY','Final population/common-calendar rank is not available; no quote body or response used here.','Do not buy or simulate until final population, source clock and actual design/rank inputs are frozen.'],
],columns=['requirement','status','current_evidence','specific_prerequisite'])
ledger.to_csv(OUT/'readiness_ledger.csv',index=False)

inv={
 'four_main_waves':bool(len(out)==4 and set(out.wave_id)==set(MAIN)),
 'no_final_support_claim':bool(out.final_population_clock_common_calendar_support.eq('NOT_RUN_INPUTS_NOT_FROZEN').all()),
 'all_status_no_min2_nonempty_all_four_main_waves':bool(out.all_status_no_min2_nonempty_both_tiers.all()),
 'cached_min2_nonempty_not_all_four_main_waves':bool(not out.all_status_cached_min2_nonempty_both_tiers.all()),
 'proposed_clean_nonempty_not_all_four_main_waves':bool(not out.proposed_clean_no_min2_nonempty_both_tiers.all()),
 'two_stock_threshold_explicitly_unapproved_heuristic':True,
 'no_quote_power_effect_run':ledger.loc[ledger.requirement=='quotes_power_effects','status'].iloc[0]=='NOT_RUN_DEPENDENCIES_NOT_READY',
}
assert all(inv.values()),inv
receipt={'status':'STEP4_READINESS_DIAGNOSTIC_COMPLETE','decision':'HOLD_DATA_AND_SCIENTIFIC_CHOICE_ACTUAL_RANK_NOT_RUN','invariants':inv,'inputs_sha256':{str(p):sha(p) for p in [NOM,NOM_RECEIPT,CORRECTED_RECEIPT,LEG,GAP,W006,ADJ,PACKAGE,CLOCK,CAL,PRIMARY]},'outputs_sha256':{str(p):sha(p) for p in [OUT/'early_stop_support_table.csv',OUT/'readiness_ledger.csv']},'counts':{'main_waves':4,'main_waves_with_nonempty_both_tiers_all_status_no_min2':int(out.all_status_no_min2_nonempty_both_tiers.sum()),'main_waves_with_nonempty_both_tiers_cached_min2':int(out.all_status_cached_min2_nonempty_both_tiers.sum()),'main_waves_with_nonempty_both_tiers_proposed_clean_no_min2':int(out.proposed_clean_no_min2_nonempty_both_tiers.sum()),'main_waves_passing_unapproved_two_stock_heuristic_all_status_no_min2':int(out.all_status_no_min2_two_per_tier_diagnostic.sum())},'source_authority':{'nominal_aggregate_sha256':sha(NOM),'nominal_receipt_sha256':sha(NOM_RECEIPT),'corrected_v2_execution_receipt_sha256':sha(CORRECTED_RECEIPT),'invalid_initial_run_used':False},'requested_route':'Sol/medium','backend_telemetry':'NOT_OBSERVED','post_response_read':False,'quote_body_read':False,'power_run':False}
(OUT/'EXECUTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
