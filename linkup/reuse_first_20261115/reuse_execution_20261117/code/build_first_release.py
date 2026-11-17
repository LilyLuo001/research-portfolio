"""Build a release from verified public aggregates only; never opens private data."""
import datetime
import hashlib
import json
from pathlib import Path


def main():
    out=Path(__file__).resolve().parents[1]
    base=out.parent
    read=lambda p:json.loads(p.read_text())
    material=read(out/'MATERIALIZATION_PUBLIC.json')
    qa=read(out/'MATERIALIZATION_INDEPENDENT_QA_V2_PUBLIC.json')
    reconciliation=read(out/'RECONCILIATION_V3_PUBLIC.json')
    coverage=read(out/'VARIABLE_COVERAGE_PUBLIC.json')
    definitions=read(base/'variable_dictionary_20261117_v1/VARIABLE_DICTIONARY_PUBLIC.json')
    shards=read(base/'execution_20261116/ALL_SHARD_ACCOUNTING_PUBLIC.json')
    auth=read(out/'AUTHORIZATION_PUBLIC.json')
    plan=read(base/'next_step_plan_20261117/PLAN_PUBLIC.json')
    engineering=read(out/'INDEPENDENT_QA_V2_ENGINEERING_PUBLIC.json')
    output_hashes=read(out/'OUTPUT_SHA256_PUBLIC.json')
    assert material['status']=='first_reuse_materialization_complete'
    assert material['checks'] and all(value is True for value in material['checks'].values())
    assert qa['status']=='pass' and qa['checks'] and all(value is True for value in qa['checks'].values())
    assert material['destination_sha256']==qa['output_sha256']
    assert material['new_model_calls']==material['new_production_accepted']==0
    assert qa['new_model_calls']==qa['new_production_accepted']==0
    assert material['raw_advertisement_files_read']==0
    assert shards['verified_shards']==2464 and shards['missing_shards']==0
    # Public aggregates must belong to the same completed output, not merely
    # share a plausible status.  Never open the private SQLite file here.
    for name in ('MATERIALIZATION_PUBLIC.json','VARIABLE_COVERAGE_PUBLIC.json'):
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==output_hashes[name], name+'_sha_mismatch'
    assert output_hashes[Path(material['destination_relative_to_migration']).name]==material['destination_sha256']
    assert material['source_database_sha256']==reconciliation['source_sha256']['values']
    assert coverage['dictionary_version']==definitions['dictionary_version']==material['dictionary_version']
    assert coverage['eligible_carrier_contexts']==material['eligible_carrier_contexts']
    assert reconciliation['audit_resolution_counts']['existing_carrier_available']==material['eligible_carrier_contexts']
    assert sum(material['source_documents_by_asset'].values())==material['processed_documents']
    assert qa['counts']['source_document']==material['processed_documents']
    assert qa['counts']['variable_value']==material['materialized_variable_rows']
    assert sum(qa['summary']['variable_measurement_rows'].values())==material['materialized_variable_rows']
    assert sum(qa['summary']['variable_workflow_rows'].values())==material['materialized_variable_rows']
    assert sum(reconciliation['audit_resolution_counts'].values())==sum(reconciliation['original_state_counts'].values())
    assert engineering['status']=='synthetic_engineering_tests_passed'
    test_counts=engineering['tests']
    assert sum(test_counts[name] for name in ('adapter_unit','materialization_driver','independent_QA_v2'))==test_counts['total_unittest']
    for name,digest in engineering['files_sha256'].items():
        assert hashlib.sha256((out/'code'/name).read_bytes()).hexdigest()==digest, name+'_engineering_pin_changed'
    assert auth['step1_execution_authorized'] and auth['model_calls_allowed_in_step1']==0
    assert auth['total_stage_budget_cap_usd']==plan['existing_stage_budget']['total_cap_usd']
    assert auth['old_conservative_model_reservation_usd']==plan['existing_stage_budget']['old_conservative_model_reservations_usd']
    # This is a first-release builder, not a latest-wins updater.
    for name in ('FIELD_GAPS_V1_PUBLIC.json','STEP1_RELEASE_PUBLIC.json','AZURE_RESEARCH_STATE.json','STEP1_RESULTS_ZH.md'):
        assert not (out/name).exists(), 'existing_release_preserved:'+name
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def save(name,value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    direct={
        'lk.identity.ad_key':'ad_binding.k and variable_value.k; original four-part key retained',
        'lk.identity.context':'source_document.h and variable_value.h',
        'lk.provenance.source':'source_document and run_metadata; same-item source anchors retained',
        'lk.state.axes':'variable_value workflow/measurement/engineering, metadata_json route/effective masks, original_mask, and context_state protections',
    }
    bykey={v['variable_key']:v for v in coverage['variables']}
    assert len(bykey)==len(coverage['variables'])==len(definitions['variables'])==89
    assert set(bykey)=={v['variable_key'] for v in definitions['variables']}
    assert sum(v['projected_atom_rows'] for v in bykey.values())==material['materialized_variable_rows']
    # A distinct ad_binding key is not necessarily a key with a usable CREATED.
    # The coverage source uses COUNT(DISTINCT k), non-NULL value_json, and
    # matched_consistent/retained_source_value states, rather than atom counts.
    created_keys=bykey['lk.time.created']['ad_keys_with_nonnull_structural_source_value']
    bound_keys=qa['summary']['bound_ad_keys']
    deferred_keys=qa['summary']['deferred_variable_keys']
    new_keys=sorted(v['variable_key'] for v in definitions['variables'] if v['availability_code']=='new_definition')
    assert set(new_keys).issubset(deferred_keys)
    legacy_deferred_keys=sorted(set(deferred_keys)-set(new_keys))
    audit_counts=reconciliation['audit_resolution_counts']
    protected_count=reconciliation['runtime_exclusion_contexts']
    fields=[]
    for definition in definitions['variables']:
        key=definition['variable_key'];row=bykey[key]
        fields.append({**row,'label_zh':definition['label_zh'],'modules':definition['modules'],
           'direct_relational_support':direct.get(key),
           'remaining_work_zh':definition['remaining_work_zh'],
           'missingness_rule':definition['missingness_rule'],
           'full_scope_inventory_status':'not_a_full_delivery_field_census',
           'safe_new_inference_queue_membership_established_by_this_report':False})
    gaps={
       'at_utc':stamp,'dictionary_version':'1.0.0','release':'step1_first_materialized_release',
       'full_target_retained_approximate_raw_records':500000000,
       'full_delivery_unique_ads':None,'full_delivery_unique_missing_field_inputs':None,
       'old_base_reuse':{'canonical_US_ads':shards['totals']['accounting.canonical_usa_rows'],
           'verified_shards':shards['verified_shards'],'missing_base_receipts':shards['missing_shards'],
           'overlapping_D67_delta_ads':5804936,'sum_base_and_delta_forbidden':True,
           'not_physically_rewritten_or_reextracted_this_run':True,
           'old_rule_candidates_not_semantic_ground_truth':True},
       'remaining_gaps':[
          {'group':'full_delivery_identity_and_field_coverage','count':None,'unit':'unique_ads_and_field_specific_contexts',
           'action':'Use existing full-scope identity and version manifests to establish denominators; no raw-body rescan or 500M-minus-US subtraction.'},
          {'group':'accepted_missing_carrier_held','count':audit_counts['held_carrier_previously_confirmed'],'unit':'contexts',
           'action':'Two previously located held files remain protected; do not reopen or regenerate.'},
          {'group':'saved_missing_carrier_or_binding','count':audit_counts['saved_carrier_or_binding_still_missing'],'unit':'contexts',
           'action':'Five Pro binding/carrier cases and one Astra failed-output locator remain unresolved; not an unread queue.'},
          {'group':'event_provenance_located_acceptance_unresolved','count':audit_counts['event_provenance_located_acceptance_unresolved'],'unit':'contexts',
           'action':'Retain event evidence and original unresolved state. No acceptance inferred from event existence.'},
          {'group':'identity_without_event','count':audit_counts['identity_present_but_no_event_in_current_index'],'unit':'contexts',
           'action':'Retain identity-only status; missing event is not proof of never processed.'},
          {'group':'runtime_protected_union','count':protected_count,'unit':'contexts',
           'action':'Exclude from projection and new model processing. Overlaps original statuses; do not add to their total.'},
          {'group':'new_semantic_representations','count':len(new_keys),'unit':'variable_keys',
           'variable_keys':new_keys,
           'action':'Preserve raw evidence and unknowns; no invented concepts, qualification logic, or task atoms.'},
          {'group':'legacy_atoms_evidence_or_derivations_deferred','count':len(legacy_deferred_keys),'unit':'variable_keys_with_at_least_one_deferred_mapping',
           'variable_keys':legacy_deferred_keys,
           'action':'A deferred mapping can mean missing legacy evidence, a stripped atom, or a pending derivation; it is not a new-definition count, a whole-variable failure, or a new-inference queue.'},
          {'group':'macro_entry_and_direct_exits','count':None,'unit':'nationwide_series',
           'action':'Nationwide entry share lacks same-frame labels; direct DELETE_DATE exit series not delivered. Existing macro first-observed and stock results can be written now.'},
          {'group':'Revelio_and_historical_comparison','count':None,'unit':'external_data_and_linkages',
           'action':'Five research modules retained. Actual person-spell delivery, entity bridge, and historical data support are not yet established.'},
       ],
       'fields':fields,'states_and_field_counts_are_not_additive':True,
       'all_deferred_mapping_variable_keys':deferred_keys,
       'existing_value_compatibility_issue_rows':material['adapter_issue_counts'],
       'compatibility_issue_rows_are_not_whole_document_rejections':True,
       'unknown_or_unprojected_not_equal_absent_or_unprocessed':True,
       'full_scope_reconciliation_complete':False,
    }
    save('FIELD_GAPS_V1_PUBLIC.json',gaps)
    inputs=[out/n for n in ['AUTHORIZATION_PUBLIC.json','RUN_PINS_PUBLIC.json','RECONCILIATION_V3_PUBLIC.json',
       'MATERIALIZATION_PUBLIC.json','MATERIALIZATION_INDEPENDENT_QA_V2_PUBLIC.json','VARIABLE_COVERAGE_PUBLIC.json',
       'OUTPUT_SHA256_PUBLIC.json','INDEPENDENT_QA_V2_ENGINEERING_PUBLIC.json']]
    inputs += [base/'next_step_plan_20261117/PLAN_PUBLIC.json',
               base/'variable_dictionary_20261117_v1/VARIABLE_DICTIONARY_PUBLIC.json',
               base/'execution_20261116/ALL_SHARD_ACCOUNTING_PUBLIC.json']
    release={
       'at_utc':stamp,'status':'step1_first_release_verified_ready_for_publication',
       'user_approved_plan_commit':auth['user_approved_plan_commit'],
       'first_materialized_release_complete':True,'full_scope_reconciliation_complete':False,
       'private_output_relative_to_migration':material['destination_relative_to_migration'],
       'private_output_sha256':material['destination_sha256'],'private_output_bytes':material['destination_bytes'],
       'source_document_carrier_rows':material['processed_documents'],
       'source_document_carrier_row_unit':'fixed10k ad-by-family carrier row; other assets original review-carrier row; not physical files or unique ads',
       'carrier_contexts':material['eligible_carrier_contexts'],
       'variable_atom_rows':material['materialized_variable_rows'],
       'bound_ad_keys_all_CREATED_states':bound_keys,
       'ad_keys_with_existing_nonnull_consistent_CREATED':created_keys,
       'CREATED_key_count_source':'VARIABLE_COVERAGE_PUBLIC.json: lk.time.created COUNT(DISTINCT k) with non-NULL matched_consistent/retained_source_value; not ad_binding provenance rows',
       'contexts_with_any_original_scope_atom':qa['summary']['contexts_with_any_original_scope_atom'],
       'ad_keys_with_any_original_scope_atom':qa['summary']['ad_keys_with_any_original_scope_atom'],
       'any_compatible_atom_includes_evidence_and_anchors_not_a_complete_measure':True,
       'materialization_elapsed_seconds':material['elapsed_seconds'],
       'successful_independent_QA_elapsed_seconds':qa['elapsed_seconds'],
       'all_contexts_or_ad_keys_have_all_fields':False,
       'new_model_calls':0,'new_production_accepted':0,'new_extraction_api_cost_usd':0,
       'new_GPU_or_VM_resources':0,'timers_resumed':False,
       'phase_total_cap_usd':auth['total_stage_budget_cap_usd'],
       'old_model_priced_usage_estimate_usd':plan['existing_stage_budget']['old_model_usage_estimate_usd'],
       'old_conservative_model_reservations_usd':auth['old_conservative_model_reservation_usd'],
       'usage_and_reservations_not_additive':True,'existing_infrastructure_caps_not_reset':True,
       'infrastructure_job_invoice_usd':None,'Codex_conversation_billing_included_in_API_zero_claim':False,
       'no_150_confirmation_or_10000_pilot_launched':True,
       'paper_resume_condition':'publish this first release; then start Module A from verified existing results',
       'synthetic_engineering_test_counts':test_counts,
       'inputs_sha256':{str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
    }
    save('STEP1_RELEASE_PUBLIC.json',release)
    save('AZURE_RESEARCH_STATE.json',{
       **release,'status':'step1_first_reuse_release_available_no_new_inference',
       'previous_state_preserved':'execution_20261116/run001/AZURE_RESEARCH_STATE.json',
       'original_state_counts':reconciliation['original_state_counts'],
       'audit_resolution_counts':reconciliation['audit_resolution_counts'],
       'original_acceptance_ledger_unchanged':True,'runtime_protected_context_union':protected_count,
       'new_production_queue_admitted':False,'full_delivery_missing_unique_inputs':None,
       'gap_register':'FIELD_GAPS_V1_PUBLIC.json','coverage_register':'VARIABLE_COVERAGE_PUBLIC.json',
    })
    q=qa['summary'];checks=len(qa['checks'])
    text=f'''# 第1步：旧成果拼接与缺口核账——第一版

日期：2026-11-17。已实际在既有Azure VM运行并通过{checks}项独立落表核查；不是方案草稿，也不是“五亿条全部语义完成”。

## 交付了什么

- **{material['eligible_carrier_contexts']:,}个上下文**的既有载体进入新版拼接；保留**{material['processed_documents']:,}条来源载体记录**。fixed10k按广告×字段族记录，Pro等按原review载体记录；这不是物理文件数、唯一广告版本数或新生产数。
- 形成**{material['materialized_variable_rows']:,}条变量原子行**。这些是字段、证据和派生表示，不能当广告数或新验收数。
- 保留**{bound_keys:,}个广告来源四键的既有日期连接状态**（包括未匹配等状态）。日期覆盖回执另确认**{created_keys:,}个四键有非空、一致的CREATED值**；这两个指标不混用，也不把来源重复行当广告数。不重新按JOB_HASH碰撞拼接；来源账本全部保留，分析视图消除同一绑定多来源造成的重复。
- 89项变量定义、五大研究模块均保留；字段分别复用，待验、未知和局部冲突不被改成已验收，也不再让一项缺失清空其他可用字段。
- 原204,774,035条美国基础结果、与之重叠的5,804,936条D67增量继续引用。2,464个分片回执已核清，**本轮没有重洗、重写或把两者相加**。

数据文件（留在Azure，不进入Git）：

`migration/{material['destination_relative_to_migration']}`（相对Azure用户主目录）

SHA256：`{material['destination_sha256']}`

主要表：`variable_value`、`source_document`、`original_mask`、`ad_binding`、`metadata_value`；连接视图：`analysis_values_with_created`。视图仍是多来源、长格式原子表，**不能不选范围/版本就直接count当广告数**。

## 真正还缺什么

1. **全交付的唯一广告/上下文及逐字段净缺口仍未核定。** 五亿是目标范围，不是已验证的可直接调用模型次数。第一版细语义拼接不代替全范围身份核账。
2. {audit_counts['held_carrier_previously_confirmed']}个原验收上下文的载体已经定位，但处于既有保护；{audit_counts['saved_carrier_or_binding_still_missing']}个待验上下文仍缺载体或绑定。两类均不进入重生成队列。
3. 原{reconciliation['original_state_counts']['not_reconciled']:,}个待对账上下文现已明确：{audit_counts['event_provenance_located_acceptance_unresolved']:,}个仅有Pro事件、{reconciliation['exclusion_intersection_original_states']['not_reconciled']}个同时有Pro/Azure事件且属于运行隔离、{audit_counts['identity_present_but_no_event_in_current_index']}个只有身份但无事件。**均不能因此认定未处理或晋升验收。**
4. 运行隔离并集{protected_count}个上下文，跨越原状态类别；本次在选择输出载荷之前排除，其中{material['excluded_source_documents']}条已有载体记录未投影。原{reconciliation['original_state_counts']['quarantined']}个quarantined保留，不把{protected_count}误叫新增隔离。
5. 字典明确的**{len(new_keys)}个新定义变量**（对象概念、资格逻辑/条件、扩展任务、跨领域开放等）仍待补。另有**{len(legacy_deferred_keys)}个旧变量或派生变量**至少存在一种未能投影的载体情况，例如旧字段/证据被剥离或派生依赖未齐；不将它们全叫“新变量”，也不表示这些变量在所有上下文都缺失。完整逐字段明细见`FIELD_GAPS_V1_PUBLIC.json`。
6. 全国初级岗位占比缺同范围语义标签，直接退出时间序列尚未交付；Revelio个人经历、跨库桥接及早期计算机化比较仍保留为后续模块，不假装已完成。

## 正确性和成本

- 原值、原schema、PRIMARY多版本、原验收账本与数据库SHA保持不变；新表是独立sidecar。
- 合成单元测试分列为**适配器{test_counts['adapter_unit']}项＋落表driver {test_counts['materialization_driver']}项＋独立QA v2等价性/保护测试{test_counts['independent_QA_v2']}项＝{test_counts['total_unittest']}项**，另有**{test_counts['independent_adapter_assertions']}项独立适配器断言**通过；真实落表独立核查也已通过。**这些证明工程和连接一致性，不是重新认证语义准确率；不是这么多条真实广告样本。**
- 新增提取模型调用0，提取API支出$0；没有新开GPU/VM，没有恢复计时器。继续沿用原${release['phase_total_cap_usd']}阶段总上限；现有VM/存储账单尚未归集，不能声称整个Azure支出为零，Codex对话费用也不含在API零支出中。
- 历史计价估计${release['old_model_priced_usage_estimate_usd']}与保守预留${release['old_conservative_model_reservations_usd']}不是两笔可相加的花费；不重置预算。
- 早期结构探针曾碰到3个运行保护范围的结构样本，未输出值/证据或进行语义重判；原探针、修正与回执均保留。已执行修正版，实际落表实行先排除、后取载荷。

## 下一步

第一版交付后，按本次授权恢复**模块A宏观章节**，只使用已有核实结果，不编造全国entry份额、退出量或AI因果效应。后续≤150条确认和≤1万条有条件试产尚未启动；需先冻结新测量协议与真正未处理输入名单，不能把待验/未知当新任务重新付费。

CREATED始终标注为首次观察岗位发布时间代理；前后变化不自动等于AI因果效应。
'''
    (out/'STEP1_RESULTS_ZH.md').write_text(text)
    print(json.dumps({'status':release['status'],'carrier_contexts':release['carrier_contexts'],
         'variable_atom_rows':release['variable_atom_rows'],'full_scope_reconciliation_complete':False}))


if __name__=='__main__':
    main()
