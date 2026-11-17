"""Recompute a bounded continuation proposal from public receipts, not raw data."""
import hashlib
import json
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    root = here.parent
    def load(rel):
        return json.loads((root / rel).read_text())
    sources = [
        'execution_20261116/EXECUTION_AUTHORIZATION_PUBLIC.json',
        'execution_20261116/QUALIFICATION_LUNA_CONFIG_PUBLIC.json',
        'execution_20261116/continuation02/final/COST_PUBLIC.json',
        'execution_20261116/continuation02/final/QUALIFICATION_DECISION_PUBLIC.json',
        'execution_20261116/continuation02/final/KIMI_FINAL_PUBLIC.json',
        'budget_plan_20261116/BUDGET_PLAN_PUBLIC.json',
        'measurement_protocol_20261117/PROTOCOL_STATUS_PUBLIC.json',
        'variable_dictionary_20261117_v1/RELEASE_QA_PUBLIC.json',
        'variable_dictionary_20261117_v1/FIELD_GAPS_PUBLIC.json',
        'next_step_plan_20261117/CLOUD_CHECKPOINT_READONLY_PUBLIC.json',
        'next_step_plan_20261117/CLOUD_COST_READONLY_PUBLIC.json',
    ]
    cost = load(sources[2])
    q = load(sources[3])
    kimi = load(sources[4])
    cloud = load(sources[-2])
    cloud_cost = load(sources[-1])
    luna = cost['qualification_model_legs']['Luna']
    astra = cost['qualification_model_legs']['Astra']
    reservations = cost['total_conservative_model_reservations_usd']
    price = {'Luna': [0.10, 0.50], 'Kimi': [2.30, 11.50], 'Astra': [12.50, 50.00]}
    # Astra retains the existing conservative cache-write input bound, not $10.
    ceilings = {'Luna': [12000, 12000], 'Kimi': [12000, 16000], 'Astra': [16000, 16000]}
    def max_cost(n, model):
        return n * sum(p*t for p,t in zip(price[model], ceilings[model])) / 1e6
    confirm_n = {'Luna': 150, 'Kimi': 150, 'Astra': 6}
    pilot_n = {'Luna': 10000, 'Kimi': 100, 'Astra': 20}
    # 20% retry allowance is per model; dollar and per-record guards both apply.
    confirm = {k: round(max_cost(n, k)*1.2, 6) for k,n in confirm_n.items()}
    pilot = {k: round(max_cost(n, k)*1.2, 6) for k,n in pilot_n.items()}
    old_leg_cap = {'Luna': 15, 'Kimi': 135, 'Astra': 100}
    new_leg_cap = {'Luna': 1.5, 'Kimi': 40, 'Astra': 8.5}
    old_legs = cost['qualification_model_legs']
    mean_tokens = (luna['input_tokens']+luna['output_tokens'])/luna['physical_attempts']
    mean_cost = luna['priced_usage_estimate_usd']/luna['physical_attempts']
    scenarios = []
    for n in [10000,100000,1000000]:
        scenarios.append({'genuinely_missing_unique_calls':n,
          'Luna_only_usage_price_estimate_usd':round(n*mean_cost,2),
          'billing_token_only_lower_bound_hours_at_80k_tpm':round(n*mean_tokens/80000/60,2),
          'not_wall_time_or_production_quote':True})
    plan = {
        'date_local':'2026-11-17', 'timezone':'Asia/Shanghai',
        'status':'proposal_only_no_new_inference_or_runtime_authorization',
        'dictionary_version':'1.0.0', 'full_delivery_target_approximate_raw_records':500000000,
        'full_delivery_unique_ads':None, 'full_delivery_missing_unique_model_inputs':None,
        'full_delivery_total_cost_usd':None, 'full_delivery_completion_date':None,
        'source_files':[{'relative_to_reuse_first':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in sources],
        'existing_stage_budget':{
            'total_cap_usd':450, 'stage1_infrastructure_cap_usd':25, 'stage2_infrastructure_cap_usd':25,
            'stage3_cap_usd':250, 'stage4_conditional_cap_usd':150, 'paper_cap_usd':0,
            'old_model_usage_estimate_usd':cost['total_priced_usage_estimate_usd'],
            'old_conservative_model_reservations_usd':reservations,
            'stage3_conservative_arithmetic_headroom_usd':round(250-reservations,7),
            'invoice_or_remaining_credit_verified':False,
            'infrastructure_spend_assigned_to_this_stage_usd':None,
            'do_not_add_usage_to_reservations_or_reset_infrastructure_caps':True,
        },
        'proposed_next_work':[
            {'step':'A','work':'Incrementally reconcile known manifest/identity/field gaps; cap exceptional carrier searches; no raw-body rescan.', 'model':'none','budget_cap_within_existing_stage_usd':25,'window_working_hours':[4,8]},
            {'step':'B','work':'Apply dictionary mappings to existing values and same-item evidence; add deterministic derived representations and field-local production adapters. Do not repeat completed attachment.', 'model':'none','budget_cap_within_existing_stage_usd':25,'window_working_hours':[6,12],'overlaps_with':'A'},
            {'step':'C','work':'Separate proposed v2 confirmation; at most 150 distinct unexposed eligible contexts, Luna candidate, independent Kimi, at most 6 Astra audits. Old 500 are development evidence only.', 'model':'Luna/Kimi/Astra','budget_cap_within_existing_stage_usd':50,'window_elapsed_hours':[2,6],'new_protocol_required':True,'old_500_input_authorization_not_reusable':True},
            {'step':'D','work':'Only newly qualified dependencies, at most 10000 genuinely unprocessed unique inputs; first 100 count inside the 10000. Existing saved outputs remain reuse, not new production.', 'model':'Luna plus bounded Kimi/Astra audit','budget_cap_within_existing_stage_usd':150,'window_elapsed_hours':[24,72],'conditional_not_currently_released':True},
        ],
        'budget_proposal':{
            'continuing_infrastructure_envelope_usd':50,
            'additional_confirmation_cap_usd':50,
            'existing_conditional_pilot_cap_usd':150,
            'combined_future_envelopes_usd':250,
            'maximum_old_model_reservations_plus_future_envelopes_usd':round(reservations+250,7),
            'not_an_extra_250_on_top_of_450':True,
            'infrastructure_remainder_must_deduct_already_accrued_costs':True,
            'new_confirmation_leg_caps_usd':new_leg_cap,
            'new_confirmation_formula_bound_with_20pct_retry_usd':confirm,
            'new_confirmation_formula_total_usd':round(sum(confirm.values()),6),
            'pilot_formula_bound_with_20pct_retry_usd':pilot,
            'pilot_formula_total_usd':round(sum(pilot.values()),6),
            'price_basis_usd_per_million_input_output':price,
            'price_basis':'previously_recorded_Azure_public_rates_not_current_contract_or_invoice; Astra retains conservative input bound',
            'per_call_input_output_token_caps':ceilings,
            'forecast_new_model_usage_range_usd':[35,75],
            'forecast_is_not_a_commitment_or_infrastructure_total':True,
            'Codex_conversation_usage_not_automatically_controlled_by_job_caps':True,
            'account_wide_credit_taxes_and_background_resource_costs_not_verified':True,
            'confirmation_base_call_caps':confirm_n,
            'confirmation_physical_call_caps_including_retries':{k:int(n*1.2) for k,n in confirm_n.items()},
            'pilot_base_call_caps':pilot_n,
            'pilot_physical_call_caps_including_retries':{k:int(n*1.2) for k,n in pilot_n.items()},
            'requests_over_caps':'defer_without_truncating_required_evidence',
        },
        'flow_control':{'project_schedule_tpm':800000,'deployment_schedule_tpm':{'Luna':80000,'Kimi':240000,'Astra':800000},
            'Astra_also_limited_by_project_remaining':True,
            'last_observed_deployment_tpm':{'Luna':100000,'Kimi':300000,'Astra':1000000},
            'last_observed_deployment_rpm':{'Luna':100,'Kimi':300,'Astra':1000},
            'refresh_actual_limits_before_spend':True,'count_estimated_input_plus_reserved_max_output_on_admission':True,
            'candidate_concurrency_steps':[1,2,4], 'max_physical_attempts_per_input_per_model':2,
            'temporary_failures_only_retry':True,'protected_or_policy_blocked_no_retry_or_reroute':True,
            'uncertain_transport_no_automatic_duplicate':True,
            'failed_usage_unknown_keeps_reservation':True},
        'schedule':{'first_reuse_and_gap_release_working_days':[1,2],
            'conditional_integrated_pilot_release_elapsed_days':[3,5],
            'conditions':['accessible manifests and carrier indexes','no new schema or access blockers','at least one route/measure qualifies','same resources available','bounded worker changes succeed'],
            'new_completion_forecast_after_first_100_pilot_inputs':True,
            'not_full_500M_completion_schedule':True},
        'observed_timing_and_cost':{'Luna_latest_500_mean_billed_tokens':mean_tokens,
            'Luna_latest_500_mean_usage_price_usd':mean_cost,
            'Kimi_old_reference_inputs':350,'Kimi_old_reference_wall_seconds':kimi['elapsed_seconds_this_process'],
            'Kimi_old_reference_concurrency':kimi['concurrent_sessions'],
            'Kimi_old_reference_inputs_per_minute':round(350/(kimi['elapsed_seconds_this_process']/60),4),
            'old_comprehensive_schema_not_new_route_benchmark':True,
            'conditional_Luna_scenarios':scenarios},
        'simplifications':['no GPU','no training prerequisite','no repeat original 500 calls','no rerun base or overlapping D67','reuse current four-key CREATED join','reuse field-local validator and tests; test only changes','no model call solely to regenerate a saved carrier','no paper expansion','no timers','no wait for Revelio to process LinkUp available fields'],
        'decision_contract':{'freeze_measure_dependencies_and_metrics_before_confirmation':True,
            'one_fixed_confirmation_not_iterative_pass_search':True,
            'confirmed_evidence_and_key_integrity_required':True,
            'machine_reference_agreement_not_true_accuracy':True,
            'adequate_support_and_coverage_required_per_measure':True,
            'rare_challenges_not_pooled_into_probability_error_estimates':True,
            'no_whole_ad_or_89_variable_joint_gate':True,
            'no_qualification_from_shadow_engineering_pass_alone':True,
            'failed_new_fields_remain_explicitly_incomplete':True,
            'all_five_research_modules_retained':True,
            'human_audit_required':False},
        'executed_this_plan':{'cloud_existing_public_checkpoint_reads':2,'raw_data_processing':False,'model_calls':0,'production_started':False,'billing_query':False,'new_resources':0}
    }
    checks = {
        'old_500_completed':q['selected_inputs']==500 and q['status']=='fixed_qualification_protocol_completed',
        'cloud_production_not_admitted':cloud['state']['step4_released'] is False and cloud['state']['new_production_accepted']==0,
        'cloud_cost_matches_archived_reservations':cloud_cost['cost']['total_conservative_model_reservations_usd']==reservations,
        'cloud_cost_matches_archived_usage_estimate':cloud_cost['cost']['total_priced_usage_estimate_usd']==cost['total_priced_usage_estimate_usd'],
        'no_stage_cap_reset':reservations+50<=250 and reservations+250<=450,
        'confirmation_formula_below_cap':sum(confirm.values())<=50,
        'pilot_formula_below_cap':sum(pilot.values())<=150,
        'old_per_model_budget_respected':all(old_legs[k]['conservative_reserved_usd']+new_leg_cap[k]<=old_leg_cap[k] for k in old_leg_cap),
        'confirmation_per_model_formula_below_caps':all(confirm[k]<=new_leg_cap[k] for k in new_leg_cap),
        'no_fabricated_full_delivery_quote':plan['full_delivery_total_cost_usd'] is None,
        'current_dictionary_is_definition_only':load(sources[7])['definition_release_only'] is True,
    }
    assert all(checks.values()), checks
    for name,value in [('PLAN_PUBLIC.json',plan),('CALCULATION_CHECKS_PUBLIC.json',{'status':'pass','checks':checks,'count':len(checks),'scope':'arithmetic_and_proposal_boundaries_not_model_qualification'})]:
        (here/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checks_passed':len(checks),'confirmation_bound':sum(confirm.values()),'pilot_bound':sum(pilot.values()),'next_envelopes':250,'not_new_inference':True}))


if __name__ == '__main__':
    main()
