#!/usr/bin/env python3
"""Offline finalization for a completed frozen P1 download.

No credential lookup and no API call. POST_FOCAL DBN is never decoded: only
existence/size/hash are inspected. PRE_FOCAL DBN may be decoded solely for
coverage and aggregate endpoint-state QA; no prices are written to output.
"""
from __future__ import annotations
import argparse,bisect,csv,hashlib,json,pathlib
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'delivery'; NY=ZoneInfo('America/New_York')
def jread(p): return json.loads(pathlib.Path(p).read_text())
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def jwrite(p,x): pathlib.Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def cwrite(p,fields,rows):
 with pathlib.Path(p).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def cid(r): return hashlib.sha256('\x1f'.join(r[x] for x in ('dataset','schema','symbols','stype_in','start','end')).encode()).hexdigest()
def utc_bound(local_date,clock): return datetime.fromisoformat(local_date+'T'+clock).replace(tzinfo=NY).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def ns(x):
 """Comparable timestamp only; avoids all quote fields."""
 raw=getattr(x,'value',x)
 if isinstance(raw,datetime): return int(raw.timestamp()*1_000_000_000)
 return int(raw)
def iso_ns(value):
 if value in (None,'', 'UNKNOWN'): return ''
 seconds,nanos=divmod(int(value),1_000_000_000)
 return (datetime.fromtimestamp(seconds,timezone.utc)+timedelta(microseconds=nanos//1000)).isoformat().replace('+00:00','Z')
def pre_metrics(path,allowed):
 """The only DBN decode path. Returned state is in-memory only, never emitted."""
 try:
  import databento as db
  count=0; instruments=set(); times=[]; states={}
  for rec in db.DBNStore.from_file(path):
   stamp=getattr(rec,'ts_recv',None) or getattr(rec,'ts_event',None)
   if stamp is None: continue
   t=ns(stamp)
   # For a mixed file, do not access any quote field unless its receive clock
   # is in an event-authorized PRE subwindow. POST values remain untouched.
   if not any(lo<=t<hi for lo,hi in allowed): continue
   count+=1;instruments.add(str(getattr(rec,'instrument_id','UNKNOWN')));times.append(t)
   # Endpoint equality is tested internally only; aggregate results are emitted.
   states[t]=tuple(getattr(rec,x,None) for x in ('bid_px_00','ask_px_00','bid_sz_00','ask_sz_00'))
  return {'status':'PRE_STRUCTURAL_QA','records':count,'instruments':';'.join(sorted(instruments)),'times':times,'states':states,'exception':''}
 except Exception as e: return {'status':'PRE_QA_EXCEPTION_UNKNOWN','records':None,'instruments':'UNKNOWN','times':[],'states':{},'exception':type(e).__name__}
def condition_for(r,conditions,overrides,date=None):
 date=date or r['start'][:10]
 for item in conditions.get('datasets',{}).get(r['dataset'],{}).get('conditions',[]):
  if item.get('date')==date:
   raw=item.get('condition','unknown').upper()
   status='AVAILABLE_VENDOR_METADATA' if raw=='AVAILABLE' else ('DEGRADED_VENDOR_METADATA_QUALITY_EXCEPTION' if raw=='DEGRADED' else f'VENDOR_METADATA_{raw}_QUALITY_EXCEPTION')
   return {'status':status,'note':f'vendor condition={item.get("condition")}; last_modified_date={item.get("last_modified_date","")}' }
 candidates=[x for x in overrides.get('overrides',[]) if x.get('date')==date and x.get('dataset',r['dataset'])==r['dataset']]
 return candidates[-1] if candidates else {'status':'UNKNOWN_NOT_CAPTURED_PRESERVE_AS_QUALITY_EXCEPTION','note':''}
def status_for(path,row,post,allowed):
 if not path.exists(): return {'status':'MISSING_UNKNOWN_NOT_ZERO','records':None,'instruments':'UNKNOWN','times':[],'states':{},'exception':''}
 if sha(path)!=row.get('sha256','') or str(path.stat().st_size)!=row.get('bytes',''): return {'status':'HASH_OR_BYTE_EXCEPTION_UNKNOWN','records':None,'instruments':'UNKNOWN','times':[],'states':{},'exception':''}
 if post: return {'status':'POST_SEALED_STRUCTURAL_ONLY','records':'NOT_INSPECTED','instruments':'NOT_INSPECTED','times':[],'states':{},'exception':''}
 state=pre_metrics(path,allowed)
 if row['analysis_access']!='DEVELOPMENT_PRE_FOCAL_ONLY' and state['status']=='PRE_STRUCTURAL_QA': state['status']='MIXED_FILE_PRE_SUBWINDOW_QA_POST_VALUES_UNINSPECTED'
 return state
def interval_ns(start,end):
 return ns(datetime.fromisoformat(start.replace('Z','+00:00'))),ns(datetime.fromisoformat(end.replace('Z','+00:00')))
def event_maps():
 maps=[]
 required={'event_id','symbol','leg','local_date','required_start_local','required_end_local','request_id'}
 for f,purpose,prefix in (('core32_event_request_map.csv','CORE32_EVENT_LEG','C32_'),('extra_event_request_map.csv','OPTIONAL_ETF_EVENT_LEG','EX_')):
  reader=csv.DictReader((ROOT/f).open(newline=''))
  if not required<=set(reader.fieldnames or []): raise RuntimeError(f'event map missing required headers: {f}')
  for r in reader:
   if not r['request_id'].startswith(prefix): raise RuntimeError(f'event map/request purpose mismatch: {f}/{r["request_id"]}')
   r['map_source']=f;r['map_purpose']=purpose;maps.append(r)
 return maps
def mbp_at_bbo_endpoints(mbp,bbo,lo,hi):
 """Last MBP-1 state at/before BBO interval-end; no pre-slice carry-in."""
 mt=sorted(t for t in mbp['states'] if lo<=t<hi); endpoints=sorted(t for t in bbo['states'] if lo<=t<hi)
 compared=matches=0;unavailable=0
 for end in endpoints:
  i=bisect.bisect_right(mt,end)-1
  if i<0: unavailable+=1;continue
  compared+=1;matches+=mbp['states'][mt[i]]==bbo['states'][end]
 return {'bbo_endpoints':len(endpoints),'compared_endpoints':compared,'matching_states':matches,'no_mbp_carry_in_or_update':unavailable}
def dry_test():
 maps=event_maps();assert len(maps)==448
 assert all(x['map_purpose'] in {'CORE32_EVENT_LEG','OPTIONAL_ETF_EVENT_LEG'} for x in maps)
 assert ns(datetime.fromisoformat('2019-07-26T19:40:00+00:00'))==1564170000000000000
 m={'states':{10:(1,),20:(2,)}};b={'states':{15:(1,),20:(2,),25:(2,)}}
 assert mbp_at_bbo_endpoints(m,b,10,30)=={'bbo_endpoints':3,'compared_endpoints':3,'matching_states':3,'no_mbp_carry_in_or_update':0}
 print(json.dumps({'dry_synthetic_test':'PASS','event_map_rows':len(maps)}))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--dataset-conditions',type=pathlib.Path,default=OUT/'DATASET_CONDITIONS.json');ap.add_argument('--condition-overrides',type=pathlib.Path,default=OUT/'DATASET_CONDITION_OVERRIDES.json');ap.add_argument('--dry-synthetic-test',action='store_true');a=ap.parse_args()
 if a.dry_synthetic_test: dry_test();return
 q=jread(OUT/'QUOTE_RECEIPT.json');s=jread(OUT/'SELECTION_RECEIPT.json');dm=list(csv.DictReader((OUT/'DOWNLOAD_MANIFEST.csv').open()))
 if s.get('quote_receipt_sha256')!=sha(OUT/'QUOTE_RECEIPT.json') or s.get('manifest_hashes')!=jread(ROOT/'manifest_hashes.json'): raise RuntimeError('frozen receipt/hash mismatch')
 if not str(s.get('status','')).startswith('FROZEN_QUOTED_BUNDLE_SELECTED'): raise RuntimeError('selection is not complete/frozen')
 selected=set(s['selected_canonical_ids']);quoted={x['canonical_id']:x for x in q['requests']};byid={x['canonical_id']:dict(x) for x in dm}
 if not selected or not selected<=set(quoted) or not selected<=set(byid) or any(quoted[x]['status']!='QUOTED' for x in selected): raise RuntimeError('selection/download manifest incomplete')
 conditions=jread(a.dataset_conditions) if a.dataset_conditions.exists() else {'datasets':{}}
 overrides=jread(a.condition_overrides) if a.condition_overrides.exists() else {'overrides':[]}
 maps=event_maps();event_access={x['event_id']:x['analysis_access'] for x in csv.DictReader((ROOT/'earnings_events.csv').open(newline=''))}
 request_rows={}
 for f in ('core32_requests.csv','extra_etf_requests.csv','validation_requests.csv'):
  for row in csv.DictReader((ROOT/f).open(newline='')): request_rows[row['request_id']]=row
 pre_windows=defaultdict(list)
 for m in maps:
  if event_access.get(m['event_id'])=='DEVELOPMENT_PRE_FOCAL_ONLY':
   base=request_rows[m['request_id']];pre_windows[cid(base)].append(interval_ns(utc_bound(m['local_date'],m['required_start_local']),utc_bound(m['local_date'],m['required_end_local'])))
 for base in (r for r in request_rows.values() if r['request_id'].startswith('V_')): pre_windows[cid(base)].append(interval_ns(base['start'],base['end']))
 final=[];qa={}
 for x in sorted(selected):
  r=byid[x];allowed=pre_windows.get(x,[]);state=status_for(pathlib.Path(r['path']),r,not bool(allowed),allowed);cond=condition_for(r,conditions,overrides)
  qa[x]=state;r.update(finalization_status=state['status'],qa_records=state['records'] if state['records'] is not None else 'UNKNOWN',qa_instrument_ids=state['instruments'],qa_first_clock=iso_ns(min(state['times'])) if state['times'] else '',qa_last_clock=iso_ns(max(state['times'])) if state['times'] else '',dataset_condition=cond['status'],dataset_condition_note=cond.get('note',''))
  final.append(r)
 cwrite(OUT/'DOWNLOAD_MANIFEST.csv',list(final[0]),final)
 cwrite(OUT/'SELECTED_ORDER.csv',['canonical_id','dataset','schema','symbols','stype_in','start','end','analysis_access','bundles','gross_usage_usd','selection_status'],[{**quoted[x],'selection_status':'FROZEN_SELECTED'} for x in sorted(selected)])
 # Link each original event leg to the physical selected interval, including
 # exact required bounds rather than treating a unioned file as unrestricted.
 request_rows={}
 for f in ('core32_requests.csv','extra_etf_requests.csv','validation_requests.csv'):
  for r in csv.DictReader((ROOT/f).open(newline='')): request_rows[r['request_id']]=r
 coverage=[]
 for m in event_maps():
  base=request_rows[m['request_id']];x=cid(base)
  if x not in selected: continue
  state=qa[x];start=utc_bound(m['local_date'],m['required_start_local']);end=utc_bound(m['local_date'],m['required_end_local']);lo,hi=interval_ns(start,end)
  post=event_access.get(m['event_id'])!='DEVELOPMENT_PRE_FOCAL_ONLY';inside=[t for t in state['times'] if lo<=t<hi]
  if post: cs='POST_SEALED_UNINSPECTED'
  elif state['records'] is None: cs='UNKNOWN_QA_EXCEPTION_NOT_ZERO'
  elif inside: cs='OBSERVED_PRE_COVERAGE'
  else: cs='NO_OBSERVED_RECORDS_UNKNOWN_WITHDRAWAL_OR_FEED_GAP'
  cond=condition_for(base,conditions,overrides,m['local_date'])
  coverage.append({'event_id':m['event_id'],'symbol':m['symbol'],'leg':m['leg'],'map_source':m['map_source'],'map_purpose':m['map_purpose'],'request_id':m['request_id'],'canonical_id':x,'dataset':base['dataset'],'schema':base['schema'],'requested_start_utc':start,'requested_end_utc':end,'observed_first_clock':iso_ns(min(inside)) if inside and not post else '','observed_last_clock':iso_ns(max(inside)) if inside and not post else '','record_count':len(inside) if not post and state['records'] is not None else ('NOT_INSPECTED' if post else 'UNKNOWN'),'coverage_status':cs,'withdrawal_or_gap_status':'UNKNOWN_NOT_ZERO' if cs!='OBSERVED_PRE_COVERAGE' else 'NOT_ASSESSED','dataset_condition':cond['status']})
 cwrite(OUT/'PILOT_COVERAGE.csv',list(coverage[0]) if coverage else ['event_id'],coverage)
 # Pair fixed XNAS bbo/mbp-1 endpoint states. ARCX is separate venue evidence.
 validation=list(csv.DictReader((ROOT/'validation_requests.csv').open(newline=''))); all_selected=[r for r in final if r['canonical_id'] in selected]
 overlap=[]
 for v in validation:
  x=cid(v)
  if x not in selected: continue
  candidates=[r for r in all_selected if r['symbols']==v['symbols'] and r['schema']=='bbo-1s' and r['dataset']=='XNAS.ITCH' and r['start']<=v['start'] and r['end']>=v['end']]
  if v['dataset']=='XNAS.ITCH' and v['schema']=='mbp-1': kind='XNAS_BBO1S_VS_MBP1';left=x;right=candidates[0]['canonical_id'] if candidates else None
  elif v['dataset']=='ARCX.PILLAR': kind='ARCX_VENUE_VS_XNAS_BBO1S';left=x;right=candidates[0]['canonical_id'] if candidates else None
  else: continue
  lo,hi=interval_ns(v['start'],v['end']); A=qa[left];B=qa[right] if right else None
  if B is None or A['records'] is None or B['records'] is None:
   endpoints=compared=matches=carry=0;rate='UNKNOWN';status='UNKNOWN_QA_EXCEPTION_OR_MISSING_PAIR'
  elif kind=='XNAS_BBO1S_VS_MBP1':
   # A is MBP-1, B is bbo-1s. BBO ts_recv is the clamped interval END;
   # MBP is carried forward only from receipts inside this slice.
   z=mbp_at_bbo_endpoints(A,B,lo,hi);endpoints=z['bbo_endpoints'];compared=z['compared_endpoints'];matches=z['matching_states'];carry=z['no_mbp_carry_in_or_update'];rate=str(Decimal(matches)/Decimal(compared)) if compared else 'UNKNOWN';status='AGGREGATE_MBP_CARRIED_TO_BBO_INTERVAL_END'
  else:
   # Different venues need not share endpoint states; report sensitivity coverage,
   # not an equality or quality verdict.
   endpoints=sum(1 for t in A['states'] if lo<=t<hi);compared=sum(1 for t in B['states'] if lo<=t<hi);matches='NOT_APPLICABLE';carry='NOT_APPLICABLE';rate='NOT_APPLICABLE';status='VENUE_SENSITIVITY_ONLY_NO_EXPECTED_EQUALITY'
  cond=condition_for(v,conditions,overrides)
  overlap.append({'validation_request_id':v['request_id'],'comparison_type':kind,'symbol':v['symbols'],'start':v['start'],'end':v['end'],'left_canonical_id':left,'right_canonical_id':right or 'MISSING','bbo_interval_endpoints':endpoints,'mbp_or_venue_endpoint_count':compared,'matching_endpoint_states':matches,'matching_rate':rate,'no_mbp_carry_in_or_update':carry,'status':status,'dataset_condition':cond['status']})
 cwrite(OUT/'SCHEMA_OVERLAP_CHECK.csv',list(overlap[0]) if overlap else ['validation_request_id'],overlap)
 conditions_hash=sha(a.dataset_conditions) if a.dataset_conditions.exists() else None
 reserved=Decimal(s['gross_quoted_usd']);jwrite(OUT/'COST_RECEIPT.json',{'status':'PURCHASE_COMPLETE_FILES_VERIFIED_BILLING_NOT_RECONCILED','quoted_gross_usage_usd':str(reserved),'reserved_gross_usage_usd':str(reserved),'actual_billed_credits_usd':'PENDING_VENDOR_BILLING_RECEIPT','cash_spent_usd':'0.00_UNDER_OWNER_CREDIT_AUTHORIZATION_UNLESS_VENDOR_RECEIPT_SHOWS_OTHERWISE','planning_cap_usd':s['planning_cap_usd'],'hard_ceiling_usd':s['hard_ceiling_usd'],'manifest_hashes':s['manifest_hashes'],'selection_receipt_sha256':sha(OUT/'SELECTION_RECEIPT.json'),'dataset_conditions_source':str(a.dataset_conditions),'dataset_conditions_sha256':conditions_hash,'post_focal_values_inspected':False})
 def counts(rows,key):
  out=defaultdict(int)
  for row in rows: out[row[key]]+=1
  return ', '.join(f'{k}: {v}' for k,v in sorted(out.items())) or 'none'
 core_map=[x for x in event_maps() if x['map_source']=='core32_event_request_map.csv']
 pre_ids={x['event_id'] for x in csv.DictReader((ROOT/'earnings_events.csv').open(newline='')) if x['analysis_access']=='DEVELOPMENT_PRE_FOCAL_ONLY'}
 cov_by_event=defaultdict(list)
 for row in coverage:
  if row['map_source']=='core32_event_request_map.csv': cov_by_event[row['event_id']].append(row)
 usable=[]
 for event in sorted(pre_ids):
  required=[x for x in core_map if x['event_id']==event]
  observed=cov_by_event.get(event,[])
  if required and len(observed)==len(required) and all(x['coverage_status']=='OBSERVED_PRE_COVERAGE' for x in observed): usable.append(event)
 pre_statuses={'PRE_STRUCTURAL_QA','MIXED_FILE_PRE_SUBWINDOW_QA_POST_VALUES_UNINSPECTED'}
 done_statuses=pre_statuses|{'POST_SEALED_STRUCTURAL_ONLY'}
 downloaded=sum(x['finalization_status'] in done_statuses for x in final);pre_decoded=sum(x['finalization_status'] in pre_statuses for x in final);post_sealed=sum(x['finalization_status']=='POST_SEALED_STRUCTURAL_ONLY' for x in final)
 exceptions=[x['canonical_id'] for x in final if x['finalization_status'] not in done_statuses]
 degraded_files=[x['canonical_id'] for x in final if x['dataset_condition']=='DEGRADED_VENDOR_METADATA_QUALITY_EXCEPTION']
 degraded_legs=[x['event_id']+'/'+x['leg'] for x in coverage if x['dataset_condition']=='DEGRADED_VENDOR_METADATA_QUALITY_EXCEPTION']
 vendor_conditions=[x for ds in conditions.get('datasets',{}).values() for x in ds.get('conditions',[])]
 vendor_available=sum(x.get('condition')=='available' for x in vendor_conditions);vendor_degraded=sum(x.get('condition')=='degraded' for x in vendor_conditions)
 text='# P1 fixed-pilot delivery\n\n'
 text+=f'Frozen selection: {len(selected)} files; structurally completed: {downloaded}; PRE decoded for authorized QA: {pre_decoded}; POST sealed without value inspection: {post_sealed}. POST values inspected: no. Quoted/reserved gross usage: ${reserved}. Cash spend: $0 under owner credit authorization unless vendor receipt shows otherwise. Actual billed credits: pending vendor billing receipt. Vendor condition provenance: {a.dataset_conditions.name} SHA-256 {conditions_hash}; requested dataset-dates: {vendor_available} available, {vendor_degraded} degraded.\n\n'
 text+='Event-leg coverage statuses: '+counts(coverage,'coverage_status')+'.\n\n'
 text+='Schema/venue overlap results: '+counts(overlap,'status')+'.\n\n'
 exception_names=', '.join(exceptions[:20])
 if len(exceptions)>20: exception_names+=f'; plus {len(exceptions)-20} more in DOWNLOAD_MANIFEST.csv'
 condition_note=f' Explicit degraded/condition exceptions: {len(degraded_files)} files, {len(degraded_legs)} event legs.'
 text+=f'Exceptions ({len(exceptions)}): '+(exception_names if exceptions else 'none')+'.'+condition_note+' Degraded/missing conditions remain quality exceptions, never zero coverage.\n\n'
 text+=f'Eligible named PRE events for the next permitted calibration only when every required stock+SPY core leg is observed: {len(usable)}. '+('; '.join(usable) if usable else 'None')+'. This is a coverage rule, not causal/treatment analysis.\n'
 (OUT/'PILOT_DELIVERY.md').write_text(text)
 print(json.dumps({'selected_requests':len(selected),'event_leg_rows':len(coverage),'overlap_rows':len(overlap),'post_focal_values_inspected':False}))
if __name__=='__main__': main()
