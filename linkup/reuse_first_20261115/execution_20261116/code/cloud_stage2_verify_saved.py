"""Verify stored PRIMARYs against SHA-pinned prepared inputs, preserving original states."""
import json,hashlib,sqlite3,os,sys,datetime,time,collections,concurrent.futures,urllib.parse,importlib.util,fcntl
from pathlib import Path
R=Path.home()/'migration';B=R/'integration_20261116/run001';O=R/'execution_20261116/run001/stage2';D=O/'revision002';os.umask(0o077)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 lock=(O/'STAGE2.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);D.mkdir(exist_ok=False);cache=D/'cache';cache.mkdir();checks=D/'validation';checks.mkdir();t0=time.monotonic()
 original=O/'REUSED_VALUES_PRIVATE.sqlite';oldsha=sha(original);db=sqlite3.connect(D/'REUSED_VALUES_PRIVATE.sqlite');old=sqlite3.connect(original.as_uri()+'?mode=ro',uri=True);old.backup(db);old.close()
 index=sqlite3.connect((B/'revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);blocked={x[0] for x in index.execute('select h from blocked')};states=dict(index.execute('select h,state from final_status'))
 plan=read(O/'REMAINING_SOURCE_LOCATORS_PRIVATE.json');mapping=plan['mapping'];by_packet=collections.defaultdict(list)
 for h,m in mapping.items():by_packet[(m['batch'],m['packet'])].append(h)
 jobs=[];skips=collections.Counter()
 for m in plan['primary_files']:
  pair=(m['batch'],m['packet']);hs=by_packet[pair]
  if any(h in blocked for h in hs):skips['whole_packet_protection']+=1;continue
  mh=mapping[hs[0]]['manifest_sha256'];inp=plan['input_packet_sha_by_manifest'].get(mh,{}).get(m['packet']);jobs.append({'primary':m,'input_sha256':inp,'contexts':hs})
 need={x['input_sha256'] for x in jobs if x['input_sha256']};found={m['sha256']:m for m in plan['primary_files']};configs={}
 for cluster in ['kunshan','wuzhen','huazhong']:
  c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);ls=list(need)
  for start in range(0,len(ls),800):
   ds=ls[start:start+800]
   for path,root,rel,size,status,h in c.execute('select path,root,rel,size,status,sha from files where sha in ('+','.join('?' for _ in ds)+')',ds):
    if status=='verified' and 'batch035' not in path.lower():found.setdefault(h,{'cluster':cluster,'path':path,'root':root,'rel':rel,'size':size,'status':status,'sha256':h})
  c.close();configs[cluster]=read(R/'private'/(cluster+'.json'))
 wanted={x['primary']['sha256'] for x in jobs}|{x['input_sha256'] for x in jobs if x['input_sha256'] in found};assert sum(found[d]['size'] for d in wanted)<256*1024*1024
 sys.path.insert(0,str(R/'code'));from workflow import call
 def fetch(d):
  m=found[d];p=cache/(d+'.data')
  try:
   c=configs[m['cluster']];url=c['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(c['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
   with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:b=response.read(m['size']+1)
   assert len(b)==m['size'] and hashlib.sha256(b).hexdigest()==d
   p.write_bytes(b);return d,None
  except Exception as e:return d,{'type':type(e).__name__,'http_status':getattr(e,'code',None)}
 available=set();errs=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for d,e in pool.map(fetch,sorted(wanted)):
   if e:errs.append({'sha256':d,**e})
   else:available.add(d)
 frozen=R/'code/validate_reviews.py';assert sha(frozen)=='f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20';schema=R/'astra/extraction/FORMAL800_REVIEW_SCHEMA.json';assert sha(schema)=='fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e'
 sp=importlib.util.spec_from_file_location('frozen_validator',frozen);v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
 counts=collections.Counter();passes=set();outcomes=[]
 def add(row,asset,source,n,accepted=False):
  h=row['context_sha256'];assert h not in blocked and h in states
  payload=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'));digest=hashlib.sha256((asset+'\0'+source+'\0'+str(n)+'\0'+payload).encode()).hexdigest();db.execute('INSERT OR IGNORE INTO document VALUES(?,?,?,?,?,?,?,?)',(digest,h,'',asset,source,n,int(accepted),payload))
  vals={'document_status':row.get('document_status'),'technology':{'inventory_status':row.get('technology_inventory_status'),'items':row.get('technology_items',[])},'experience':{'outcomes':row.get('experience_outcomes'),'items':row.get('experience_clauses',[])},'entry':{'outcomes':row.get('entry_outcomes'),'items':row.get('entry_items',[])},'responsibility':{'outcomes':row.get('responsibility_outcomes'),'items':row.get('responsibility_items',[])},'qualification_alternatives':row.get('qualification_alternatives',[]),'evidence_resolution':row.get('evidence_resolution',[]),'unresolved_notes':row.get('unresolved_notes',[])}
  for fam,val in vals.items():db.execute('INSERT OR IGNORE INTO field_value VALUES(?,?,?,?)',(digest,fam,'original_scope' if accepted else 'saved_unverified',json.dumps(val,ensure_ascii=False,separators=(',',':'))))
 for i,job in enumerate(jobs):
  pd=job['primary']['sha256'];inp=job['input_sha256'];status='input_or_primary_missing'
  if pd in available and inp in available:
   sub=checks/f'{i:04d}';sub.mkdir();sys.argv=['validate_reviews.py','--packet',str(cache/(inp+'.data')),'--reviews',str(cache/(pd+'.data')),'--schema',str(schema),'--expected-records',str(len(job['contexts'])),'--private-validated',str(sub/'VALIDATED_PRIVATE.jsonl'),'--private-errors',str(sub/'ERRORS_PRIVATE.jsonl'),'--public-receipt',str(sub/'RECEIPT_PUBLIC.json')]
   try:v.main();status='frozen_mechanical_pass_still_saved_unverified'
   except SystemExit:status='frozen_validation_failed_preserved'
   except Exception as e:status='validator_exception_'+type(e).__name__
   if (sub/'RECEIPT_PUBLIC.json').exists():
    rr=read(sub/'RECEIPT_PUBLIC.json');counts['submitted_primary_rows']+=rr['counts']['submitted_review_rows'];counts['validated_rows_including_partial_packets']+=rr['counts']['validated_records']
    if rr['status']=='pass':passes.update(job['contexts'])
  counts[status]+=1;outcomes.append({'primary_sha256':pd,'input_sha256':inp,'status':status,'contexts':job['contexts']})
  if pd in available:
   try:
    for n,line in enumerate((cache/(pd+'.data')).open(),1):
     row=json.loads(line)
     if row.get('context_sha256') not in job['contexts']:db.execute('INSERT INTO issue VALUES(?,?,?,?)',('primary_binding_mismatch','',pd,''));continue
     add(row,'Pro_PRIMARY_saved_unverified',pd,n)
   except Exception as e:db.execute('INSERT INTO issue VALUES(?,?,?,?)',('primary_parse_failure','',pd,type(e).__name__))
  if i%50==0:(D/'PROGRESS_PUBLIC.json').write_text(json.dumps({'packets_completed':i+1,'packets_total':len(jobs),'new_model_calls':0}))
 # Correct Astra run locator from existing execution code; no new inference.
 st=read(R/'astra/extraction/STATE_PRIVATE.json');ac=0
 for task,x in st['accepted'].items():
  p=R/'astra/extraction'/x['run']/'VALIDATED_PRIVATE.jsonl'
  if p.exists() and sha(p)==x['sha256']:
   for n,l in enumerate(p.open(),1):
    row=json.loads(l);assert row['context_sha256']==x['context_sha256'];add(row,'Astra_original_accepted',x['sha256'],n,True);ac+=1
   db.execute('INSERT OR IGNORE INTO source VALUES(?,?,?)',(x['sha256'],str(p),p.stat().st_size))
 for d in available:db.execute('INSERT OR IGNORE INTO source VALUES(?,?,?)',(d,str(cache/(d+'.data')),found[d]['size']))
 db.execute("DELETE FROM issue WHERE kind='no_value_carrier_attached_yet' AND h IN (SELECT h FROM document)")
 (D/'PRIMARY_VALIDATION_PRIVATE.json').write_text(json.dumps(outcomes,indent=2)+'\n')
 assert sha(original)==oldsha;assert db.execute('pragma integrity_check').fetchone()[0]=='ok';assert not db.execute('select 1 from document where h in (select h from protected)').fetchone()
 result={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'stored_primary_revalidation_complete_original_states_preserved','packets':len(jobs),'skipped':dict(skips),'files_downloaded_sha_verified':len(available),'bytes_downloaded':sum(found[d]['size'] for d in available),'download_errors':errs,'validation_counts':dict(counts),'contexts_in_fully_passing_saved_Pro_packets':len(passes),'Astra_original_accepted_attached':ac,'accepted_original_contexts_with_values':db.execute('select count(distinct h) from document where original_accepted=1').fetchone()[0],'saved_contexts_with_any_attached_document':db.execute('select count(distinct h) from document where original_accepted=0').fetchone()[0],'value_documents_by_asset':dict(db.execute('select asset,count(*) from document group by asset')),'unattached_contexts_by_original_state':dict(db.execute("select detail,count(*) from issue where kind='no_value_carrier_attached_yet' group by detail")),'new_model_calls':0,'new_production_accepted':0,'original_database_unchanged':True,'no_protected_payloads_attached':True,'duration_seconds':time.monotonic()-t0}
 db.commit();db.close();index.close();result['database_sha256']=sha(D/'REUSED_VALUES_PRIVATE.sqlite');(D/'SAVED_OUTPUT_VERIFICATION_PUBLIC.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception as e:
  import traceback
  (O/'REVISION002_FAILURE_PRIVATE.txt').write_text(traceback.format_exc());print(json.dumps({'status':'stage2_revision002_failed_preserved','exception_type':type(e).__name__}));raise SystemExit(2)
