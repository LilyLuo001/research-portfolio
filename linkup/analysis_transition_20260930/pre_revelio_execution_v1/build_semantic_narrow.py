#!/usr/bin/env python3
"""Project frozen typed V6 tables to one private analysis row per canonical ad."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

VERSION = "pre_revelio_semantic_narrow_v1"
KEYS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
OBJECTS = ("general_work", "specific_tool", "industry_domain", "object_unspecified")
TECHNOLOGIES = ("traditional_software", "generative_ai", "predictive_ai", "unspecified_ai")
ROLES = ("use", "develop", "implement", "unknown")

AD_OUTPUT_SCHEMA = pa.schema(
    [("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()),
     ("SOURCE_ROW", pa.int64()), ("RECORD_SOURCE_ROW", pa.int64()),
     ("CREATED", pa.timestamp("ms")), ("STATE", pa.string()),
     ("usable", pa.bool_()), ("DESCRIPTION_EMPTY", pa.bool_()),
     ("PARSE_ERROR", pa.bool_()), ("INPUT_EVIDENCE_TRUNCATED", pa.bool_()),
     ("ENRICHMENT_INCOMPLETE", pa.bool_())]
    + [("exp_%s_%s" % (obj, suffix), pa.bool_())
       for obj in OBJECTS
       for suffix in ("main", "required", "broad", "exact_or_unspecified")]
    + [("tech_%s_detected" % tech, pa.bool_()) for tech in TECHNOLOGIES]
    + [("tech_%s_%s_explicit" % (tech, role), pa.bool_())
       for tech in TECHNOLOGIES for role in ("use", "develop", "implement")]
    + [("exp_occupation_task_main", pa.bool_()),
       ("exp_occupation_task_available", pa.bool_())]
)

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def atomic_json(path,value):
    path=Path(path); temp=Path(str(path)+".tmp")
    temp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n"); os.replace(temp,path)

def iter_rows(shard,name):
    paths=sorted(Path(shard).glob("chunk_*/%s.parquet"%name))
    if not paths: raise FileNotFoundError("missing frozen typed table: "+name)
    for path in paths:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=65536): yield from batch.to_pylist()

def key(row):
    value=tuple(row.get(name) for name in KEYS)
    if any(part is None for part in value): raise RuntimeError("nullable canonical key")
    return value

def validate_production_binding(shard,receipt,gate):
    g=json.loads(Path(gate).read_text())
    if g.get("status")!="complete" or g.get("final_publication_complete") is not True or g.get("total_shards")!=2464:
        raise RuntimeError("global 2,464-shard publication gate is not accepted")
    wrapper=json.loads(Path(receipt).read_text()); complete_path=Path(shard)/"SHARD_COMPLETE.json"
    if wrapper.get("status")!="published_verified": raise RuntimeError("input receipt is not published_verified")
    if not complete_path.is_file() or wrapper.get("shard_complete_sha256")!=sha256(complete_path):
        raise RuntimeError("published receipt does not bind this shard SHARD_COMPLETE")
    complete=json.loads(complete_path.read_text())
    if wrapper.get("shard_complete")!=complete or complete.get("status")!="complete":
        raise RuntimeError("published receipt content differs from shard completion marker")
    return complete

def blank_flags():
    result={}
    for obj in OBJECTS:
        result.update({"exp_%s_main"%obj:False,"exp_%s_required"%obj:False,
                       "exp_%s_broad"%obj:False,"exp_%s_exact_or_unspecified"%obj:False})
    for tech in TECHNOLOGIES:
        result["tech_%s_detected"%tech]=False
        for role in ("use","develop","implement"): result["tech_%s_%s_explicit"%(tech,role)]=False
    return result

def build(shard,output,receipt,threads,memory,gate=None):
    del threads,memory
    shard=Path(shard); output=Path(output)
    complete=validate_production_binding(shard,receipt,gate) if receipt and gate else None
    ads={}; order=[]
    for ad in iter_rows(shard,"ad_status"):
        k=key(ad)
        if k in ads: raise RuntimeError("duplicate canonical key in ad_status")
        value=blank_flags(); value.update({**dict(zip(KEYS,k)),"CREATED":ad["CREATED"],"STATE":ad["STATE"],
            "usable":not any(ad[n] for n in ("DESCRIPTION_EMPTY","PARSE_ERROR","INPUT_EVIDENCE_TRUNCATED","ENRICHMENT_INCOMPLETE")),
            "DESCRIPTION_EMPTY":ad["DESCRIPTION_EMPTY"],"PARSE_ERROR":ad["PARSE_ERROR"],
            "INPUT_EVIDENCE_TRUNCATED":ad["INPUT_EVIDENCE_TRUNCATED"],"ENRICHMENT_INCOMPLETE":ad["ENRICHMENT_INCOMPLETE"],
            "exp_occupation_task_main":None,"exp_occupation_task_available":False})
        ads[k]=value; order.append(k)
    if complete and complete.get("accounting",{}).get("canonical_usa_rows")!=len(ads):
        raise RuntimeError("published canonical count differs from ad_status")
    observed={"experience.OBJECT_TYPE":set(),"experience.BINDING_STATUS":set(),
              "technology.TECHNOLOGY_TYPE":set(),"technology.ROLE":set(),"technology.BINDING_STATUS":set()}
    durations=[]; orphan_exp=orphan_tech=0
    for item in iter_rows(shard,"experience"):
        k=key(item); target=ads.get(k)
        if target is None: orphan_exp+=1; continue
        obj=item["OBJECT_TYPE"]; binding=item["BINDING_STATUS"]
        if obj is not None: observed["experience.OBJECT_TYPE"].add(obj)
        if binding is not None: observed["experience.BINDING_STATUS"].add(binding)
        if obj not in OBJECTS or not item["APPLICANT_CONTEXT_CANDIDATE"]: continue
        target["exp_%s_broad"%obj]=True
        main=binding=="explicit" and item["REQUIREMENT_STRENGTH"] in ("required","preferred")
        if main:
            target["exp_%s_main"%obj]=True
            target["exp_%s_required"%obj] |= item["REQUIREMENT_STRENGTH"]=="required"
            target["exp_%s_exact_or_unspecified"%obj] |= item["BOUND_TYPE"]=="exact_or_unspecified"
            if target["usable"] and item["MIN_YEARS"] is not None:
                durations.append({**dict(zip(KEYS,k)),"EVIDENCE_ORDINAL":item["EVIDENCE_ORDINAL"],"OBJECT_TYPE":obj,
                    "MIN_YEARS":item["MIN_YEARS"],"MAX_YEARS":item["MAX_YEARS"],"DURATION_UNIT":item["DURATION_UNIT"],
                    "BOUND_TYPE":item["BOUND_TYPE"],"REQUIREMENT_STRENGTH":item["REQUIREMENT_STRENGTH"]})
    for item in iter_rows(shard,"technology"):
        k=key(item); target=ads.get(k)
        if target is None: orphan_tech+=1; continue
        tech,role,binding=item["TECHNOLOGY_TYPE"],item["ROLE"],item["BINDING_STATUS"]
        if tech is not None: observed["technology.TECHNOLOGY_TYPE"].add(tech)
        if role is not None: observed["technology.ROLE"].add(role)
        if binding is not None: observed["technology.BINDING_STATUS"].add(binding)
        if tech not in TECHNOLOGIES or not item["APPLICANT_CONTEXT_CANDIDATE"]: continue
        target["tech_%s_detected"%tech]=True
        if binding=="explicit" and role in ("use","develop","implement"):
            target["tech_%s_%s_explicit"%(tech,role)]=True
    if orphan_exp or orphan_tech: raise RuntimeError("orphan evidence keys: experience=%d, technology=%d"%(orphan_exp,orphan_tech))
    allowed={"experience.OBJECT_TYPE":set(OBJECTS),"experience.BINDING_STATUS":{"explicit","unknown"},
             "technology.TECHNOLOGY_TYPE":set(TECHNOLOGIES),"technology.ROLE":set(ROLES),
             "technology.BINDING_STATUS":{"explicit","candidate_local_relation","unknown"}}
    for name,values in observed.items():
        if values-allowed[name]: raise RuntimeError("unexpected frozen enum %s: %s"%(name,sorted(values-allowed[name])))
    output.parent.mkdir(parents=True,exist_ok=True); temp=Path(str(output)+".tmp")
    pq.write_table(pa.Table.from_pylist([ads[x] for x in order], schema=AD_OUTPUT_SCHEMA),temp,compression="zstd",row_group_size=65536)
    if pq.ParquetFile(temp).metadata.num_rows!=len(ads): temp.unlink(missing_ok=True); raise RuntimeError("output conservation failed")
    os.replace(temp,output)
    duration_output=output.with_suffix(".durations.parquet"); duration_temp=Path(str(duration_output)+".tmp")
    schema=pa.schema([(n,pa.string()) for n in KEYS[:2]]+[(n,pa.int64()) for n in KEYS[2:]]+
        [("EVIDENCE_ORDINAL",pa.int32()),("OBJECT_TYPE",pa.string()),("MIN_YEARS",pa.float64()),("MAX_YEARS",pa.float64()),
         ("DURATION_UNIT",pa.string()),("BOUND_TYPE",pa.string()),("REQUIREMENT_STRENGTH",pa.string())])
    pq.write_table(pa.Table.from_pylist(durations,schema=schema),duration_temp,compression="zstd",row_group_size=65536); os.replace(duration_temp,duration_output)
    report={"status":"complete","version":VERSION,"canonical_ads":len(ads),"output_rows":len(ads),"output_sha256":sha256(output),
        "duration_detail_rows":len(durations),"duration_detail_sha256":sha256(duration_output),
        "observed_enums":{n:sorted(v) for n,v in observed.items()},"key_audit":{"nullable_canonical_keys":0,"orphan_experience":0,"orphan_technology":0},
        "occupation_task":"unavailable_in_frozen_object_taxonomy; emitted null with availability=false",
        "year_units":"MIN_YEARS/MAX_YEARS already expressed in years by frozen enrichment",
        "duration_detail":"private clause-level sidecar; no cross-clause ad-level min/max collapse",
        "exact_or_unspecified":"retained separately; not interpreted as a proved minimum",
        "main_measure":"applicant context + explicit binding + required/preferred","broad_measure":"applicant-context within-ad candidate co-occurrence",
        "source_receipt_sha256":sha256(receipt) if receipt else None}
    atomic_json(output.with_suffix(".receipt.json"),report); return report

def main():
    p=argparse.ArgumentParser(); p.add_argument("--shard",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    p.add_argument("--receipt",type=Path); p.add_argument("--gate",type=Path); p.add_argument("--threads",type=int,default=2); p.add_argument("--memory-limit",default="4GB")
    a=p.parse_args()
    if a.receipt is None or a.gate is None: p.error("production CLI requires both --receipt and --gate")
    print(json.dumps(build(a.shard,a.output,a.receipt,a.threads,a.memory_limit,a.gate),sort_keys=True))
if __name__=="__main__": main()
