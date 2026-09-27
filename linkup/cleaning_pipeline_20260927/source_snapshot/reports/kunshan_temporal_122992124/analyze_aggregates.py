#!/usr/bin/env python3
import json, math
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parent
REPORT=json.loads((ROOT/'temporal_risk_report.json').read_text())
O=REPORT['overall_usa']

def rate(n,d): return None if not d else n/d

def countpct(n,d): return {'numerator':int(n),'denominator':int(d),'fraction':rate(n,d),'percent':None if not d else 100*n/d}

def rows(name): return pq.read_table(ROOT/name).to_pylist()

def endpoint(prefix):
    valid=O[prefix+'_interval_valid']; records=O['records']
    same=O[prefix+'_same_quarter']; crossq=O[prefix+'_cross_quarter_same_year']; crossy=O[prefix+'_cross_year']
    missing=O[prefix+'_checked_missing'] if prefix=='last' else O['delete_missing']
    return {
      'record_denominator':int(records),
      'valid':countpct(valid,records), 'endpoint_missing':countpct(missing,records),
      'negative_interval':countpct(O[prefix+'_interval_negative'],records),
      'endpoint_after_snapshot':countpct(O[prefix+'_after_snapshot'],records),
      'created_after_snapshot':countpct(O['created_after_snapshot'],records),
      'same_quarter':countpct(same,valid),
      'cross_quarter_including_cross_year':countpct(crossq+crossy,valid),
      'cross_quarter_same_year':countpct(crossq,valid), 'cross_year':countpct(crossy,valid),
      'nov30_2022': {'among_all_valid':countpct(O[prefix+'_cross_nov'],valid),
                     'conditional_on_valid_pre_boundary_start':countpct(O[prefix+'_cross_nov'],O[prefix+'_pre_nov_valid'])},
      'jan01_2023_sensitivity': {'among_all_valid':countpct(O[prefix+'_cross_jan'],valid),
                     'conditional_on_valid_pre_boundary_start':countpct(O[prefix+'_cross_jan'],O[prefix+'_pre_jan_valid'])},
    }

def cohort_row(r, prefix='last'):
    valid=r[prefix.upper()+'_INTERVAL_VALID']; pre=r[prefix.upper()+'_PRE_NOV_VALID']; cross=r[prefix.upper()+'_CROSS_NOV']
    return {'records':int(r['RECORDS']),'valid':int(valid),'pre_nov_valid':int(pre),'cross_nov':int(cross),
            'cross_nov_rate_conditional':rate(cross,pre),'share_all_cross_nov':rate(cross,O[prefix+'_cross_nov']),
            'share_all_pre_nov_valid':rate(pre,O[prefix+'_pre_nov_valid'])}

years=rows('temporal_risk_by_cohort_year.parquet')
quarters=rows('temporal_risk_by_cohort_quarter.parquet')
yearmap={int(r['CREATED_YEAR']):r for r in years if r['CREATED_YEAR'] is not None}
qmap={str(r['CREATED_QUARTER']):r for r in quarters if r['CREATED_QUARTER'] is not None}

def top_cohorts(rs,keyfield,prefix,n=12):
    cp=prefix.upper(); out=[]
    for r in rs:
        pre=r[cp+'_PRE_NOV_VALID']; cross=r[cp+'_CROSS_NOV']
        if pre:
            out.append({'cohort':str(r[keyfield]), **cohort_row(r,prefix)})
    return sorted(out,key=lambda x:x['cross_nov'],reverse=True)[:n]

companies=rows('temporal_risk_by_company.parquet')
company_null=sum(1 for r in companies if r['RECORD_COMPANY_ID'] is None)
base=[r for r in companies if r['LAST_INTERVAL_VALID']>=100]
base_rates=np.array([r['LAST_CROSS_NOV']/r['LAST_PRE_NOV_VALID'] for r in base if r['LAST_PRE_NOV_VALID']>0],dtype=float)
highrisk_pool=[r for r in base if r['LAST_PRE_NOV_VALID']>=100]

def comp_item(r):
    return {'company_id':None if r['RECORD_COMPANY_ID'] is None else str(r['RECORD_COMPANY_ID']),
      'records':int(r['RECORDS']),'last_valid':int(r['LAST_INTERVAL_VALID']),
      'pre_nov_valid':int(r['LAST_PRE_NOV_VALID']),'cross_nov':int(r['LAST_CROSS_NOV']),
      'cross_nov_rate':rate(r['LAST_CROSS_NOV'],r['LAST_PRE_NOV_VALID']),
      'share_all_cross_nov':rate(r['LAST_CROSS_NOV'],O['last_cross_nov']),
      'share_all_pre_nov_valid':rate(r['LAST_PRE_NOV_VALID'],O['last_pre_nov_valid']),
      'share_all_last_valid':rate(r['LAST_INTERVAL_VALID'],O['last_interval_valid'])}

topcontrib=sorted(base,key=lambda r:r['LAST_CROSS_NOV'],reverse=True)
toprisk=sorted(highrisk_pool,key=lambda r:rate(r['LAST_CROSS_NOV'],r['LAST_PRE_NOV_VALID']) or -1,reverse=True)

def concentration(n):
    rs=topcontrib[:n]
    return {'companies':n,'share_cross_nov':sum(r['LAST_CROSS_NOV'] for r in rs)/O['last_cross_nov'],
      'share_pre_nov_valid':sum(r['LAST_PRE_NOV_VALID'] for r in rs)/O['last_pre_nov_valid'],
      'share_all_last_valid':sum(r['LAST_INTERVAL_VALID'] for r in rs)/O['last_interval_valid']}

states=rows('temporal_risk_by_state.parquet')
def state_item(r):
    return {'state':r['STATE'],'records':int(r['RECORDS']),'share_usa_records':rate(r['RECORDS'],O['records']),
      'pre_nov_valid':int(r['LAST_PRE_NOV_VALID']),'cross_nov':int(r['LAST_CROSS_NOV']),
      'cross_nov_rate':rate(r['LAST_CROSS_NOV'],r['LAST_PRE_NOV_VALID']),
      'share_all_cross_nov':rate(r['LAST_CROSS_NOV'],O['last_cross_nov'])}
state_records=sorted(states,key=lambda r:r['RECORDS'],reverse=True)
state_risk=sorted([r for r in states if r['LAST_PRE_NOV_VALID']>=100],key=lambda r:rate(r['LAST_CROSS_NOV'],r['LAST_PRE_NOV_VALID']) or -1,reverse=True)

out={
 'status':'complete_from_existing_aggregates_no_raw_rescan',
 'scope':{'description_files':1358,'description_file_selection':'available downloaded subset; order not established random and not full supplier corpus',
   'description_distinct_keys':REPORT['global_key_match']['description_distinct_keys'],
   'matched_keys':REPORT['global_key_match']['matched_keys'],'orphan_keys':REPORT['global_key_match']['orphan_keys'],
   'usa_matched_records':int(O['records']),'country_filter':'COUNTRY == USA before all supplied company/state/cohort aggregations'},
 'temporal':{'main_endpoint_created_to_last_checked':endpoint('last'),
             'alternative_endpoint_created_to_delete_date':endpoint('delete'),
             'cutoffs_utc':REPORT['cutoffs_utc'],
             'interpretation':'Observed vendor envelope only; not description-text validity and calendar cutoffs are not causal dates.'},
 'cohort_focus':{
   'created_year_2022':{'last':cohort_row(yearmap[2022],'last'),'delete':cohort_row(yearmap[2022],'delete')},
   'created_2022_q3':{'last':cohort_row(qmap['2022-07-01'],'last'),'delete':cohort_row(qmap['2022-07-01'],'delete')},
   'created_2022_q4':{'last':cohort_row(qmap['2022-10-01'],'last'),'delete':cohort_row(qmap['2022-10-01'],'delete'),
      'note':'Quarter straddles Nov 30; pre-boundary denominator uses exact CREATED timestamps, not all Q4 records.'},
   'top_years_by_last_cross_nov_contribution':top_cohorts(years,'CREATED_YEAR','last'),
   'top_quarters_by_last_cross_nov_contribution':top_cohorts(quarters,'CREATED_QUARTER','last')},
 'company':{
   'company_rows':len(companies),'null_company_id_rows':company_null,'company_names_available':False,
   'overall_ad_weighted_cross_nov_rate':rate(O['last_cross_nov'],O['last_pre_nov_valid']),
   'base_threshold':'LAST_INTERVAL_VALID >= 100','base_firms':len(base),
   'firm_equal_weight_rate_distribution_base_with_nonzero_pre_nov':{'firms':len(base_rates),'p25':float(np.quantile(base_rates,.25)),
      'median':float(np.median(base_rates)),'p75':float(np.quantile(base_rates,.75)),'p90':float(np.quantile(base_rates,.9))},
   'high_risk_sensitivity_threshold':'LAST_INTERVAL_VALID >= 100 and LAST_PRE_NOV_VALID >= 100',
   'high_risk_pool_firms':len(highrisk_pool),'top_high_risk_rate_company_ids':list(map(comp_item,toprisk[:20])),
   'top_crossing_contributor_company_ids':list(map(comp_item,topcontrib[:20])),
   'concentration_comparison':[concentration(n) for n in (10,50,100)]},
 'state':{'state_labels':len(states),'state_semantics':'All rows passed COUNTRY == USA; STATE may include null, territories, or nonstandard labels and is not an independent country test.',
          'top_by_records':[state_item(r) for r in state_records[:20]],
          'top_cross_nov_rate_min100_preboundary':[state_item(r) for r in state_risk[:20]]},
 'limitations':{'description_history_semantics':'unconfirmed','occupation_mapping':'pending','duration_quantiles':'pending',
                'company_names':'not present in aggregate; IDs only','reopened_or_gap_periods':'unobservable'}
}
# Strong conservation checks for delivery.
assert O['last_same_quarter']+O['last_cross_quarter_same_year']+O['last_cross_year']==O['last_interval_valid']
assert O['delete_same_quarter']+O['delete_cross_quarter_same_year']+O['delete_cross_year']==O['delete_interval_valid']
assert REPORT['global_key_match']['matched_keys']+REPORT['global_key_match']['orphan_keys']==REPORT['global_key_match']['description_distinct_keys']
(ROOT/'formal_report_metrics.json').write_text(json.dumps(out,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'overall_last':out['temporal']['main_endpoint_created_to_last_checked'],
 '2022':out['cohort_focus']['created_year_2022']['last'],
 '2022Q3':out['cohort_focus']['created_2022_q3']['last'],
 '2022Q4':out['cohort_focus']['created_2022_q4']['last'],
 'company_distribution':out['company']['firm_equal_weight_rate_distribution_base_with_nonzero_pre_nov'],
 'concentration':out['company']['concentration_comparison'],
 'top_states':out['state']['top_by_records'][:5]},indent=2))
