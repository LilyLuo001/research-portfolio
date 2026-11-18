"""Explicit-file Stage5 outcome publication; dry-run unless --apply is supplied.

No source edits, recursive source admission, Git staging, commit, push, network,
cloud operation, or model call. Original runtime-v1 publication is preserved.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tokenize

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parents[1]
REPO = Path('/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git')
ROOT_REL = 'linkup/reuse_first_20261115'
PUB_REL = 'reuse_execution_20261117/confirmation_stage5_20261118'
B = REPO / ROOT_REL
OUT = B / PUB_REL
PROTECTED_LITERAL_SHA = 'b01af4ee4739078408ff2ec1872fc0a17f46d25c875cba1a027bc198a8206632'
OPERATING_PREFIXES = (
    '/home/linkup/migration/',
    '/Users/lilyluo/Documents/LinkUp_Resume_Review_20261110/',
    '/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/',
)

# Every source and target is deliberate. No glob/rglob admits source files.
# Missing future artifacts are reported and skipped; supplied names cannot
# expand this list. The repaired six executables have separate v2 destinations.
FILES = {
    'STAGE5_OUTCOME_PUBLIC.json': 'receipts/STAGE5_OUTCOME_PUBLIC.json',
    'STAGE5_RESULT_ZH.md': 'STAGE5_RESULT_ZH.md',
    'control/build_stage5_outcome.py': 'control/build_stage5_outcome.py',
    'control/stage5_closure_control.py': 'control/stage5_closure_control.py',
    'control/STAGE5_CLOSURE_PUBLIC.json': 'receipts/STAGE5_CLOSURE_PUBLIC.json',
    'control/ASTRA_PREPARE_PUBLIC.json': 'receipts/ASTRA_PREPARE_PUBLIC.json',
    'control/ASTRA_LAUNCH_PUBLIC.json': 'receipts/ASTRA_LAUNCH_PUBLIC.json',
    'control/ASTRA_FAILURE_INSPECTION_PUBLIC.json': 'receipts/ASTRA_FAILURE_INSPECTION_PUBLIC.json',
    'control/ASTRA_FAILURE_INSPECTION_V2_PUBLIC.json': 'receipts/ASTRA_FAILURE_INSPECTION_V2_PUBLIC.json',
    'control/ASTRA_DIAGNOSTIC_TRANSPORT_PUBLIC.json': 'receipts/ASTRA_DIAGNOSTIC_TRANSPORT_PUBLIC.json',
    'control/SCORING_TRANSPORT_PUBLIC.json': 'receipts/SCORING_TRANSPORT_PUBLIC.json',
    'control/PRIMARY_DECISION_INDEPENDENT_CHECK_PUBLIC.json': 'receipts/PRIMARY_DECISION_INDEPENDENT_CHECK_PUBLIC.json',
    'astra_transport_regression/README.md': 'astra_transport_regression/README.md',
    'astra_transport_regression/REGRESSION_PUBLIC.json': 'astra_transport_regression/REGRESSION_PUBLIC.json',
    'astra_transport_regression/ORIGINALS_BEFORE_PUBLIC.json': 'astra_transport_regression/ORIGINALS_BEFORE_PUBLIC.json',
    'astra_transport_regression/test_astra_transport_regression.py': 'astra_transport_regression/test_astra_transport_regression.py',
    'control/stage5_direct_v4_control.py': 'control/stage5_direct_v4_control.py',
    'control/stage5_scoring_control.py': 'control/stage5_scoring_control.py',
    'control/stage5_astra_control.py': 'control/stage5_astra_control.py',
    'control/test_stage5_astra_control.py': 'control/test_stage5_astra_control.py',
    'control/test_stage5_scoring_control.py': 'control/test_stage5_scoring_control.py',
    'control/SCORING_CONTROLLER_ENGINEERING_REVIEW_PUBLIC.json': 'receipts/SCORING_CONTROLLER_ENGINEERING_REVIEW_PUBLIC.json',
    'control/SCORING_CONTROLLER_COMPANION_INSTALL_REVIEW_PUBLIC.json': 'receipts/SCORING_CONTROLLER_COMPANION_INSTALL_REVIEW_PUBLIC.json',
    'control/SCORING_BUNDLE_PRESENCE_PUBLIC.json': 'receipts/SCORING_BUNDLE_PRESENCE_PUBLIC.json',
    'control/PILOT_READINESS_ZH.md': 'control/PILOT_READINESS_ZH.md',
    'pilot_preparation/release_mask.py': 'pilot_preparation/release_mask.py',
    'pilot_preparation/test_release_mask.py': 'pilot_preparation/test_release_mask.py',
    'pilot_preparation/README.md': 'pilot_preparation/README.md',
    'pilot_preparation/ENGINEERING_PUBLIC.json': 'pilot_preparation/ENGINEERING_PUBLIC.json',
    'control/DIRECT_ARM_DEPLOYMENT_PUBLIC.json': 'receipts/DIRECT_ARM_DEPLOYMENT_PUBLIC.json',
    'control/IDENTITY_RESOLUTION_EVIDENCE_PUBLIC.json': 'receipts/IDENTITY_RESOLUTION_EVIDENCE_PUBLIC.json',
    'control/DIRECT_V4_PREPARE_PUBLIC.json': 'receipts/DIRECT_V4_PREPARE_PUBLIC.json',
    'control/DIRECT_V4_LAUNCH_PUBLIC.json': 'receipts/DIRECT_V4_LAUNCH_PUBLIC.json',
    'control/KIMI_V3_HOLD_FINAL_PUBLIC.json': 'receipts/KIMI_V3_HOLD_FINAL_PUBLIC.json',
    'runtime_direct_v4/stage5_common.py': 'runtime_direct_v4/stage5_common.py',
    'runtime_direct_v4/stage5_cloud_worker.py': 'runtime_direct_v4/stage5_cloud_worker.py',
    'runtime_direct_v4/stage5_kimi_gateway.py': 'runtime_direct_v4/stage5_kimi_gateway.py',
    'runtime_direct_v4/stage5_kimi_worker.py': 'runtime_direct_v4/stage5_kimi_worker.py',
    'runtime_direct_v4/stage5_prepare.py': 'runtime_direct_v4/stage5_prepare.py',
    'runtime_direct_v4/stage5_validate_kimi.py': 'runtime_direct_v4/stage5_validate_kimi.py',
    'runtime_direct_v4/test_stage5_direct.py': 'runtime_direct_v4/test_stage5_direct.py',
    'runtime_direct_v4/test_stage5_identity.py': 'runtime_direct_v4/test_stage5_identity.py',
    'runtime_direct_v4/test_stage5_runtime.py': 'runtime_direct_v4/test_stage5_runtime.py',
    'runtime_direct_v4/DIRECT_REPAIR_PUBLIC.json': 'runtime_direct_v4/DIRECT_REPAIR_PUBLIC.json',
    'runtime_direct_v4/README.md': 'runtime_direct_v4/README.md',
    'protocol/DIRECT_NEXT_STAGE_COMMANDS.md': 'protocol/DIRECT_NEXT_STAGE_COMMANDS.md',
    'ASTRA_DIAGNOSTIC_PUBLIC.json': 'receipts/ASTRA_DIAGNOSTIC_PUBLIC.json',
    'control/stage5_direct_control.py': 'control/stage5_direct_control.py',
    'control/DIRECT_KIMI_AUTH_PROBE_PUBLIC.json': 'receipts/DIRECT_KIMI_AUTH_PROBE_PUBLIC.json',
    'control/DIRECT_ROUTE_AMENDMENT_PUBLIC.json': 'receipts/DIRECT_ROUTE_AMENDMENT_PUBLIC.json',
    'control/DIRECT_TRANSITION_IMPORT_PUBLIC.json': 'receipts/DIRECT_TRANSITION_IMPORT_PUBLIC.json',
    'control/DIRECT_PREPARE_PUBLIC.json': 'receipts/DIRECT_PREPARE_PUBLIC.json',
    'control/DIRECT_LAUNCH_PUBLIC.json': 'receipts/DIRECT_LAUNCH_PUBLIC.json',
    'control/KIMI_V2_USER_DIRECT_SWITCH_PUBLIC.json': 'receipts/KIMI_V2_USER_DIRECT_SWITCH_PUBLIC.json',
    'control/KIMI_DIRECT_TRANSITION_PACKAGE_PUBLIC.json': 'receipts/KIMI_DIRECT_TRANSITION_PACKAGE_PUBLIC.json',
    'control/KIMI_DIRECT_TRANSITION_TRANSPORT_PUBLIC.json': 'receipts/KIMI_DIRECT_TRANSITION_TRANSPORT_PUBLIC.json',
    'runtime_direct_v3/stage5_common.py': 'runtime_direct_v3/stage5_common.py',
    'runtime_direct_v3/stage5_cloud_worker.py': 'runtime_direct_v3/stage5_cloud_worker.py',
    'runtime_direct_v3/stage5_kimi_gateway.py': 'runtime_direct_v3/stage5_kimi_gateway.py',
    'runtime_direct_v3/stage5_kimi_worker.py': 'runtime_direct_v3/stage5_kimi_worker.py',
    'runtime_direct_v3/stage5_prepare.py': 'runtime_direct_v3/stage5_prepare.py',
    'runtime_direct_v3/stage5_validate_kimi.py': 'runtime_direct_v3/stage5_validate_kimi.py',
    'runtime_direct_v3/test_stage5_direct.py': 'runtime_direct_v3/test_stage5_direct.py',
    'runtime_direct_v3/test_stage5_runtime.py': 'runtime_direct_v3/test_stage5_runtime.py',
    'control/DIRECT_REPAIR_EXPORT_PUBLIC.json': 'runtime_direct_v3/DIRECT_REPAIR_PUBLIC.json',
    'runtime_direct_v3/REPAIR_PUBLIC_ORIGINAL_6bc66b0b.json': 'runtime_direct_v3/REPAIR_PUBLIC_ORIGINAL_6bc66b0b.json',
    'runtime_direct_v3/README.md': 'runtime_direct_v3/README.md',
    'LUNA_FINAL_PUBLIC.json': 'receipts/LUNA_FINAL_PUBLIC.json',
    'control/KIMI_V1_INCIDENT_PUBLIC.json': 'receipts/KIMI_V1_INCIDENT_PUBLIC.json',
    'control/KIMI_V2_PREPARE_PUBLIC.json': 'receipts/KIMI_V2_PREPARE_PUBLIC.json',
    'control/KIMI_V2_LAUNCH_PUBLIC.json': 'receipts/KIMI_V2_LAUNCH_PUBLIC.json',
    'KIMI_FINAL_PUBLIC.json': 'receipts/KIMI_FINAL_PUBLIC.json',
    'SCORING_PUBLIC.json': 'receipts/SCORING_PUBLIC.json',
    'ASTRA_FINAL_PUBLIC.json': 'receipts/ASTRA_FINAL_PUBLIC.json',
    'PROGRESS_PUBLIC.json': 'receipts/PROGRESS_PUBLIC.json',
    'runtime_transport_v2/stage5_common.py': 'runtime_transport_v2/stage5_common.py',
    'runtime_transport_v2/stage5_cloud_worker.py': 'runtime_transport_v2/stage5_cloud_worker.py',
    'runtime_transport_v2/stage5_kimi_gateway.py': 'runtime_transport_v2/stage5_kimi_gateway.py',
    'runtime_transport_v2/stage5_kimi_worker.py': 'runtime_transport_v2/stage5_kimi_worker.py',
    'runtime_transport_v2/stage5_validate_kimi.py': 'runtime_transport_v2/stage5_validate_kimi.py',
    'runtime_transport_v2/stage5_prepare.py': 'runtime_transport_v2/stage5_prepare.py',
    'runtime_transport_v2/test_stage5_transport.py': 'runtime_transport_v2/test_stage5_transport.py',
    'runtime_transport_v2/test_stage5_runtime.py': 'runtime_transport_v2/test_stage5_runtime.py',
    'runtime_transport_v2/REPAIR_PUBLIC.json': 'runtime_transport_v2/REPAIR_PUBLIC.json',
    'runtime_transport_v2/README.md': 'runtime_transport_v2/README.md',
    'runtime_transport_v2/ORIGINALS_BASELINE_PUBLIC.json': 'runtime_transport_v2/ORIGINALS_BASELINE_PUBLIC.json',
    'control/stage5_control.py': 'control/stage5_control.py',
    'control/stage5_transport_repair_control.py': 'control/stage5_transport_repair_control.py',
    'control/publish_stage5_outcomes.py': 'control/publish_stage5_outcomes.py',
    'control/PUBLICATION_READINESS.md': 'control/PUBLICATION_READINESS.md',
    'protocol/cloud_score_adapter.py': 'protocol/cloud_score_adapter.py',
    'protocol/test_cloud_score_adapter.py': 'protocol/test_cloud_score_adapter.py',
    'protocol/ADAPTER_HANDOFF.md': 'protocol/ADAPTER_HANDOFF.md',
    'protocol/ADAPTER_VERIFICATION_PUBLIC.json': 'protocol/ADAPTER_VERIFICATION_PUBLIC.json',
    'protocol/astra_diagnostic_compare.py': 'protocol/astra_diagnostic_compare.py',
    'protocol/test_astra_diagnostic_compare.py': 'protocol/test_astra_diagnostic_compare.py',
    'protocol/NEXT_STAGE_READINESS.md': 'protocol/NEXT_STAGE_READINESS.md',
    'protocol/NEXT_STAGE_COMMANDS.md': 'protocol/NEXT_STAGE_COMMANDS.md',
    'protocol/NEXT_STAGE_READINESS_PUBLIC.json': 'protocol/NEXT_STAGE_READINESS_PUBLIC.json',
}
FORBIDDEN_JSON_KEYS = {
    'full_document', 'context_sha256', 'normalized_context_sha256', 'canonical_key',
    'canonical_keys', 'source_row', 'record_source_row', 'record_id', 'job_hash',
    'case', 'case_id', 'task_id', 'source_task', 'packet_id', 'row', 'rows_private',
    'response_text', 'model_output', 'raw_text', 'source_text', 'description',
    'messages', 'choices', 'quotes', 'evidence_text', 'access_token', 'refresh_token',
    'client_secret', 'api_key', 'password', 'container_sas',
}


class PublicationError(Exception): pass


def need(condition, reason):
    if not condition: raise PublicationError(reason)


def sha(data): return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def load_scanner():
    p = B / 'scan_public_git.py'
    need(p.is_file() and not p.is_symlink(), 'scanner_missing_or_symlinked')
    spec = importlib.util.spec_from_file_location('stage5_public_scanner', p)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    need(module.self_tests()['all_passed'], 'existing_scanner_self_tests_failed')
    return module


def safe_source(p):
    need(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(D.resolve()), 'source_missing_or_unsafe')
    need(not any(parent.is_symlink() for parent in p.parents if parent.is_relative_to(D)), 'source_symlink_parent')


def no_private_json(x):
    if isinstance(x, dict):
        for k, v in x.items():
            need(not (str(k).lower() in FORBIDDEN_JSON_KEYS and v not in (None, '', [], {})), 'private_value_key_in_public_receipt')
            no_private_json(v)
    elif isinstance(x, list):
        for v in x: no_private_json(v)
    elif isinstance(x, str):
        need(not re.search(r'\bcorpus-pro-[0-9a-f]{64}\b|\bcase\d{4}\b', x), 'row_identifier_in_public_receipt')


def redact_public_strings(value, scanner):
    if isinstance(value, str):
        value = value.replace('127\0560\0560\0561', 'localhost')
        value = re.sub(scanner.RULES['machine_private_absolute_path'], '[private-runtime-path]', value)
        # The only accepted UUID is a fixed deny marker. All other UUIDs fail.
        return re.sub(scanner.RULES['uuid_identifier'],
            lambda m: 'provider-protected-thread' if sha(m.group().encode()) == PROTECTED_LITERAL_SHA else m.group(), value)
    if isinstance(value, dict): return {k: redact_public_strings(v, scanner) for k, v in value.items()}
    if isinstance(value, list): return [redact_public_strings(v, scanner) for v in value]
    return value


def render_python(source):
    before = ast.dump(ast.parse(source), include_attributes=False)
    tokens = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.STRING and '127\0560\0560\0561' in token.string:
            token = token._replace(string=token.string.replace('127\0560\0560\0561', r'127\0560\0560\0561'))
        tokens.append(token)
    result = tokenize.untokenize(tokens)
    need(ast.dump(ast.parse(result), include_attributes=False) == before, 'public_python_AST_not_value_equivalent')
    compile(result, '<public-stage5-code>', 'exec')
    return result


def scanned_bytes(text, suffix, target_rel, scanner):
    data = text.encode(); need(len(data) <= scanner.MAX_BYTES and '\x00' not in text, 'public_size_or_nul_gate')
    digest = sha(data); exemptions = []
    # Resolve only explicit operating paths, never arbitrary machine paths.
    path_literals = {sha(m.group().encode()): m.group()
        for m in re.finditer(scanner.RULES['machine_private_absolute_path'], text)}
    for issue in scanner.scan_text(text):
        rule = issue['rule']; allowed = False
        if suffix == '.py' and rule == 'uuid_identifier':
            allowed = issue['literal_sha256'] == PROTECTED_LITERAL_SHA
        elif suffix == '.py' and rule == 'machine_private_absolute_path':
            value = path_literals.get(issue['literal_sha256'], '')
            allowed = any(value == prefix.rstrip('/') or value.startswith(prefix) for prefix in OPERATING_PREFIXES)
        need(allowed, 'unapproved_public_scan_finding:' + rule)
        exemptions.append({'file': target_rel, 'file_sha256': digest, **issue,
            'review_reason': 'Fixed deny-only protection marker or explicitly scoped operational code path; no credential, advertisement identity, body, or model response.'})
    if suffix == '.json':
        obj = json.loads(text); no_private_json(obj)
        need(not scanner.scan_json_values(obj), 'repository_JSON_value_scanner_failed')
    return data, exemptions


def render_file(relative, scanner):
    p = D / relative; safe_source(p)
    original = p.read_bytes(); need(len(original) <= scanner.MAX_BYTES, 'source_public_size_cap')
    source = original.decode('utf-8'); obj = None
    if p.suffix == '.py': text = render_python(source)
    elif p.suffix == '.json':
        obj = json.loads(source); no_private_json(obj)
        text = encode(redact_public_strings(obj, scanner)).decode()
    elif p.suffix == '.md': text = redact_public_strings(source, scanner)
    else: raise PublicationError('unsupported_explicit_source_type')
    target_rel = PUB_REL + '/' + FILES[relative]
    data, exemptions = scanned_bytes(text, p.suffix, target_rel, scanner)
    return data, exemptions, {'source': relative, 'source_sha256': sha(original),
        'published_sha256': sha(data), 'bytes': len(data),
        'transformation': 'Python AST preserved; loopback string syntax only' if p.suffix == '.py'
            else 'Public strings omit machine paths and fixed protection marker; aggregate values preserved'}, obj


def validate_aggregate_cross_checks(objects):
    legs = {}
    for name, leg in [('LUNA_FINAL_PUBLIC.json', 'Luna'), ('KIMI_FINAL_PUBLIC.json', 'Kimi'), ('ASTRA_FINAL_PUBLIC.json', 'Astra')]:
        if name not in objects: continue
        x = objects[name]
        need(x.get('leg') == leg and x.get('terminal_no_active_requests') is True, 'final_receipt_not_terminal_expected_leg')
        need(isinstance(x.get('selected'), int) and 0 <= x['selected'] <= (6 if leg == 'Astra' else 150), 'final_receipt_selection_cap')
        need(x.get('outputs_accounted') == x['selected'], 'final_receipt_accounting_incomplete')
        for key in ['logical_calls', 'physical_attempts', 'reserved_usd', 'input_tokens', 'output_tokens']:
            need(isinstance(x.get(key), (int, float)) and not isinstance(x.get(key), bool) and x[key] >= 0, 'final_receipt_numeric_accounting_invalid')
        legs[leg] = {key: x[key] for key in ['selected', 'outputs_accounted', 'logical_calls', 'physical_attempts', 'reserved_usd', 'input_tokens', 'output_tokens']}
        if 'field_validation_complete' in x: legs[leg]['field_validation_complete'] = x['field_validation_complete']
        legs[leg]['terminal_no_active_requests'] = True
    if all(n in objects for n in ['LUNA_FINAL_PUBLIC.json', 'KIMI_FINAL_PUBLIC.json']):
        a, b = objects['LUNA_FINAL_PUBLIC.json'], objects['KIMI_FINAL_PUBLIC.json']
        need(a['selected'] == b['selected'] and a['roster_sha256'] == b['roster_sha256'], 'Luna_Kimi_final_rosters_disagree')
    return legs


def make_plan(scanner, only=None):
    names = sorted(FILES if not only else set(only))
    need(set(names) <= set(FILES), 'source_not_in_fixed_publication_list')
    rendered, exemptions, copies, objects, missing = {}, [], {}, {}, []
    for relative in names:
        if not (D / relative).exists(): missing.append(relative); continue
        data, ex, copy, obj = render_file(relative, scanner)
        dest = FILES[relative]; rendered[dest] = data; copies[dest] = copy; exemptions.extend(ex)
        if obj is not None: objects[relative] = obj
    need(rendered, 'no_explicit_source_files_available')
    legs = validate_aggregate_cross_checks(objects)
    manifest = {'status': 'public_outcomes_snapshot_prepared', 'public_files': copies,
        'terminal_leg_accounting': legs, 'missing_future_or_unselected_files_not_inferred_complete': missing,
        'score_aggregate_receipt_included': 'SCORING_PUBLIC.json' in objects,
        'v1_incident_preserved': 'control/KIMI_V1_INCIDENT_PUBLIC.json' in objects,
        'original_runtime_v1_and_initial_delivery_manifest_unchanged': True,
        'published_code_not_claimed_identical_to_executed_bytes_after_literal_rendering': True,
        'field_quality_or_pilot_release_inferred': False, 'actual_Azure_invoice_claimed': False,
        'raw_text_row_outputs_or_credentials_published': False, 'Git_operations_performed': False}
    rendered['PUBLIC_OUTCOMES_MANIFEST.json'], _ = scanned_bytes(encode(manifest).decode(), '.json', PUB_REL+'/PUBLIC_OUTCOMES_MANIFEST.json', scanner)
    status = ['# 阶段五公开结果快照', '', '本快照按实际终态回执记录计数，保留原启动记录和传输第一版事件。模型输出槽位已记账不等于语义通过。', '']
    for leg, x in legs.items():
        status.append(f"- {leg}：{x['outputs_accounted']} 个槽位完成记账，{x['physical_attempts']} 次物理请求，保守预留 ${x['reserved_usd']:.8f}。")
    if not legs: status.append('尚未纳入终态回执。')
    if 'STAGE5_OUTCOME_PUBLIC.json' in objects:
        outcome = objects['STAGE5_OUTCOME_PUBLIC.json']
        need(outcome['eligible_measures'] == [] and outcome['Astra_failure']['diagnostic_judgments_received'] == 0, 'closing_decision_summary_changed')
        status += ['', '**实际决定：51项独立研究量，26项支持/参考覆盖不足，25项支持足但指标未达标，合格项0，试产未启动。**',
            'Astra的6个槽位均为HTTP400请求错误，没有审核答案；不能把终态记账称为审核完成。错误复盘与未应用修复另存。',
            '当前阶段五模型进程已结束。详见STAGE5_RESULT_ZH.md；本轮主确认结束不等于五亿语义目标完成。']
    if 'control/DIRECT_V4_LAUNCH_PUBLIC.json' in objects:
        status += ['', '按用户最新指令，OpenCode 已停止；当前 Kimi 为现有 Azure VM 托管身份直接调用。v4 导入此前 11 次真实响应及全部预算，从剩余 124 条继续；不重复请求旧输入。ARM 部署与响应头均核实 300 万 TPM，本次固定确认仍使用原保守调度上限。',
            'v3 因返回模型短名与部署全名不同而保护暂停；部署身份核查及精确投影证据保留，旧账本不改。v4 只修正运行身份核验，不改变模型请求、输入、评分规则；厂商官方别名未宣称获证。',
            '启动不等于完成；实际运行终态、字段结果与试产状态以本快照所含回执为准。']
    elif 'control/DIRECT_LAUNCH_PUBLIC.json' in objects:
        status += ['', '按用户最新指令，OpenCode 已停止；Kimi 改为现有 Azure VM 托管身份直接调用。旧通道 10 条已完成响应及预算已导入，剩余 125 条从真实断点继续。实际响应头核实配额为 300 万 TPM，本次确认仍使用冻结的保守调度上限。',
            '直连启动只代表任务已派发，完成情况以最终账本与评分回执为准；不得把启动或已保存直接视为字段合格。']
    status += ['', '字段评分以纳入的独立汇总回执为准；本发布器不推断合格字段、不放行试产、不把机器间一致性写成人工或全库准确率。金额为运行账本预留，未声称核验 Azure 发票。',
        '', '历史传输版、首个直连版及身份核验修正版分别保存在 runtime_transport_v2、runtime_direct_v3、runtime_direct_v4；此前版本保留但不再启动 OpenCode。Python 公开副本只改变回环地址字符串的字面书写；AST 和字符串值保持相同，原执行字节和 SHA 仍单独保留。',
        '', '所有来源均为明确列出的公开汇总、代码和交接文件。正文、逐条身份、输出内容、私有映射和凭据不发布。', '']
    rendered['OUTCOMES_STATUS_ZH.md'], _ = scanned_bytes('\n'.join(status), '.md', PUB_REL+'/OUTCOMES_STATUS_ZH.md', scanner)
    plan = {'files': {name: sha(data) for name, data in sorted(rendered.items())}, 'sources': copies,
        'scanner_sha256': sha((B/'scan_public_git.py').read_bytes()), 'missing': missing}
    plan_sha = sha(encode(plan))
    return rendered, exemptions, plan, plan_sha


def apply_plan(rendered, exemptions, plan, expected, plan_sha):
    need(expected == plan_sha, 'reviewed_plan_SHA_required_or_changed')
    allowpath = B/'PUBLIC_GIT_ALLOWLIST.json'
    need(allowpath.is_file() and not allowpath.is_symlink(), 'allowlist_missing_or_symlinked')
    allow = json.loads(allowpath.read_bytes())
    need(allow['root_repo_relative_path'] == ROOT_REL, 'allowlist_scope_mismatch')
    need(sha((B/'scan_public_git.py').read_bytes()) == plan['scanner_sha256'], 'scanner_changed_during_publication')
    for info in plan['sources'].values():
        p = D/info['source']; safe_source(p)
        need(sha(p.read_bytes()) == info['source_sha256'], 'source_changed_since_reviewed_plan')
    targets = {}
    for relative, data in rendered.items():
        target = OUT/relative
        need(target.resolve().is_relative_to(OUT.resolve()) and not target.is_symlink(), 'unsafe_public_target')
        need(not any(p.is_symlink() for p in target.parents if p.is_relative_to(REPO)), 'public_target_symlink_parent')
        targets[target] = data
    names = {PUB_REL+'/'+name for name in rendered}
    allow['allowed_files'] = sorted(set(allow['allowed_files']) | names)
    allow['reviewed_literal_exemptions'] = [e for e in allow.get('reviewed_literal_exemptions', []) if e['file'] not in names] + exemptions
    # All sources/transforms/scans pass before the first write. Only explicit
    # destinations and their own exemption entries change; no source is edited.
    for target, data in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    allowpath.write_bytes(encode(allow))


def self_tests(scanner):
    passed = []
    sample = 'url = "http://127\0560\0560\0561:1234/api"\n'
    rendered = render_python(sample)
    need('127\0560\0560\0561' not in rendered and ast.dump(ast.parse(sample)) == ast.dump(ast.parse(rendered)), 'test_AST_equivalence')
    passed.append('loopback_full_AST_value_equivalence')
    for name, x in [('body', {'full_document':'synthetic body'}), ('context', {'context_sha256':'a'*64}), ('row', {'record_id':'synthetic'})]:
        try: no_private_json(x)
        except PublicationError: passed.append('reject_'+name)
        else: raise PublicationError('private_JSON_detector_test_failed')
    try: render_python('value = r"127\0560\0560\0561"\n')
    except PublicationError: passed.append('reject_value_changing_raw_string_render')
    else: raise PublicationError('raw_string_equivalence_test_failed')
    path = '/home/linkup/migration/example/data'
    cleaned = redact_public_strings({'runtime_path':path}, scanner)
    need(cleaned['runtime_path']=='[private-runtime-path]' and not scanner.scan_text(encode(cleaned).decode()), 'path_redaction_test_failed')
    passed.append('receipt_path_redaction')
    try: scanned_bytes('record_id = "'+'b'*32+'"\n', '.py', 'synthetic.py', scanner)
    except PublicationError: passed.append('record_identifier_cannot_be_exempted')
    else: raise PublicationError('record_identifier_exemption_test_failed')
    need(set(FILES.values()) and len(FILES.values())==len(set(FILES.values())), 'duplicate_explicit_destinations')
    need(all(not d.startswith('runtime/') for d in FILES.values()), 'runtime_v1_overwrite_test_failed')
    passed.append('exact_destinations_preserve_runtime_v1')
    return {'publisher_tests_passed':len(passed), 'publisher_tests_total':8,
            'all_passed':len(passed)==8, 'repository_scanner':scanner.self_tests()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Copy the reviewed explicit plan; never stage, commit, or push.')
    parser.add_argument('--expect-plan-sha', help='Required with --apply; use the digest from a prior dry-run.')
    parser.add_argument('--only', action='append', choices=sorted(FILES), help='Restrict to named entries; repeat as needed.')
    parser.add_argument('--self-test', action='store_true', help='Pure in-memory tests; no publication writes.')
    args = parser.parse_args()
    try:
        scanner = load_scanner(); tests = self_tests(scanner)
        if args.self_test:
            need(not args.apply, 'self_test_cannot_apply'); print(json.dumps(tests, sort_keys=True)); return 0
        rendered, exemptions, plan, plan_sha = make_plan(scanner, args.only)
        if args.apply: apply_plan(rendered, exemptions, plan, args.expect_plan_sha, plan_sha)
        print(json.dumps({'status':'public_outcomes_copied_not_staged' if args.apply else 'dry_run_publication_ready',
            'plan_sha256':plan_sha, 'public_files':plan['files'], 'missing_explicit_files':plan['missing'],
            'reviewed_literal_exemptions':len(exemptions), 'tests':tests, 'sources_unchanged':True,
            'repository_writes':args.apply, 'git_stage_commit_push':False,
            'required_next_repository_scanner':'python3 -B linkup/reuse_first_20261115/scan_public_git.py --check-staged'}, sort_keys=True))
        return 0
    except (PublicationError, UnicodeDecodeError, json.JSONDecodeError, SyntaxError) as e:
        print(json.dumps({'status':'publication_stopped', 'reason':str(e) if isinstance(e,PublicationError) else type(e).__name__,
            'no_Git_operations':True}, sort_keys=True)); return 2


if __name__ == '__main__': raise SystemExit(main())
