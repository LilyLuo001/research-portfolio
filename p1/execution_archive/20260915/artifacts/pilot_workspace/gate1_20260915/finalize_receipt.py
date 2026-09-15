"""Reconcile small control artifacts; never read native DBN bodies or secrets."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
A=OUT.parent/'missing_data_round_20260914/databento_final_acquisition'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p):return json.loads(p.read_text())
def csvrows(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))

selection=js(A/'selection_receipt.json')
recovery=js(A/'gap_recovery_receipt.json')
grouping=js(A/'grouping_receipt.json')
header=js(OUT/'header_audit_receipt.json')
manifest=csvrows(A/'download_manifest.csv')
ids={r['job_id'] for r in manifest}
invariants={
 'unique_download_job_ids':len(ids)==len(manifest),
 'selected_ids_equal_final_manifest_ids':set(selection['selected_job_ids'])==ids,
 'final_manifest_matches_recovery_receipt':sha(A/'download_manifest.csv')==recovery['download_manifest_sha256'],
 'final_manifest_matches_remote_header_input':sha(A/'download_manifest.csv')==header['inputs']['download_manifest.csv'],
 'quotes_match_frozen_selection':sha(A/'quote_jobs.csv')==selection['quote_jobs_sha256'],
 'grouping_receipt_matches_selection':sha(A/'grouping_receipt.json')==selection['grouping_receipt_sha256'],
 'all_grouped_control_hashes_match':all(sha(A/name)==digest for name,digest in grouping['output_hashes'].items()),
 'three_recovered_jobs_in_manifest':set(recovery['recovered_job_ids']).issubset(ids),
 'four_excluded_jobs_not_in_manifest':not(set(selection['excluded_unquoted_or_failed_job_ids']) & ids),
 'archive_labeled_jobs_in_sealed_post_path':all('/sealed_post/' in r['path'] for r in manifest if r['analysis_access'].startswith('ARCHIVE')),
 'all_downloads_header_match':header['job_status'].get('HEADER_CONTRACT_MATCH')==len(manifest),
}
assert all(invariants.values()),invariants
receipt=dict(utc=datetime.now(timezone.utc).isoformat(),decision='HOLD_DATA_AND_HOLD_DESIGN',measurement_gate='NOT_PASSED',selected_acquisition='STRUCTURALLY_ACCOUNTED_FOR',planned_acquisition='FOUR_EXPLICIT_QUOTE_FAILURE_GAPS',invariants=invariants,excluded_jobs=selection['excluded_unquoted_or_failed_job_ids'],recovered_jobs=recovery['recovered_job_ids'],full_dbn_hashing='NOT_RESTARTED_PER_USER',body_integrity='NOT_CERTIFIED',post_response_analysis=False,charged_vendor_calls=0,new_scc_jobs='HEADER_ONLY_AUDIT_NO_SCHEDULER_SUBMISSION',billing_reconciled=False,requested_agent_routing={'gate1_spec':'gpt-5.6-sol/medium','gate1_referee':'gpt-6-astra/high'},effective_backend_model_effort_telemetry='NOT_OBSERVED',code_and_artifact_hashes={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='run_manifest.json'},source_receipt_hashes={name:sha(A/name) for name in ['selection_receipt.json','grouping_receipt.json','gap_recovery_receipt.json','download_manifest.csv']})
(OUT/'run_manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(decision=receipt['decision'],invariants=invariants),indent=2))
