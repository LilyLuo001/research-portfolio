#!/usr/bin/env python3
"""Strict P1 executor: prepare offline; quote only metadata/symbology/cost; guarded DBN download."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,pathlib,sys
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from decimal import Decimal,InvalidOperation
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'delivery'; UTC=timezone.utc; NY=ZoneInfo('America/New_York')
FILES=('core32_requests.csv','core16_budget_reduction_requests.csv','validation_requests.csv','extra_etf_requests.csv')
BUNDLE={'core32_requests.csv':'core32','core16_budget_reduction_requests.csv':'core16'}
def digest(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def canon(r): return tuple(r[x] for x in ('dataset','schema','symbols','stype_in','start','end'))
def cid(r): return hashlib.sha256('\x1f'.join(canon(r)).encode()).hexdigest()
def money(x):
 try: d=Decimal(str(x))
 except (InvalidOperation,ValueError,TypeError): return None
 return d if d.is_finite() and d>=0 else None
def jwrite(p,v): pathlib.Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def jread(p): return json.loads(pathlib.Path(p).read_text())
def cwrite(p,fields,rows):
 with pathlib.Path(p).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def load():
 h=jread(ROOT/'manifest_hashes.json'); bad={n:(v,digest(ROOT/n) if (ROOT/n).exists() else None) for n,v in h.items() if not (ROOT/n).exists() or digest(ROOT/n)!=v}
 if bad: raise RuntimeError('immutable manifest mismatch')
 rows={f:list(csv.DictReader((ROOT/f).open(newline=''))) for f in FILES}; unique={}; memberships=defaultdict(set)
 for f,rr in rows.items():
  seen=set()
  for r in rr:
   k=canon(r)
   if k in seen: raise RuntimeError(f'duplicate request in {f}: {r["request_id"]}')
   seen.add(k); unique.setdefault(k,{**r,'canonical_id':cid(r)})
   memberships[k].add(BUNDLE.get(f) or ('validation_mbp1' if r['bundle']=='QUOTE_UPDATE_VALIDATION' else 'validation_arcx' if r['bundle']=='SECOND_VENUE_VALIDATION' else 'extra_etfs'))
   a=datetime.fromisoformat(r['start'].replace('Z','+00:00'));b=datetime.fromisoformat(r['end'].replace('Z','+00:00'))
   if not(a.tzinfo==UTC and b.tzinfo==UTC and a<b and a.astimezone(NY).date().isoformat()==r['local_date'] and b.astimezone(NY).date().isoformat()==r['local_date'] and a.astimezone(NY).strftime('%H:%M')==r['local_start'] and b.astimezone(NY).strftime('%H:%M')==r['local_end']): raise RuntimeError(f'UTC/New_York invariant failed: {r["request_id"]}')
 return rows,unique,memberships,h
def blocked(rows,h,why):
 OUT.mkdir(exist_ok=True);(OUT/'sealed_post_focal').mkdir(exist_ok=True)
 order=[{**r,'original_manifest':f,'selection_status':'NOT_SELECTED_BLOCKED','blocker':why} for f,rr in rows.items() for r in rr];cwrite(OUT/'SELECTED_ORDER.csv',list(order[0]),order)
 jwrite(OUT/'COST_RECEIPT.json',{'status':'BLOCKED_NO_LIVE_EXECUTION','blocker':why,'quoted_gross_usage_usd':None,'actually_consumed_credits_usd':'0.00','cash_spent_usd':'0.00','planning_cap_usd':'100.00','hard_cap_usd':'125.00','reserve_usd':'25.00','manifest_hashes':h,'actual_routing_telemetry':'NOT_OBSERVED'})
 fields=['request_id','dataset','schema','symbols','stype_in','start','end','analysis_access','job_request_id','path','bytes','records','completion_status','sha256','note']; cwrite(OUT/'DOWNLOAD_MANIFEST.csv',fields,[{**r,'completion_status':'NOT_ATTEMPTED_BLOCKED','note':why} for rr in rows.values() for r in rr])
def client():
 try: import databento as db
 except ImportError as e: raise RuntimeError('Databento SDK unavailable; no API call made') from e
 return db.Historical(os.environ['DATABENTO_API_KEY'])
def symbology_complete(response, symbol):
 """Reject explicit partial/not-found resolution responses before costing."""
 if not isinstance(response,dict): raise RuntimeError('invalid_symbology_response')
 if response.get('partial') or response.get('not_found'): raise RuntimeError('symbology_partial_or_not_found')
 result=response.get('result')
 if not isinstance(result,dict) or symbol not in result or not result[symbol]: raise RuntimeError('symbology_not_found')
def symbology_dates(r):
 start_day=datetime.fromisoformat(r['start'].replace('Z','+00:00')).date(); end_day=datetime.fromisoformat(r['end'].replace('Z','+00:00')).date()
 return start_day.isoformat(),max(end_day,start_day+timedelta(days=1)).isoformat()
def quote(unique,members,h,balance):
 c=client(); avail={}
 for ds in sorted({r['dataset'] for r in unique.values()}):
  try: avail[ds]={'status':'AVAILABLE','dataset_range':c.metadata.get_dataset_range(ds),'schemas':c.metadata.list_schemas(ds)}
  except Exception as e: avail[ds]={'status':'UNAVAILABLE','error_type':type(e).__name__,'dataset_range':None,'schemas':None}
 cached={}
 old=OUT/'QUOTE_RECEIPT.json'
 if old.exists():
  prior=jread(old)
  if prior.get('manifest_hashes')==h:
   cached={e.get('canonical_id'):e for e in prior.get('requests',[]) if e.get('status')=='QUOTED' and money(e.get('gross_usage_usd')) is not None}
 entries=[]
 for r in unique.values():
  e={k:r[k] for k in ('canonical_id','dataset','schema','symbols','stype_in','start','end','analysis_access')};e['bundles']=sorted(members[canon(r)])
  if e['canonical_id'] in cached:
   e.update(status='QUOTED',gross_usage_usd=str(money(cached[e['canonical_id']]['gross_usage_usd'])),quote_cache='REUSED_SUCCESSFUL_EXACT_CANONICAL')
   entries.append(e);continue
  try:
   if avail[r['dataset']]['status']!='AVAILABLE' or r['schema'] not in avail[r['dataset']]['schemas']: raise RuntimeError('range_or_schema_unavailable')
   resolve_start,resolve_end=symbology_dates(r)
   resolved=c.symbology.resolve(dataset=r['dataset'],symbols=[r['symbols']],stype_in=r['stype_in'],stype_out='instrument_id',start_date=resolve_start,end_date=resolve_end)
   symbology_complete(resolved,r['symbols'])
   x=money(c.metadata.get_cost(dataset=r['dataset'],start=r['start'],end=r['end'],symbols=[r['symbols']],schema=r['schema'],stype_in=r['stype_in']))
   if x is None: raise RuntimeError('invalid_quote')
   e.update(status='QUOTED',gross_usage_usd=str(x))
  except Exception as ex: e.update(status='UNAVAILABLE_OR_UNQUOTED',gross_usage_usd=None,error_type=type(ex).__name__)
  entries.append(e)
 costs={}
 for b in ('core32','core16','validation_mbp1','validation_arcx','extra_etfs'):
  es=[e for e in entries if b in e['bundles']];costs[b]=str(sum((Decimal(e['gross_usage_usd']) for e in es),Decimal('0'))) if es and all(e['status']=='QUOTED' for e in es) else None
 receipt={'receipt_version':1,'api_scope':'metadata.get_dataset_range,metadata.list_schemas,symbology.resolve,metadata.get_cost','manifest_hashes':h,'canonical_request_count':len(entries),'dataset_checks':avail,'requests':entries,'cost_usd_by_bundle':costs,'bundle_complete':{b:costs[b] is not None for b in costs}}
 jwrite(OUT/'QUOTE_RECEIPT.json',receipt);qh=digest(OUT/'QUOTE_RECEIPT.json');gate={'remaining_credits_usd':None,'cost_usd_by_bundle':costs,'quote_receipt_sha256':qh,'manifest_hashes':h}
 if balance:
  b=jread(balance);m=money(b.get('remaining_credits_usd'))
  if m is None or not isinstance(b.get('source'),str) or not b['source']: raise RuntimeError('balance requires nonnegative remaining_credits_usd and source')
  gate.update(remaining_credits_usd=str(m),balance_source=b['source'],balance_expiry=b.get('expiry'))
 jwrite(OUT/'BUDGET_GATE_INPUT.json',gate)
 if balance:
  sys.path.insert(0,str(ROOT));from budget_gate import select
  d=select(gate);chosen=[e for e in entries if set(e['bundles'])&set(d.get('selected',[]))]; d.update(status='FROZEN_'+d['status'],quote_receipt_sha256=qh,manifest_hashes=h,selected_canonical_ids=[e['canonical_id'] for e in chosen],selected_request_hash=hashlib.sha256('\n'.join(sorted(e['canonical_id'] for e in chosen)).encode()).hexdigest(),balance_source=gate['balance_source']);jwrite(OUT/'SELECTION_RECEIPT.json',d)
 print(json.dumps({'status':'QUOTES_RECORDED_NO_DOWNLOAD','unique_canonical_requests':len(entries),'quote_receipt_sha256':qh}))
def download(unique,h,balance,selection,approved):
 if not approved or not balance or not selection: raise RuntimeError('download requires owner flag, balance JSON, and frozen selection receipt; no history call made')
 b=jread(balance);rem=money(b.get('remaining_credits_usd'));s=jread(selection);qp=OUT/'QUOTE_RECEIPT.json'
 if rem is None or not b.get('source') or not qp.exists() or s.get('quote_receipt_sha256')!=digest(qp) or s.get('manifest_hashes')!=h: raise RuntimeError('untrusted balance/quote/selection; no history call made')
 total,cap,hard=map(money,(s.get('gross_quoted_usd'),s.get('planning_cap_usd'),s.get('hard_ceiling_usd')))
 if not(str(s.get('status','')).startswith('FROZEN_QUOTED_BUNDLE_SELECTED') and total is not None and cap is not None and hard is not None and total<=cap<=Decimal('100') and total<=hard<=Decimal('125') and total<=rem): raise RuntimeError('budget caps failed; no history call made')
 qs={e['canonical_id']:e for e in jread(qp)['requests']};ids=s.get('selected_canonical_ids',[])
 if not ids or any(i not in qs or qs[i]['status']!='QUOTED' for i in ids): raise RuntimeError('incomplete selected quotes; no history call made')
 c=client();reserved=Decimal('0');manifest=[];byid={r['canonical_id']:r for r in unique.values()}
 for i in ids:
  q=qs[i];reserved+=Decimal(q['gross_usage_usd'])
  if reserved>total or reserved>Decimal('100') or reserved>Decimal('125') or reserved>rem: raise RuntimeError('reservation cap breach before submission')
  r=byid[i];folder=OUT/('native_pre_focal' if r['analysis_access']=='DEVELOPMENT_PRE_FOCAL_ONLY' else 'sealed_post_focal');folder.mkdir(exist_ok=True);path=folder/f'{i}.dbn.zst'
  row={**q,'job_request_id':'DIRECT_TIMESERIES_GET_RANGE','path':str(path),'bytes':'','records':'NOT_INSPECTED','completion_status':'SUBMISSION_STARTED_NO_RETRY','sha256':'','reserved_gross_usage_usd':str(reserved)};manifest.append(row);cwrite(OUT/'DOWNLOAD_MANIFEST.csv',list(row),manifest)
  try: c.timeseries.get_range(dataset=r['dataset'],start=r['start'],end=r['end'],symbols=[r['symbols']],schema=r['schema'],stype_in=r['stype_in'],stype_out='instrument_id',path=path);row.update(completion_status='DOWNLOADED_NATIVE_DBN_UNINSPECTED',bytes=str(path.stat().st_size),sha256=digest(path))
  except Exception as e: row.update(completion_status='UNCERTAIN_OR_PARTIAL_NO_RETRY',error_type=type(e).__name__);cwrite(OUT/'DOWNLOAD_MANIFEST.csv',list(row),manifest);raise RuntimeError('uncertain/partial download; stopped without retry')
  cwrite(OUT/'DOWNLOAD_MANIFEST.csv',list(row),manifest)
 jwrite(OUT/'COST_RECEIPT.json',{'status':'DOWNLOADS_COMPLETED_PENDING_BILLING_RECONCILIATION','selected_order_sha256':s['selected_request_hash'],'reserved_gross_usage_usd':str(reserved),'actual_consumed_credits_usd':'RECONCILE_WITH_VENDOR','manifest_hashes':h})
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','quote','download'),nargs='?',default='prepare');p.add_argument('--balance-json',type=pathlib.Path);p.add_argument('--selection-receipt',type=pathlib.Path);p.add_argument('--owner-approved-download',action='store_true');a=p.parse_args();rows,u,m,h=load();key=bool(os.environ.get('DATABENTO_API_KEY'))
 if a.mode=='prepare' or not key: blocked(rows,h,'DATABENTO_API_KEY_ABSENT' if not key else 'PREPARE_ONLY');print(json.dumps({'mode':a.mode,'status':'BLOCKED','api_calls':0}));return
 if a.mode=='quote':quote(u,m,h,a.balance_json)
 else:download(u,h,a.balance_json,a.selection_receipt,a.owner_approved_download)
if __name__=='__main__':main()
