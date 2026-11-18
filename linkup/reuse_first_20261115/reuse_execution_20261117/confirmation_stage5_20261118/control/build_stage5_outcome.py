"""Build an aggregate decision from preserved terminal receipts; no model calls."""
import datetime as dt
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((D / name).read_text())


def sha(name):
    return hashlib.sha256((D / name).read_bytes()).hexdigest()


def stamp(value):
    return dt.datetime.fromisoformat(value)


def build():
    sources = ['LUNA_FINAL_PUBLIC.json', 'KIMI_FINAL_PUBLIC.json', 'ASTRA_FINAL_PUBLIC.json',
               'SCORING_PUBLIC.json', 'ASTRA_DIAGNOSTIC_PUBLIC.json',
               'control/ASTRA_FAILURE_INSPECTION_V2_PUBLIC.json',
               'control/SCORING_TRANSPORT_PUBLIC.json', 'control/DIRECT_V4_LAUNCH_PUBLIC.json',
               'EXECUTION_FREEZE_PUBLIC.json', 'protocol/PROTOCOL_FREEZE.json']
    score, diagnostic = read('SCORING_PUBLIC.json'), read('ASTRA_DIAGNOSTIC_PUBLIC.json')
    assert sha('SCORING_PUBLIC.json') == read('control/SCORING_TRANSPORT_PUBLIC.json')['sha256']
    assert sha('protocol/PROTOCOL_FREEZE.json') == 'fdf07cec40eef5ce3ed1ac4e2cb7bcf435403ccbaa7aa240f6625b9d27792f11'
    assert score['primary_gate_unchanged'] and not score['primary_reference_overwritten']
    assert diagnostic['original_primary_scores_sha256'] == score['scores_sha256']
    assert not diagnostic['reference_overwritten'] and not diagnostic['primary_gates_recomputed']
    rows = score['measure_results']['confirmation']
    eligible = sorted(k for k, v in rows.items() if v['machine_reference_measure_gate_pass'])
    assert eligible == sorted(score['eligible_measure_dependencies'])
    assert len(rows) == 51 and score['accounting']['frame_cases'] == 135
    # This closing report records the observed non-admission; it cannot authorize a run.
    assert not eligible, 'this_decision_builder_is_for_the_observed_zero_eligible_result'
    groups = {'insufficient_support_or_reference_coverage': [], 'adequate_support_below_quality_gate': []}
    compact = []
    for measure, value in rows.items():
        reasons = value['blocking_reasons']
        insufficient = any(r.startswith('insufficient_') or r == 'known_reference_coverage_below_gate' for r in reasons)
        group = 'insufficient_support_or_reference_coverage' if insufficient else 'adequate_support_below_quality_gate'
        groups[group].append(measure)
        present = value['class_metrics'].get('present', {})
        compact.append({'measure': measure, 'decision': group, 'known_reference_cases': value['known_reference_cases'],
                        'known_reference_coverage': value['known_reference_coverage'], 'support': value['support'],
                        'positive_precision': present.get('precision'), 'positive_recall': present.get('recall'),
                        'outcome_macro_f1': value['outcome_macro_f1'], 'blocking_reasons': reasons})
    rates = {'Luna': (100, 500), 'Kimi': (2300, 11500), 'Astra': (12500, 50000)}
    caps = {'Luna': 2, 'Kimi': 40, 'Astra': 8}
    legs = {}
    for leg in rates:
        value = read(leg.upper() + '_FINAL_PUBLIC.json')
        assert value['terminal_no_active_requests'] and value['selected'] == value['outputs_accounted']
        assert value['selected'] == (6 if leg == 'Astra' else 135)
        assert value['reserved_usd'] <= caps[leg]
        r_in, r_out = rates[leg]
        legs[leg] = {k: value[k] for k in ['selected', 'physical_attempts', 'logical_calls', 'outputs_accounted',
                    'reserved_usd', 'input_tokens', 'output_tokens', 'attempt_states', 'at_utc', 'output_sha256']}
        legs[leg]['reported_usage_priced_at_inherited_rates_usd'] = (
            value['input_tokens'] * r_in + value['output_tokens'] * r_out) / 1e9
    assert diagnostic['astra_outputs_sha256'] == legs['Astra']['output_sha256']
    assert legs['Astra']['attempt_states'] == {'http_error_terminal': 6}
    failures = read('control/ASTRA_FAILURE_INSPECTION_V2_PUBLIC.json')['errors']
    assert len(failures) == 1 and failures[0]['count'] == 6 and failures[0]['http_status'] == 400
    assert failures[0]['message_keyword_flags']['exact_previously_documented_json_input_error']
    assert sum(v.get('astra_luna_comparable', 0) + v.get('astra_kimi_comparable', 0)
               for v in diagnostic['measure_diagnostics'].values()) == 0
    reservation = sum(v['reserved_usd'] for v in legs.values())
    priced = sum(v['reported_usage_priced_at_inherited_rates_usd'] for v in legs.values())
    assert reservation <= 50 and 178.0651464 + reservation <= 250
    result = {
        'status': 'primary_confirmation_scored_no_pilot_admission_Astra_diagnostic_unavailable',
        'at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'fresh_candidate_rows': 150, 'prior_exposed_rows_excluded_without_replacement': 15, 'fixed_fresh_contexts': 135,
        'independent_research_measures': 51, 'eligible_measures': eligible,
        'measure_decision_counts': {k: len(v) for k, v in groups.items()}, 'measure_results_compact': compact,
        'model_legs': legs, 'physical_attempts_all_legs': sum(v['physical_attempts'] for v in legs.values()),
        'budget': {'stage5_cap_usd': 50, 'conservative_reserved_usd': reservation,
                   'reported_usage_priced_at_inherited_rates_usd': priced,
                   'historical_plus_this_run_reservation_usd': 178.0651464 + reservation,
                   'old_step3_cap_usd': 250, 'phase_cap_usd': 450, 'pilot_cap_usd_not_spent': 150,
                   'invoice_verified': False, 'no_usage_not_treated_as_zero_actual_cost': True,
                   'reservation_and_priced_usage_not_added': True,
                   'infrastructure_and_Codex_session_cost_not_included': True},
        'duration': {'direct_v4_seconds': (stamp(legs['Kimi']['at_utc']) - stamp(read('control/DIRECT_V4_LAUNCH_PUBLIC.json')['at_utc'])).total_seconds(),
                     'freeze_to_last_leg_terminal_seconds': (stamp(legs['Astra']['at_utc']) - stamp(read('EXECUTION_FREEZE_PUBLIC.json')['at_utc'])).total_seconds()},
        'direct_Kimi': {'authentication': 'existing_VM_managed_identity', 'verified_TPM': 3000000,
                        'scheduled_TPM_during_fixed_confirmation': 240000,
                        'prior_calls_reused_not_replayed': 11, 'new_direct_v4_calls': 124,
                        'OpenCode_used_for_v4': False},
        'Astra_failure': {'diagnostic_judgments_received': 0, 'HTTP_400_attempts': 6, 'param': 'input',
                          'cause': 'Responses json_object requires json in input; instructions-only wording was insufficient.',
                          'previously_documented_regression_reintroduced': True,
                          'not_a_model_quality_or_permission_failure': True,
                          'originals_preserved': True, 'six_physical_attempt_cap_not_reset': True,
                          'retry_or_recovery_launched': False},
        'pilot_launched': False, 'new_production_accepted': 0, 'stage5_model_workers_still_running': False,
        'primary_reference_overwritten': False, 'gates_changed_after_outputs': False,
        'new_confirmation_sample_drawn': False, 'human_gold_or_population_accuracy_claimed': False,
        'whole_corpus_completed': False, 'five_modules_retained': True,
        'sources_sha256': {name: sha(name) for name in sources}}
    (D / 'STAGE5_OUTCOME_PUBLIC.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    lines = ['# 阶段五实际结果与停点', '',
        '**主确认已完成评分；没有合格的 Luna 试产字段。Astra 诊断未取得模型答案，因此不能称整轮独立审核全部完成。**', '',
        '## 已做完', '',
        '- 固定150候选排除15个既有上下文后，135个新上下文不补样。Luna与Kimi各135次请求，均已终态记账。',
        '- Kimi已直接使用Azure VM托管身份；实际配额300万TPM。此前11次响应复用，v4新增124次；最终134个完整响应、1个截断输出保留，不重跑。',
        '- 原冻结评分器已在Azure运行，51个独立研究量分别判定；不是13字段捆绑判整条。',
        '- 26项因正例支持或参考覆盖不足而证据不足；25项支持量足够但至少一项既定质量指标不足。最终合格项0，1万条/$150试产没有启动。', '',
        '## 这次到底卡在哪里', '',
        '第一，当前廉价候选Luna相对独立Kimi的一致性不足，不是Kimi配额或SSH问题。接近门槛的字段和核心字段要分开看：', '',
        '| 研究量 | 正例Precision | 正例Recall | 二类Macro-F1 | 主要不足 |',
        '|---|---:|---:|---:|---|']
    labels = {'experience.occupation_task.mention': '职业/任务经验提及', 'experience.industry_domain.years': '行业经验年限',
              'responsibility.people_supervision.mention': '人员监督提及', 'responsibility.training_mentoring.mention': '培训指导提及',
              'technology.mention': '技术提及'}
    for name, label in labels.items():
        value = rows[name]; positive = value['class_metrics']['present']
        lines.append(f"| {label} | {positive['precision']:.1%} | {positive['recall']:.1%} | {value['outcome_macro_f1']:.1%} | {', '.join(value['blocking_reasons'])} |")
    lines += ['', '这些是机器参考一致性，不是人工准确率，也不代表五亿总体。关系型字段另受原关系门槛约束，上表不是给未通过项变相放行。', '',
        '第二，Astra的6次请求全部HTTP400：Responses的json_object要求input本身含json；脚本只在instructions里写了JSON。这是11月16日曾记录并修复过、此次被重新引入的工程错误，不是模型不够强，也不是没权限。0个Astra判断，不能冒充6条审核。',
        '错误正文、原账本和输出槽位均保留；已定位旧修复，另备未应用补丁。不重置6次物理请求上限，不用额外调用或Astra替换Kimi来改写本次primary结果。', '',
        '## 成本与时间', '',
        f'- 本轮请求保守预留 **${reservation:.4f} / $50**；有usage部分按原记录单价计算约 **${priced:.4f}**。两者不相加，未核实Azure发票。Astra无usage不当作零实际费用。',
        f"- Kimi v4直接执行约 **{result['duration']['direct_v4_seconds']/60:.1f}分钟**；本次固定确认保持原串行调度，并未宣称用满300万TPM。",
        '- 原历史预留不重置；本轮未花试产$150。上述数额不含现有VM/存储或Codex会话费用。', '',
        '## 后续边界', '',
        '此次固定确认已给出决定，不再重抽一批、换一套门槛反复求pass。不能自动把Luna扩大到1万条或全库；已保存结果作为版本化机器输出保留，不覆盖旧accepted。',
        '已有基础清洗、旧验收语义和复用增量仍按各自原范围有效。五大模块及LinkUp—Revelio目标不缩减；本结果既不证明五亿处理完成，也不证明Kimi自身不合格。',
        'Astra未应用的传输修复与有界恢复需另列明确执行版本；当前阶段五三个模型进程均已结束。真正的全量缺口、可接受的测量误差和后续生产路线仍未解决，不虚报完成。', '',
        '## 结果位置', '',
        '- 云端评分：`/home/linkup/migration/confirmation_stage5_20261118/execution_v1/scoring_v1`',
        '- 云端Kimi输出：`/home/linkup/migration/confirmation_stage5_20261118/execution_v1/kimi_direct_v4`',
        '- 云端Astra失败及诊断：`/home/linkup/migration/confirmation_stage5_20261118/execution_v1/astra_diagnostic_v1`',
        '- 本机对应目录：`/Users/lilyluo/Documents/LinkUp_Resume_Review_20261110/confirmation_stage5_20261118`', '']
    (D / 'STAGE5_RESULT_ZH.md').write_text('\n'.join(lines))
    print(json.dumps({'status': result['status'], 'decision_counts': result['measure_decision_counts'],
                      'reserved_usd': reservation, 'reported_usage_estimate_usd': priced,
                      'pilot_launched': False, 'model_workers_running': False}))


if __name__ == '__main__':
    build()
