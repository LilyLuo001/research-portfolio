"""Cloud-only aggregate profile and explicitly conditional whole-target arithmetic."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics
import time


def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def profile(root):
    db=sqlite3.connect((root/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    attempts=[dict(x) for x in db.execute('select * from attempts')]
    meta=dict(db.execute('select key,value from meta'));db.close()
    policy=read(root/'policy.json')
    prices={'Luna':(.1,.5),'Kimi':(2.3,11.5),'Astra':(12.5,50.)}
    model={}
    upgrade=root/'control/RATE_UPGRADE_LAUNCH_PUBLIC.json'
    upgrade_at=dt.datetime.fromisoformat(read(upgrade)['at_utc']).timestamp() if upgrade.exists() else float('inf')
    for leg,(ip,op) in prices.items():
        rows=[x for x in attempts if x['leg']==leg]
        actual=[];latencies=[];recent=[]
        for x in rows:
            d=json.loads(x['detail']);u=d.get('usage')
            if u:actual.append(u)
            if x['result_path']:
                p=root/x['result_path'];assert sha(p)==x['result_sha']
                latencies.append(max(0,p.stat().st_mtime-x['forwarded']))
                if x['forwarded']>=upgrade_at:recent.append((x['forwarded'],p.stat().st_mtime))
        ni=sum(x.get('prompt_tokens',0) for x in actual);no=sum(x.get('completion_tokens',0) for x in actual)
        known_cost=(ni*ip+no*op)/1e6
        model[leg]={'physical_attempts':len(rows),'unique_claimed_contexts':len({x['context'] for x in rows}),
            'states':dict(Counter(x['state'] for x in rows)),'returned_usage_requests':len(actual),
            'input_tokens':ni,'output_tokens':no,'priced_usage_usd_not_invoice':known_cost,
            'configured_input_usd_per_million':ip,'configured_output_usd_per_million':op,
            'reserved_usd':sum(x['dollars_nano'] for x in rows)/1e9,
            'mean_priced_usage_usd_per_returned_request':known_cost/len(actual) if actual else None,
            'mean_upper_tokens_per_request':statistics.mean(x['tokens'] for x in rows) if rows else None,
            'request_latency_median_seconds':statistics.median(latencies) if latencies else None,
            'observed_limit_token_headers':sorted({str(json.loads(x['detail']).get('rate_headers',{}).get('x-ratelimit-limit-tokens')) for x in rows if json.loads(x['detail']).get('rate_headers')}),
            'post_rate_upgrade_completed_requests':len(recent)}
        if len(recent)>=2:
            sec=max(x[1] for x in recent)-min(x[0] for x in recent)
            model[leg].update(post_rate_upgrade_span_seconds=sec,post_rate_upgrade_completions_per_hour=len(recent)*3600/sec)
    manifests=[];cpu=[]
    for b in sorted((root/'preparation').glob('batch*')):
        if b.is_dir() and (b/'BATCH_MANIFEST_PUBLIC.json').exists():
            manifests.append(read(b/'BATCH_MANIFEST_PUBLIC.json'))
            if (b/'CPU_RULE_RECEIPT_PUBLIC.json').exists():cpu.append(read(b/'CPU_RULE_RECEIPT_PUBLIC.json'))
    n=sum(x['input_rows_processed'] for x in cpu);seconds=sum(x['wall_seconds'] for x in cpu)
    rules_rps=n/seconds
    cost=model['Luna']['mean_priced_usage_usd_per_returned_request']
    rph=model['Luna'].get('post_rate_upgrade_completions_per_hour')
    scenarios=[]
    for u in [500_000,5_000_000,50_000_000,500_000_000]:
        scenarios.append({'hypothetical_new_unique_Luna_inputs':u,
            'Luna_priced_usage_usd_if_current_mix_persists':u*cost if cost else None,
            'Luna_continuous_channel_days_if_current_rate_persists':u/rph/24 if rph else None,
            'excludes_Kimi_Astra_VM_storage_IO_retries':True})
    projection=root/'projection/batch0001/PHYSICAL_PROJECTION_PUBLIC.json'
    return {'status':'bounded_live_profile_not_global_completion_quote','at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'requested_approximate_commercial_physical_rows':500_000_000,
        'global_authoritative_physical_total':None,'global_unique_texts_needing_semantics':None,
        'verified_US_canonical_catalog_rows':204_774_035,
        'Description_raw_rows_existing_inventory':298_673_078,'Records_footer_rows_existing_inventory':356_449_214,
        'these_denominators_are_nonadditive':True,
        'physical_rows_prepared':manifests[-1]['cumulative_physical_rows'],
        'new_unique_contexts_prepared':manifests[-1]['cumulative_new_unique_contexts'],
        'old_or_duplicate_rows_not_reinferred':manifests[-1]['cumulative_physical_rows']-manifests[-1]['cumulative_new_unique_contexts'],
        'local_cache_or_exclusion_fraction_not_global_ratio':True,
        'models':model,'pilot_reserved_usd':sum(x['dollars_nano'] for x in attempts)/1e9,
        'usage_prices_are_existing_pinned_configuration_not_new_retail_quote':True,'invoice_verified':False,
        'first100_physical_projection_exists':projection.exists(),
        'first100_projection_sha256':sha(projection) if projection.exists() else None,
        'CPU':{'new_unique_inputs':n,'wall_seconds':seconds,'short_run_candidates_per_second':rules_rps,
               'hypothetical_500m_single_process_CPU_kernel_days':500e6/rules_rps/86400,
               'not_end_to_end_or_sustained_burst_VM_forecast':True,'model_API_cost':0},
        'conditional_scenarios_not_forecast':scenarios,
        'full_scope_cost_formula':'CPU+storage+joins+U_L*(I_L*0.1+O_L*0.5)/1e6+U_K*(I_K*2.3+O_K*11.5)/1e6+bounded_Astra; U_L/U_K are true missing unique inputs, NOT 500m physical rows.',
        'frozen_pilot_budget_usd':150,'global_hold':meta.get('global_hold'),
        'next_pricing_requirements':['Authoritative non-overlapping physical-row manifest','Full-target content-hash count and per-field reusable coverage','Sustained CPU/IO benchmark rather than a seconds-long burst','Measured low-cost routing rate after cache; no automatic all-unique Kimi run']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=profile(a.directory);a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'path':str(a.out),'sha256':sha(a.out),'physical_prepared':result['physical_rows_prepared'],
        'Luna':result['models']['Luna'],'pilot_reserved_usd':result['pilot_reserved_usd'],'CPU':result['CPU']}))
if __name__=='__main__':main()
