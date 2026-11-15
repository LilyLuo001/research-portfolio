"""Freeze a mixed-source 500-context metadata frame before inference; not a callable input queue."""
import json,sqlite3,hashlib,collections,datetime,os
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';S=B/'stage2';V=S/'revision003';O=B/'qualification_frame_v1';os.umask(0o077);O.mkdir(exist_ok=False)
db=sqlite3.connect((V/'REUSED_VALUES_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);idx=sqlite3.connect((R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);blocked={h for h, in idx.execute('select h from blocked')};old20=json.loads((R/'reuse_first_20261115/run01/benchmark20/SELECTION_PRIVATE.json').read_text());excluded=blocked|{x['context_sha256'] for x in old20}
validation=json.loads((S/'revision002/PRIMARY_VALIDATION_PRIVATE.json').read_text());failed=set();passed=set();input_by_context={}
for v in validation:
 for h in v['contexts']:input_by_context.setdefault(h,set()).add(v.get('input_sha256'))
 if v['status']=='frozen_mechanical_pass_still_saved_unverified':passed.update(v['contexts'])
# Only error IDs known to the trusted original index; no quoted text is inspected here.
for p in (S/'revision002/validation').glob('*/ERRORS_PRIVATE.jsonl'):
 for l in p.open():
  x=json.loads(l);rid=x.get('record_id','') or ''
  if rid.startswith('corpus-pro-'):
   h=rid.removeprefix('corpus-pro-')
   if h in input_by_context:failed.add(h)
pools={
 'original_accepted_Pro':{h for h, in db.execute("select distinct h from document where asset='Pro' and original_accepted=1")},
 'existing_Kimi_saved':{h for h, in db.execute("select distinct h from document where asset='Kimi_saved_unverified'")},
 'ordinary_Pro_frozen_error':failed-passed,
 'ordinary_Pro_saved_pass':passed,
}
quotas={'original_accepted_Pro':200,'existing_Kimi_saved':150,'ordinary_Pro_frozen_error':100,'ordinary_Pro_saved_pass':50};selected=[];used=set(excluded);availability={}
for group,n in quotas.items():
 eligible=pools[group]-used;availability[group]=len(eligible);assert len(eligible)>=n,'insufficient_predeclared_stratum_no_replacement'
 order=sorted(eligible,key=lambda h:hashlib.sha256(('qualification_mixed_20261116_v1|'+group+'|'+h).encode()).hexdigest())[:n]
 for i,h in enumerate(order):
  selected.append({'context_sha256':h,'stratum':group,'split':'development' if i<int(n*.4) else 'heldout','source_document_pins':[{'asset':a,'sha256':s,'ordinal':o,'original_accepted':bool(ac)} for a,s,o,ac in db.execute('select asset,source_sha,source_ordinal,original_accepted from document where h=?',(h,))],'already_cached_prepared_input_shas':sorted(x for x in input_by_context.get(h,set()) if x),'inference_admitted':False,'purpose':'bounded_model_qualification_not_production','reference_policy':'reuse_prior_blind_Kimi' if group=='existing_Kimi_saved' else 'new_independent_Kimi_reference_required'})
 used.update(order)
assert len(selected)==len({x['context_sha256'] for x in selected})==500;assert all(x['context_sha256'] not in excluded for x in selected)
# Do not change original masks. Record uncertainty and no-hit coverage rather than selecting only easy rows.
mask_counts=collections.Counter()
for x in selected:
 for family,status in idx.execute('select family,status from field where h=?',(x['context_sha256'],)):mask_counts[(x['split'],family,status)]+=1
(O/'FRAME_PRIVATE.json').write_text(json.dumps(selected,indent=2)+'\n');split=collections.Counter(x['split'] for x in selected)
protocol={'status':'metadata_frame_frozen_inputs_and_runtime_not_yet_admitted','selected_contexts':500,'split':dict(split),'strata':quotas,'stratum_eligible_counts_before_selection':availability,'previous20_and_all_known_protection_excluded':True,'unknown_and_no_hit_not_filtered_out':True,'new_Luna_calls_max':500,'new_Kimi_reference_calls_max':350,'existing_Kimi_reference_reuses':150,'new_Astra_audit_calls_max':50,'total_stage_cap_usd':250,'no_human_review':True,'inputs_require_full_SHA_validation_before_admission':True,'new_production_accepted':0,'model_calls_this_preparation':0,'scope':'known historical prepared contexts; tests passed, unknown/no-hit and ordinary failed-output strata, but does not certify unseen full-corpus sources','prior_frozen_error_handling':'New independent qualification references are separate from failed original Pro outputs; not a retry of their production task and no old result is replaced. Provider blocks and Kimi retry-forbidden cases are excluded.','gate':'Per-field machine-reference P>=.90 R>=.80 MacroF1>=.85 with support and source-evidence checks; absent/failed/unknown outcomes remain explicit. Not human ground truth. Step4 also needs a confirmed nonduplicate missing-field queue.','paper_paused':True,'frame_sha256':hashlib.sha256((O/'FRAME_PRIVATE.json').read_bytes()).hexdigest(),'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(O/'PROTOCOL_PUBLIC.json').write_text(json.dumps(protocol,indent=2)+'\n');(O/'FIELD_MASK_COUNTS_PUBLIC.json').write_text(json.dumps([{'split':s,'field':f,'status':st,'n':n} for (s,f,st),n in sorted(mask_counts.items())],indent=2)+'\n');print(json.dumps(protocol))
