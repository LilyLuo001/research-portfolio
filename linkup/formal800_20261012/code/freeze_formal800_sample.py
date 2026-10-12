#!/usr/bin/env python3
"""Freeze the authorized ad-level Formal800 sample on a scheduled SCNet node.

This program never changes the fixed10k frame.  It excludes whole exact-text
groups that were exposed in prior review/development/evaluation, computes the
already-frozen rulefirst-v1.2 entry candidate flag, samples ADS (not contexts),
and only then groups selected identical contexts for review reuse.
"""
import argparse, collections, datetime as dt, hashlib, importlib, json, math, os, platform, sys
from pathlib import Path
import pyarrow.parquet as pq

KEY=("JOB_HASH","SOURCE_FILE","SOURCE_ROW","RECORD_SOURCE_ROW")
ARMS=("A","B","C"); QUOTA={"A":320,"B":320,"C":160}; SEED="formal800-20261012-ad-freeze-v1"

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def dump(path, value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+".tmp")
 with open(t,"w",encoding="utf-8") as f:
  if isinstance(value,list):
   for x in value:f.write(json.dumps(x,sort_keys=True,ensure_ascii=False)+"\n")
  else:json.dump(value,f,indent=2,sort_keys=True);f.write("\n")
 os.replace(t,p)
def canonical(row): return json.dumps([row[x] for x in KEY],separators=(",",":"))
def rank(row,purpose): return hashlib.sha256((SEED+"|"+purpose+"|"+canonical(row)).encode()).hexdigest()
def context_id(h): return "ctx-"+hashlib.sha256((SEED+"|context|"+h).encode()).hexdigest()[:20]
def load_exclusions(paths):
 raw=set(); norm=set(); audit=[]
 def gather(v):
  r=[];n=[]
  if isinstance(v,dict):
   if v.get("hash_scope") in ("raw_exact","normalized") and isinstance(v.get("sha256"),str) and len(v["sha256"])==64:
    (r if v["hash_scope"]=="raw_exact" else n).append(v["sha256"])
   for k,x in v.items():
    if k in ("exact_text_sha256","source_exact_text_sha256","source_text_sha256","raw_output_source_text_sha256","source_sha256","text_sha256") and isinstance(x,str) and len(x)==64:r.append(x)
    elif k in ("context_sha256","normalized_text_sha256") and isinstance(x,str) and len(x)==64:n.append(x)
    elif k in ("original_text","source_text","full_document") and isinstance(x,str):r.append(hashlib.sha256(x.encode()).hexdigest())
    a,b=gather(x);r+=a;n+=b
  elif isinstance(v,list):
   for x in v:
    a,b=gather(x);r+=a;n+=b
  return r,n
 for fn in paths:
  rows=0; r=0; n=0
  with open(fn,encoding="utf-8") as f:
   for line in f:
    if not line.strip():continue
    x=json.loads(line); rows+=1
    aa,bb=gather(x);raw.update(aa);norm.update(bb);r+=len(aa);n+=len(bb)
  if not (r or n): raise RuntimeError("exclusion manifest has no exact-context hash: "+fn)
  audit.append({"path":fn,"sha256":sha(fn),"rows":rows,"raw_hash_rows":r,"normalized_hash_rows":n})
 return raw,norm,audit
def allocate(available):
 # Balanced candidate/no-hit allocation.  A shortage is first taken in full;
 # the predeclared remainder transfers only to the other stratum in its arm.
 out={}; notes=[]
 for arm in ARMS:
  target=QUOTA[arm]; base={"candidate":target//2,"nohit":target-target//2}
  if sum(available[(arm,s)] for s in base)<target: raise RuntimeError("eligible arm below frozen quota: "+arm)
  take={s:min(base[s],available[(arm,s)]) for s in base}; rem=target-sum(take.values())
  if rem:
   other=sorted(base,key=lambda s:(available[(arm,s)]-take[s],s),reverse=True)[0]
   if available[(arm,other)]-take[other]<rem: raise RuntimeError("same-arm redistribution impossible: "+arm)
   take[other]+=rem;notes.append({"arm":arm,"rule":"short stratum taken in full; remainder to other same-arm stratum","targets":base,"selected":take})
  out.update({(arm,s):take[s] for s in base})
 return out,notes
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--frame",required=True);p.add_argument("--exclusion",action="append",required=True)
 p.add_argument("--frozen-rule-dir",required=True);p.add_argument("--private-output",required=True);p.add_argument("--public-receipt",required=True)
 p.add_argument("--arm-map-json",required=True,help="JSON mapping fixed10k arm values to A/B/C")
 a=p.parse_args(); os.umask(0o077); armmap=json.loads(a.arm_map_json)
 if set(armmap.values())!=set(ARMS):raise RuntimeError("arm map must cover A/B/C exactly")
 sys.path.insert(0,a.frozen_rule_dir); rule=importlib.import_module("rule_engine")
 raw_ex,norm_ex,ex_audit=load_exclusions(a.exclusion)
 needed=set(KEY)|{"arm","exact_text_sha256","original_text","total_inclusion_probability","nested_design_weight"}
 pf=pq.ParquetFile(a.frame)
 if not needed<=set(pf.schema_arrow.names):raise RuntimeError("frame lacks required fixed10k fields: "+repr(sorted(needed-set(pf.schema_arrow.names))))
 prepared=[]; rows=[]; excluded=collections.Counter(); excluded_weight=0.0; excluded_missing_weight=0; upstream_status=collections.Counter(); excluded_contexts=set(); excluded_by_arm=collections.Counter(); seen_keys=set()
 for batch in pf.iter_batches(batch_size=4096):
  for row in batch.to_pylist():
   source=row["exact_text_sha256"]; result=rule.extract(row["original_text"])
   ck=canonical(row)
   if ck in seen_keys:raise RuntimeError("fixed10k repeats canonical ad key")
   seen_keys.add(ck)
   probability_status="verified"
   for prob,weight in ((row.get("inclusion_probability"),row.get("design_weight")),(row["total_inclusion_probability"],row["nested_design_weight"])):
    if prob is None or weight is None:
     probability_status="missing";break
    if not math.isfinite(float(prob)) or not (0<float(prob)<=1) or not math.isfinite(float(weight)) or float(weight)<=0 or not math.isclose(float(prob)*float(weight),1.0,rel_tol=1e-8,abs_tol=1e-10):
     probability_status="invalid";break
   upstream_status[probability_status]+=1
   row["upstream_probability_status"]=probability_status
   if result.get("source_text_sha256")!=source:raise RuntimeError("source hash mismatch for fixed cache row")
   norm=result.get("normalized_text_sha256"); normalized=result.get("normalized_text")
   if not isinstance(normalized,str) or hashlib.sha256(normalized.encode()).hexdigest()!=norm: raise RuntimeError("frozen normalized context hash mismatch")
   if row["arm"] not in armmap: raise RuntimeError("unmapped fixed10k arm: "+repr(row["arm"]))
   arm=armmap[row["arm"]]
   flags=result.get("flags",{}); entry=bool(flags.get("graduate_language") or flags.get("explicit_no_experience"))
   prepared.append(dict(row,formal_arm=arm,entry_stratum="candidate" if entry else "nohit",raw_exact_text_sha256=source,context_sha256=norm,normalized_full_document=normalized,normalization_flags=result.get("normalization_flags",{})))
 # Closure: any raw-hash exposure excludes every fixed10k row with its same
 # frozen normalized context, including byte variants not named by history.
 norm_ex.update(r["context_sha256"] for r in prepared if r["raw_exact_text_sha256"] in raw_ex)
 for r in prepared:
  if r["raw_exact_text_sha256"] in raw_ex or r["context_sha256"] in norm_ex:
   excluded["prior_exposed_exact_context"]+=1
   if r["upstream_probability_status"]=="verified":excluded_weight+=float(r["nested_design_weight"])
   else:excluded_missing_weight+=1
   excluded_contexts.add((r["raw_exact_text_sha256"],r["context_sha256"]));excluded_by_arm[str(r["arm"])+"|prior_exposed_exact_context"]+=1
  else: rows.append(r)
 if len(rows)+sum(excluded.values())!=pf.metadata.num_rows:raise RuntimeError("frame conservation failure")
 groups=collections.Counter((r["formal_arm"],r["entry_stratum"]) for r in rows); take,redistribution=allocate(groups)
 selected=[]
 for key,n in sorted(take.items()):
  pool=[r for r in rows if (r["formal_arm"],r["entry_stratum"])==key]
  selected.extend(sorted(pool,key=lambda r:rank(r,"primary|"+key[0]+"|"+key[1]))[:n])
 if len(selected)!=800 or len({canonical(r) for r in selected})!=800:raise RuntimeError("ad freeze cardinality failure")
 # Fixed 20% audit ADS, stratified by realized sampling stratum; ties resolve
 # by stable ad-key rank, independent from the primary rank.
 audit_n={k:int(.2*n) for k,n in take.items()}; rem=160-sum(audit_n.values())
 for k in sorted((k for k in take if audit_n[k]<take[k]),key=lambda x:(-(.2*take[x]-int(.2*take[x])),rank({z:"" for z in KEY},"audit-remainder|"+"|".join(x)))):
  if not rem:break
  audit_n[k]+=1;rem-=1
 if rem:raise RuntimeError("audit allocation lacks capacity")
 audit=[]
 for k,n in audit_n.items():
  pool=[r for r in selected if (r["formal_arm"],r["entry_stratum"])==k]
  audit.extend(sorted(pool,key=lambda r:rank(r,"audit|"+k[0]+"|"+k[1]))[:n])
 if len(audit)!=160:raise RuntimeError("audit cardinality failure")
 contexts={}
 for r in selected:
  h=r["context_sha256"];contexts.setdefault(h,{"record_id":context_id(h),"context_sha256":h,"full_document":r["normalized_full_document"]})
 # Readers receive only the opaque id, context hash, and full frozen document.
 ordered=sorted(contexts.values(),key=lambda v:hashlib.sha256((SEED+"|primary-packet-order|"+v["record_id"]).encode()).hexdigest())
 primary=[]
 for i in range(0,len(ordered),20):
  packet_id="formal800-primary-%03d"%(i//20+1)
  primary.extend([dict(v,assignment={"packet_id":packet_id,"reviewer_role":"primary","provenance":"formal800-cloud-freeze-v1"}) for v in ordered[i:i+20]])
 audit_contexts={r["context_sha256"] for r in audit}
 blind=[{"record_id":"audit-"+hashlib.sha256((SEED+"|audit|"+h).encode()).hexdigest()[:20],"context_sha256":h,"full_document":contexts[h]["full_document"],"assignment":{"packet_id":"formal800-blind-audit-v1","reviewer_role":"blind_audit","provenance":"formal800-cloud-freeze-v1"}} for h in sorted(audit_contexts,key=lambda h:hashlib.sha256((SEED+"|audit-packet-order|"+h).encode()).hexdigest())]
 hidden=[]
 for r in selected:
   h=r["context_sha256"]; k=(r["formal_arm"],r["entry_stratum"]); hidden.append({"record_id":contexts[h]["record_id"],**{x:r[x] for x in KEY},"formal_arm":r["formal_arm"],"entry_stratum":r["entry_stratum"],"N_h":groups[k],"n_h":take[k],"audit_selected":canonical(r) in {canonical(x) for x in audit},"pi12":r["total_inclusion_probability"],"pi3":take[k]/groups[k],"nested_design_weight":r["nested_design_weight"],"upstream_probability_status":r["upstream_probability_status"],"occupation_major":r.get("OCCUPATION_MAJOR"),"raw_exact_text_sha256":r["raw_exact_text_sha256"],"normalized_context_sha256":h,"normalization_flags":r["normalization_flags"]})
 private=Path(a.private_output)
 for packet_id in sorted({x["assignment"]["packet_id"] for x in primary}):
  dump(private/(packet_id.upper().replace("-","_")+"_PRIVATE.jsonl"),[x for x in primary if x["assignment"]["packet_id"]==packet_id])
 dump(private/"BLIND_AUDIT_PACKET_PRIVATE.jsonl",blind);dump(private/"HIDDEN_LINKAGE_PRIVATE.jsonl",hidden)
 cross=collections.Counter()
 for h in contexts:
  uses={(r["formal_arm"],r["entry_stratum"]) for r in selected if r["context_sha256"]==h}
  if len(uses)>1:cross["cross_arm_or_stratum_contexts"]+=1
 receipt={"version":"formal800-ad-sample-v1","status":"pass","scheduler":{"job_id":os.getenv("SLURM_JOB_ID"),"host":platform.node()},"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"frame":{"path":a.frame,"sha256":sha(a.frame),"rows":pf.metadata.num_rows},"frozen_rule":{"version":rule.VERSION,"rule_engine_sha256":sha(Path(a.frozen_rule_dir)/"rule_engine.py"),"legacy_normalizer_sha256":sha(Path(a.frozen_rule_dir)/"legacy_v5_frozen.py"),"entry_predicate":"graduate_language OR explicit_no_experience"},"exclusions":{"manifests":ex_audit,"excluded_ads":dict(excluded),"excluded_unique_exact_contexts":len(excluded_contexts),"excluded_ads_by_source_arm_and_reason":dict(excluded_by_arm),"excluded_weight_mass_nested_known_only":excluded_weight,"excluded_ads_without_verified_upstream_weights":excluded_missing_weight,"eligible_ads":len(rows)},"upstream_probability_status":dict(upstream_status),"parent_frame_inference_enabled":False,"main_estimand":"eligible_fixed10k_using_third_stage_pi3_only","sample":{"unit":"ad","ads":800,"unique_review_contexts":len(primary),"arm_quotas":QUOTA,"eligible_strata":{"|".join(k):v for k,v in groups.items()},"selected_strata":{"|".join(k):v for k,v in take.items()},"redistribution":redistribution,"pi3":"selected_ads / eligible_ads within arm x entry stratum","audit_ads":160,"unique_audit_contexts":len(blind),"context_reuse":dict(cross)},"hash_scopes":{"raw_exact_source":"exact_text_sha256 is SHA-256 of cached original text","review_context":"context_sha256 is SHA-256 of rulefirst-v1.2 normalized_text; packet full_document is that exact normalized text"},"privacy":"private packets/linkage contain text and row identities; this receipt contains aggregates and hashes only"}
 dump(a.public_receipt,receipt)
if __name__=="__main__":main()
