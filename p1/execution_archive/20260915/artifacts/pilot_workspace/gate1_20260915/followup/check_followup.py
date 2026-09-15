"""Offline validation of the bounded follow-up packet."""
import ast,csv,hashlib,json,os
from collections import Counter
from pathlib import Path
O=Path(__file__).resolve().parent
with (O/'CRD_CLASS_B_REPAIR_REQUESTS.csv').open(newline='') as f:r=list(csv.DictReader(f))
q=json.loads((O/'FREE_SYMBOLOGY_QUERIES.json').read_text())
src=json.loads((O/'identity_clock_receipt.json').read_text())
tree=ast.parse((O/'resolve_free_symbology.py').read_text())
attrs={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
checks={
 '192_unique_repair_windows':len(r)==192==len({x['repair_id'] for x in r}),
 '48_windows_each_feed':set(Counter(x['dataset'] for x in r).values())=={48},
 'no_companion_symbol_repurchase':all(x['proposed_symbol'] in {'CRD.B','CRD B'} for x in r),
 'historical_class_B_all12':src['identity']['crd_class_counts']=={'B':12},
 'source_metadata_match_852':src['clock_metadata']['date_agreement']==852==src['clock_metadata']['time_agreement'],
 'four_free_queries':len(q)==4,
 'no_charged_endpoint_in_runner':not (attrs & {'timeseries','get_range','batch','submit_job','live','reference'}),
 'source_projection_excludes_values':not(set(src['approved_columns']['actuals_metadata_projection']) & {'value','price','ret','bid_px','ask_px','forecast'}),
}
assert all(checks.values()),checks
out=dict(status='BOUNDED_FOLLOWUP_COMPLETE_CLOCK_EVIDENCE_AND_FREE_AUTH_PENDING',checks=checks,new_agent_dispatches=0,charged_calls=0,free_symbology_status='NOT_RUN_AUTH_ENV_ABSENT',local_key_env_present=bool(os.environ.get('DATABENTO_API_KEY')),post_response_decode=False,gate1='NOT_PASSED',independent_new_agent_review='NOT_COMMISSIONED_BOUNDED_SCRIPT_CHECK_ONLY',artifact_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='followup_receipt.json'})
(O/'followup_receipt.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(checks,indent=2))
