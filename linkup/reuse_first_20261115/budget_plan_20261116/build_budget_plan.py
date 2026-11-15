"""Recompute the proposed next tranche from public receipts; no cloud or model calls."""
import argparse, datetime as dt, hashlib, json
from pathlib import Path

def build(review, out):
    sources = []
    def read(rel):
        p = review / rel
        data = p.read_bytes()
        sources.append({'source': 'external_public:' + rel, 'sha256': hashlib.sha256(data).hexdigest()})
        return json.loads(data)
    live = read('budget_plan_20261116/AZURE_CURRENT_READONLY_PUBLIC.json')
    index = read('budget_plan_20261116/CLOUD_INDEX_READONLY_PUBLIC.json')
    assets = read('reuse_audit_20261116/RATE_AND_REUSE_ADDENDUM_PUBLIC.json')['confirmed_completed_assets']
    benchmark = read('reuse_audit_20261116/COST_TIME_SCOPE_CORRECTION_PUBLIC.json')['actual_benchmark']
    kimi = read('azure_gpu_launch_20261115/ACTUAL_WORKLOAD_COST_PUBLIC.json')
    kimi_price = read('azure_gpu_launch_20261115/K31_PUBLIC_API_PRICE_SUPPLEMENT_PUBLIC.json')
    luna_price = read('reuse_first_20261115/LUNA_AZURE_PRICE_READONLY_PUBLIC.json')
    read('budget_plan_20261116/VM_RETAIL_PRICE_READONLY_PUBLIC.json')
    html = review / 'reuse_first_20261115/LUNA_AZURE_PRICE_SOURCE_PUBLIC.html'
    sources.append({'source': 'external_public:reuse_first_20261115/LUNA_AZURE_PRICE_SOURCE_PUBLIC.html', 'sha256': hashlib.sha256(html.read_bytes()).hexdigest()})
    rows = live['cost_query']['rows']
    assert not live['cost_query']['has_next_page']
    assert {x['Currency'] for x in rows} == {'USD'}
    posted = sum(x['Cost'] for x in rows)
    selected = {name: sum(x['Cost'] for x in rows if x['ResourceId'] == name) for name in ['rg-linkup','vm-linkup-transfer','stlinkup70d455c0261104']}
    rates = {'Luna': {'input': .1, 'output': .5}, 'Kimi': {'input': 2.3, 'output': 11.5}, 'Astra': {'input': 10., 'output': 50.}}
    def cost(model, calls, in_tokens, out_tokens):
        return calls * (in_tokens * rates[model]['input'] + out_tokens * rates[model]['output']) / 1e6
    qualification = [
        {'model': 'Luna', 'nominal_calls': 500, 'maximum_input_tokens_per_call': 12000, 'maximum_output_tokens_per_call': 12000},
        {'model': 'Kimi', 'nominal_calls': 500, 'maximum_input_tokens_per_call': 12000, 'maximum_output_tokens_per_call': 16000},
        {'model': 'Astra', 'nominal_calls': 100, 'maximum_input_tokens_per_call': 16000, 'maximum_output_tokens_per_call': 16000},
    ]
    pilot = [dict(qualification[0],nominal_calls=10000),dict(qualification[1],nominal_calls=100),dict(qualification[2],nominal_calls=20)]
    def limits(work, ceiling):
        for x in work: x['no_cache_price_upper_usd'] = cost(x['model'],x['nominal_calls'],x['maximum_input_tokens_per_call'],x['maximum_output_tokens_per_call'])
        nominal = sum(x['no_cache_price_upper_usd'] for x in work)
        return {'requests':work, 'nominal_token_cap_price_usd':nominal, 'maximum_additional_physical_retry_fraction':.2, 'including_twenty_percent_retry_reserve_usd':nominal*1.2, 'stage_model_spend_cap_usd':ceiling, 'implemented_or_launched':False, 'long_inputs':'Never truncate to fit this estimate; record as separately costed out-of-envelope work.', 'failures':'Preserve unsuccessful outputs and tokens, no semantic resubmission loop; safety blocks are excluded, never retried.'}
    unit = benchmark['estimated_usage_usd_per_called_record']
    mean_tokens = benchmark['mean_total_tokens']
    effective_tpm = next(x for x in live['deployments'] if x['name']=='linkup-gpt-6-luna-benchmark')['rate_limits'][1]['count']
    assert effective_tpm == 100000
    sensitivities=[]
    for n in [100000,1000000,3000000,5000000]:
        sensitivities.append({'new_unique_eligible_calls':n,'Luna_only_public_price_usd':n*unit,'optimistic_billed_token_days_at_90_percent_actual_Luna_quota':n*mean_tokens/(effective_tpm*.9*1440),'optimistic_billed_token_days_at_80_percent_actual_Luna_quota':n*mean_tokens/(effective_tpm*.8*1440),'not_a_production_quote':True})
    stages=[
        {'step':1,'work':'Complete delivery/asset/field inventory using existing manifests and ledgers; distinguish source rows, ads, contexts and unresolved scope.','output':'Global field-by-universe coverage and missingness table; confirmed counts or explicit unknowns, no assumed dedup rate.','new_model_cap_usd':0,'incremental_infrastructure_risk_allowance_usd':25,'incremental_stage_cap_usd':25,'planning_work_window_days':[1,2]},
        {'step':2,'work':'Attach old accepted values and evidence under original field masks; mechanically validate existing saved outputs and reconcile status-only events.','output':'Versioned joinable semantic-value sidecar, reuse/unknown/protected masks and exact ad bindings; not just a status index.','new_model_cap_usd':0,'incremental_infrastructure_risk_allowance_usd':25,'incremental_stage_cap_usd':25,'planning_work_window_days':[1,2]},
        {'step':3,'work':'One bounded qualification attempt on at most 500 eligible contexts; cheap candidate model plus independent Kimi comparison and at most 100 Astra adjudications.','output':'Per-field evidence checks, machine-reference agreement, unknown rates and measured token/latency/failure profile; no human QA.','new_model_cap_usd':250,'incremental_infrastructure_risk_allowance_usd':0,'incremental_stage_cap_usd':250,'planning_work_window_days':[1,2]},
        {'step':4,'work':'Only if step3 qualifies the proposed fields, process up to 10000 truly missing eligible contexts for incremental production and throughput measurement.','output':'Nonduplicate field-level incremental sidecars and cost/accepted-field throughput receipt; this is a pilot, not the full target or a replacement sample.','new_model_cap_usd':150,'incremental_infrastructure_risk_allowance_usd':0,'incremental_stage_cap_usd':150,'planning_work_window_days':None,'depends_on_qualified_fields':True},
        {'step':5,'work':'In parallel, develop the existing paper draft and compatible macro/micro tables from reused data; preserve proxy and causal limits.','output':'Paper data/methods/descriptive results and clearly marked remaining identification/Revelio work.','new_model_cap_usd':0,'incremental_infrastructure_risk_allowance_usd':50,'incremental_stage_cap_usd':50,'planning_work_window_days':[2,4]},
        {'step':6,'work':'Release measured missing-field production by bounded tranche; no new training/GPU, no full-text rerun by default.','output':'Full target remains unchanged; itemized true remaining cost and schedule from the qualified workload.','incremental_stage_cap_usd':None,'incremental_infrastructure_risk_allowance_usd':None,'new_model_cap_usd':None,'planning_work_window_days':None,'gate':'Need verified eligible unique count by field, qualified route, measured throughput and verified funds; no automatic full expansion.'},
    ]
    raw=kimi['raw_usage_all_1253_responses']; kprice=rates['Kimi']
    k_no_cache=(raw['prompt_tokens']['sum']*kprice['input']+raw['completion_tokens']['sum']*kprice['output'])/1e6
    result={
        'as_of_local_date':'2026-11-16','currency':'USD','status':'verified_facts_and_proposed_bounded_budget_not_full_completion_quote',
        'actions_this_audit':{'model_calls':0,'production_workers_started':0,'new_resources':0,'quota_or_permission_changes':0,'cloud_index_readonly_check':True,'resource_group_cost_query':True},
        'confirmed_assets':assets, 'known_index':index,
        'not_additive':'Base ads, new-field overlay, historical semantic contexts and source rows overlap or use different units. Never sum them as cleaned total.',
        'full_requested_rows_approx':500000000,'full_remaining_eligible_unique_contexts':None,'full_completion_cost_usd':None,'full_completion_days':None,
        'billing':{'queried_at_utc':live['observed_at_utc'],'scope':'existing_LinkUp_resource_group','period':'MonthToDate','posted_actual_cost_usd':posted,'known_resource_cost_usd':selected,'other_resource_cost_usd':posted-sum(selected.values()),'posted_cost_includes_historical_activity_and_can_lag':True,'model_deployment_cost_breakdown_verified':False,'user_reported_credit_usd':5000,'remaining_credit_verified':False,'remaining_credit_usd':None,'if_5000_were_initial_credit_and_only_this_RG_charged_arithmetic_remaining_usd':5000-posted,'arithmetic_is_not_credit_balance':True,'Marketplace_credit_eligibility_verified':False,'price_tax_credit_applicability_not_confirmed':True},
        'price_baseline':{'rates_usd_per_million_tokens':rates,'type':'public_Azure_list_prices_checked_2026_11_15_not_contract_or_invoice','discounts_assumed':False,'Luna_and_Astra_source_url':luna_price['url'],'Kimi_source_url':kimi_price['source_fetches'][0]['url'],'Astra_evidence':'Same saved official Azure source: Global Standard short context Input10 CachedInput1 CacheWrite12.5 Output50.','VM_retail_lookup_failed':'URLError; no VM-hour rate invented. Infrastructure amounts below are risk allowances, not measured job prices.'},
        'real_usage_checks':{'Luna_calls':20,'Luna_usage_public_price_usd':benchmark['estimated_usage_usd_from_public_price'],'Luna_engineering_pass':14,'Luna_quality_certified':False,'Luna_new_production_accepted':0,'Luna_observed_usd_per_request':unit,'Luna_observed_total_tokens_per_request':mean_tokens,'Kimi_known_usage_response_count':1253,'Kimi_total_attempts':1309,'Kimi_known_usage_no_cache_public_price_usd':k_no_cache,'Kimi_unknown_usage_attempt_count':56,'Kimi_known_usage_not_complete_bill':True,'do_not_add_usage_estimates_to_posted_cost_as_new_charges':True},
        'stages':stages,'next_tranche_cap_usd':sum(s['incremental_stage_cap_usd'] for s in stages if s['incremental_stage_cap_usd'] is not None),'tranche_scope':'Steps1-5 only; caps are proposed, not purchased, reserved or automatically enforced by Azure. Stop job admission before caps; maintain separate existing-resource baseline costs.','qualification_token_envelope':limits(qualification,250),'pilot_token_envelope':limits(pilot,150),
        'review_design':{'reuse_existing_labels_before_new_calls':True,'training_required':False,'human_review_required':False,'one_predeclared_eligible_frame_max_contexts':500,'development_contexts_max':200,'heldout_contexts_max':300,'old_benchmark20_excluded_from_holdout':True,'split_grouped_by_exact_context':True,'avoid_candidate_only_screening':True,'sample_covers':['passing','exception','unknown','no_hit','new_eligible_inputs'],'frozen_original_unknowns_not_overwritten':True,'protected_content_excluded_from_all_routes':True,'reviewer_blinded_to_candidate_output_until_reference_saved':True,'no_reference_is_human_gold':True,'P90_R80_MacroF1_85_interpretation':'Predeclared machine-reference agreement diagnostics by field/relation, not true population accuracy. Insufficient class support is reported, never turned into a passing score.','failed_fields':'Remain unavailable/unknown in new overlays; compatible qualified fields can advance independently without changing research definitions.','no_repeat_until_pass':True},
        'limits':{'shared_project_user_ceiling_tpm':1000000,'Luna_tpm':100000,'Kimi_tpm':300000,'Astra_tpm':1000000,'planning_utilization_range':[.8,.9],'upper_project_schedule_tpm':900000,'admission':'Both project and model token/RPM gates; estimated input/max output, response limits and Retry-After respected. Concurrency does not add TPM.','caps_enforcement_not_implemented_by_this_audit':True},
        'new_work_sensitivities':sensitivities,'sensitivity_caveats':['Unrepresentative20-context Luna workload only, no quality qualification.','Excludes QA, failed-attempt overhead beyond measured20, storage, CPU, tax and baseline costs.','Times are optimistic billed-token lower bounds, not measured saturation or finish dates; max-output reservations, RPM, other users and service latency can dominate.','Current Luna quota100k, not Astra1M; unchanged single-worker pilot timing is not production throughput.'],
        'conditional_pilot_time':{'old_Luna_workload_10000_fluid_hours_90_percent':10000*mean_tokens/(effective_tpm*.9*60),'old_Luna_workload_10000_fluid_hours_80_percent':10000*mean_tokens/(effective_tpm*.8*60),'unchanged_reservation_fluid_hours_90_percent':10000*36175.25/(effective_tpm*.9*60),'unchanged_reservation_fluid_hours_80_percent':10000*36175.25/(effective_tpm*.8*60),'unchanged_serial_worker_hours':10000*565.424/20/3600,'planning_statement':'Do not promise overnight; measure safe concurrent admission first, or unchanged-worker10k alone is approximately79h before independent review.'},
        'old_budget_reconciliation':{'training800':'Removed as mandatory; actual bounded machine qualification proposed cap250.','infrastructure700':'Replace with100 total incremental risk allowance for existing VM metadata/join/paper work, no new CPU purchase.','extra_review500':'Not a separate automatic500; reviews already included in the250 qualification and150 pilot caps.','full_production3000':'Withdrawn as completion quote; measured production budget remains unallocated until true missing workload is known.','total5000':'Credit/budget boundary, not amount that must be spent or verified remaining funds.'},
        'production_formula':'Cost=sum(new eligible context-field-route bundles * measured tokens * matched model rates)+separately bounded QA/rework+incremental CPU/storage/network+continuing baseline; timeline=max(token admission, RPM, measured request service+IO constraints), not serial extrapolation.',
        'scope_of_first_deliverable':'An integrated reuse/missingness ledger and improved current paper draft; not a completed full500M semantic dataset or causal paper.',
        'sources':sources,
    }
    checks={
        'partition_sums_to_union':sum(index['context_states'].values())==index['unique_contexts'],
        'verified_cloud_index_matches_prior':index['index_sha256']=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a',
        'next_tranche500':result['next_tranche_cap_usd']==500,
        'qualification_under_cap':result['qualification_token_envelope']['including_twenty_percent_retry_reserve_usd']<=250,
        'pilot_under_cap':result['pilot_token_envelope']['including_twenty_percent_retry_reserve_usd']<=150,
        'full_cost_not_invented':result['full_completion_cost_usd'] is None,
        'credit_balance_not_invented':result['billing']['remaining_credit_usd'] is None,
        'preserve_full_scope':result['full_requested_rows_approx']==500000000,
        'no_new_model_calls':result['actions_this_audit']['model_calls']==0,
        'Luna_quota_not_mixed':effective_tpm==result['limits']['Luna_tpm'],
    }
    assert all(checks.values()),checks
    out.mkdir(parents=True,exist_ok=True)
    (out/'BUDGET_PLAN_PUBLIC.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'CALCULATION_CHECKS_PUBLIC.json').write_text(json.dumps({'status':'arithmetic_and_scope_checks_not_semantic_accuracy','checks':checks,'all_passed':all(checks.values())},indent=2)+'\n')
    print(json.dumps({'first_tranche_cap':500,'posted_actual_cost':posted,'qualification_upper_with_retry':result['qualification_token_envelope']['including_twenty_percent_retry_reserve_usd'],'pilot_upper_with_retry':result['pilot_token_envelope']['including_twenty_percent_retry_reserve_usd'],'checks':checks}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--review-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.review_root,a.output)
