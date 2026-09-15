"""Hash only small plan artifacts; never open research data or credentials."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

BASE = Path(__file__).resolve().parent
CONTRACT = Path('/Users/lilyluo/research-portfolio-p1-feasibility-20260913/p1/feasibility_adjudication/20260913/reconciliation/estimation_contract.reconciled.PROPOSED.yaml')
EXPECTED_CONTRACT = '00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

names = ['START_HERE.md', 'PILOT_RESEARCH_PLAN.md', 'DATA_GAP_MATRIX.md', 'PLAN_REVIEW.md', 'finalize_plan_receipt.py']
assert all((BASE / name).is_file() for name in names)
assert sha(CONTRACT) == EXPECTED_CONTRACT
plan_hash = sha(BASE / 'PILOT_RESEARCH_PLAN.md')
review = (BASE / 'PLAN_REVIEW.md').read_text()
assert plan_hash in review, 'Independent review must name the final plan hash'
assert 'PASS_WITH_LIMITATIONS' in review

receipt = {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'task': 'P1 entire pilot research plan; pause Gate 1 verification',
    'status': 'PLAN_COMPLETE_REVIEWED_NOT_EXECUTED',
    'research_status': ['HOLD_DESIGN', 'HOLD_DATA'],
    'gate1': 'PAUSED_NOT_PASSED',
    'contract': {'path': str(CONTRACT), 'sha256': EXPECTED_CONTRACT, 'status': 'PROPOSAL_NOT_PI_APPROVED'},
    'artifacts': {name: {'path': str(BASE / name), 'sha256': sha(BASE / name)} for name in names},
    'delegation': [
        {'role': 'coordinator', 'requested': 'retain existing coordinator', 'effective_model_effort': 'NOT_OBSERVED'},
        {'role': 'local evidence inventory', 'agent': '/root/pilot_inventory', 'requested_model': 'gpt-5.6-sol', 'requested_effort': 'medium', 'dispatch_accepted': True, 'effective_backend_telemetry': 'NOT_OBSERVED'},
        {'role': 'independent bounded plan referee', 'agent': '/root/pilot_plan_referee', 'requested_model': 'gpt-6-astra', 'requested_effort': 'high', 'dispatch_accepted': True, 'effective_backend_telemetry': 'NOT_OBSERVED'},
    ],
    'scope_record': {
        'local_docs_receipts_code_only': True,
        'official_model_and_primary_methodology_web_read': True,
        'raw_research_values_read': False,
        'scc_access_this_turn': False,
        'provider_queries_or_contact_this_turn': False,
        'market_data_download_this_turn': False,
        'data_spend_this_turn_usd': 0,
        'post_response_unsealed': False,
        'empirical_power_run': False,
        'treatment_effect_run': False,
        'commit_push_merge': False,
        'configuration_or_authentication_changed': False,
        'full_archive_hashing': False,
    },
    'validation': {'required_artifacts_present': True, 'baseline_contract_hash_matches': True, 'review_references_final_plan_hash': True},
    'next_action': 'One zero-purchase outcome-blind P0/P1/P3 design build; queue necessary P2 measurement, not another Gate1 audit',
    'limitations': ['Planning pass is not scientific GO', 'Full realized PRE+POST numeric rank not observed', 'New scientific choices remain explicitly proposed', 'Future workpackets have not been executed'],
}
(BASE / 'PLAN_RECEIPT.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'status': receipt['status'], 'plan_sha256': plan_hash, 'validated_artifacts': len(names)}, indent=2))
