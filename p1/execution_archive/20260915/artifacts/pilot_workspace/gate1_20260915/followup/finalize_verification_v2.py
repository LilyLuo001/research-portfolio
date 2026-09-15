import ast,hashlib,json
from decimal import Decimal
from pathlib import Path
O=Path(__file__).resolve().parent
s=json.loads((O/'free_symbology_responses.json').read_text())
r=json.loads((O/'repair_mapping_receipt.json').read_text())
q=json.loads((O/'four_quote_recheck.json').read_text())
checks=dict(four_symbology_responses=len(s)==4 and all(x['status']=='RESPONSE_RECEIVED' for x in s),no_partial_or_notfound=all(not x['response']['partial'] and not x['response']['not_found'] for x in s),all192windows_mapped=r['all_dates_mapped_windows']==192 and r['gap_windows']==0,four_exact_requotes=len(q['results'])==4 and all('cost' in x and 'record_count' in x for x in q['results']))
attrs=set()
for name in ['resolve_free_symbology.py','recheck_four_quotes.py']:
    tree=ast.parse((O/name).read_text());attrs|={x.attr for x in ast.walk(tree) if isinstance(x,ast.Attribute)}
checks['no_charged_endpoint_in_executed_api_scripts']=not(attrs&{'timeseries','get_range','batch','submit_job','live','reference'})
assert all(checks.values()),checks
receipt=dict(status='SYMBOL_MAPPING_VALIDATED_CLOCK_BRIDGE_PENDING',gate1='NOT_PASSED',checks=checks,free_symbology_calls=4,free_cost_count_calls=8,download_calls=0,post_response_decode=False,requested_new_agent_dispatches=0,original_four_request_quote_total_usd=str(sum(Decimal(str(x['cost'])) for x in q['results'])),total_CRD_repair_cost='NOT_QUOTED',artifact_hashes={str(p.relative_to(O)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(O.rglob('*')) if p.is_file() and '__pycache__' not in str(p) and p.name!='verification_v2_receipt.json'})
(O/'verification_v2_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='artifact_hashes'},indent=2))
