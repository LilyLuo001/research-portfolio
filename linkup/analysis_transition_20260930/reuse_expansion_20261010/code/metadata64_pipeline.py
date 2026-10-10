#!/usr/bin/env python3
"""Bounded-memory D67 metadata projection for the 64 shards beyond the accepted first five."""
import argparse, collections, datetime as dt, gc, hashlib, importlib.util, json, os, re
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

PREFIXES = tuple("0123456789abcdef")
VERSION = "d67-metadata64-v1"
EXPECTED_NEW = 5380710
EXPECTED_FIRST5 = 424226
EXPECTED_ALL = 5804936
CAP = 10_000_000_000


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()


def atomic(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def load_base(path):
    spec = importlib.util.spec_from_file_location("d67_metadata_base", str(path))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def prepare_keys(a):
    base = load_base(a.base_code); manifest = json.load(open(a.inputs_manifest))
    files = manifest["files"]
    if len(files) != 64 or len({x["shard_id"] for x in files}) != 64:
        raise RuntimeError("target manifest must contain 64 unique shards")
    out = Path(a.key_dir); out.mkdir(parents=True, exist_ok=True)
    paths = {p: out / ("keys_%s.parquet" % p) for p in PREFIXES}
    tmps = {p: Path(str(paths[p]) + ".tmp") for p in PREFIXES}
    writers = {p: pq.ParquetWriter(tmps[p], base.KEY_SCHEMA, compression="zstd") for p in PREFIXES}
    buffers = {p: [] for p in PREFIXES}; counts = collections.Counter(); inputs = []
    try:
        for item in files:
            path = Path(item["path"])
            if sha(path) != item["sha256"] or pq.ParquetFile(path).metadata.num_rows != item["rows"]:
                raise RuntimeError("input key projection identity mismatch")
            inputs.append({"shard_id": item["shard_id"], "path": str(path), "sha256": item["sha256"], "rows": item["rows"]})
            for batch in pq.ParquetFile(path).iter_batches(batch_size=65536, columns=list(base.CANONICAL_KEY)+["CREATED","STATE"]):
                for row in base.arrow_rows(batch):
                    job = row["JOB_HASH"]
                    if not base.valid_job_hash(job): raise RuntimeError("invalid JOB_HASH")
                    if (not isinstance(row["SOURCE_FILE"], str) or not row["SOURCE_FILE"] or
                            "/" in row["SOURCE_FILE"] or "\\" in row["SOURCE_FILE"] or
                            not isinstance(row["SOURCE_ROW"], int) or row["SOURCE_ROW"] < 0 or
                            not isinstance(row["RECORD_SOURCE_ROW"], int) or row["RECORD_SOURCE_ROW"] < 0):
                        raise RuntimeError("invalid canonical locator")
                    p = job[0]
                    buffers[p].append({"JOB_HASH": job, "SOURCE_FILE": row["SOURCE_FILE"], "SOURCE_ROW": row["SOURCE_ROW"],
                        "RECORD_SOURCE_ROW": row["RECORD_SOURCE_ROW"], "POSTING_CREATED": row.get("CREATED"),
                        "POSTING_STATE": base.clean_string(row.get("STATE"))})
                    counts[p] += 1
                    if len(buffers[p]) >= 8192:
                        writers[p].write_table(base.rows_table(buffers[p], base.KEY_SCHEMA)); buffers[p] = []
        for p in PREFIXES:
            if buffers[p]: writers[p].write_table(base.rows_table(buffers[p], base.KEY_SCHEMA))
            writers[p].close(); os.replace(tmps[p], paths[p])
    except Exception:
        for p in PREFIXES:
            try: writers[p].close()
            except Exception: pass
            if tmps[p].exists(): tmps[p].unlink()
        raise
    if sum(counts.values()) != EXPECTED_NEW: raise RuntimeError("64-shard denominator mismatch")
    key_files = []
    for p in PREFIXES:
        locators, jobs = set(), set()
        for batch in pq.ParquetFile(paths[p]).iter_batches(batch_size=32768):
            for row in base.arrow_rows(batch):
                locator = tuple(row[x] for x in base.CANONICAL_KEY)
                if locator in locators or row["JOB_HASH"] in jobs: raise RuntimeError("duplicate key in prefix")
                locators.add(locator); jobs.add(row["JOB_HASH"])
        if len(locators) != counts[p]: raise RuntimeError("prefix row mismatch")
        key_files.append({"prefix": p, "rows": counts[p], "bytes": paths[p].stat().st_size, "sha256": sha(paths[p])})
        del locators, jobs; gc.collect()
    public = {"version": VERSION, "status": "complete", "stage": "prepare_keys", "posting_rows": EXPECTED_NEW,
        "target_shards": 64, "canonical_locator_unique": True, "canonical_job_hash_unique": True,
        "key_files": key_files, "input_manifest_sha256": sha(a.inputs_manifest), "base_code_sha256": sha(a.base_code),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    atomic(a.public_receipt, public)
    atomic(out/"KEY_PREP_RECEIPT_PRIVATE.json", {"status":"complete", "inputs":inputs, "public_receipt":public})


def prepare_specs(a):
    root = Path(a.root); work=root/"work"; hits=root/"private/hits"; work.mkdir(parents=True,exist_ok=True);hits.mkdir(parents=True,exist_ok=True)
    key_receipt=json.load(open(a.key_receipt));
    if key_receipt.get("posting_rows") != EXPECTED_NEW or not key_receipt.get("canonical_job_hash_unique"): raise RuntimeError("bad key receipt")
    entries=[]
    for kind, invpath in (("records",a.records_inventory),("onet",a.onet_inventory)):
        inv=json.load(open(invpath)); groups=[]; cur=[]; n=0
        for x in inv["files"]:
            if cur and n+x["size_bytes"]>CAP: groups.append(cur);cur=[];n=0
            cur.append(x);n+=x["size_bytes"]
        if cur:groups.append(cur)
        for i,g in enumerate(groups,1):
            bid="%s_%02d"%(kind,i);spec=work/(bid+"_SPEC_PRIVATE.json");output=hits/(bid+".parquet");receipt=work/(bid+"_RECEIPT_PRIVATE.json")
            atomic(spec,{"version":VERSION,"kind":kind,"batch_id":bid,"staging_cap_bytes":CAP,"key_dir":a.key_dir,
                "key_receipt":a.key_receipt,"input_files":[{k:x[k] for k in ("source_id","path","size_bytes","sha256")} for x in g],
                "output":str(output),"receipt":str(receipt)})
            entries.append({"array_index":len(entries),"kind":kind,"spec":str(spec),"spec_sha256":sha(spec),
                "source_files":len(g),"source_bytes":sum(x["size_bytes"] for x in g)})
    if len(entries) != 4 or [x["array_index"] for x in entries] != list(range(4)):
        raise RuntimeError("retained cache must resolve to the accepted four bounded batches")
    atomic(a.array_map,{"version":VERSION,"status":"ready","entries":entries,"records_inventory_sha256":sha(a.records_inventory),
        "onet_inventory_sha256":sha(a.onet_inventory),"created_utc":dt.datetime.now(dt.timezone.utc).isoformat()})


def key_values(base, key_dir, prefix, records):
    table=pq.read_table(Path(key_dir)/("keys_%s.parquet"%prefix),columns=["JOB_HASH","RECORD_SOURCE_ROW"])
    if records: return {(j,int(r)) for j,r in zip(table["JOB_HASH"].to_pylist(),table["RECORD_SOURCE_ROW"].to_pylist())}
    return table["JOB_HASH"].combine_chunks()


def extract(a):
    base=load_base(a.base_code); cfg=json.load(open(a.batch_spec));kind=cfg["kind"]
    verified=[]; total=0
    for x in cfg["input_files"]:
        p=Path(x["path"]); size=p.stat().st_size
        if size!=x["size_bytes"] or sha(p)!=x["sha256"]:raise RuntimeError("source identity mismatch")
        total+=size;verified.append(x)
    if total>CAP:raise RuntimeError("source batch exceeds cap")
    output=Path(cfg["output"]);output.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(output)+".tmp")
    schema=base.RECORD_HIT_SCHEMA if kind=="records" else base.ONET_HIT_SCHEMA
    columns=(["JOB_HASH","RECORD_SOURCE_ROW","COMPANY_ID","CREATED","LAST_CHECKED","DELETE_DATE","STATE"] if kind=="records" else ["JOB_HASH","ONET_OCCUPATION_CODE"])
    writer=pq.ParquetWriter(tmp,schema,compression="zstd");scanned=hits=0
    try:
        if kind=="onet":
            arrays=[key_values(base,cfg["key_dir"],p,False) for p in PREFIXES]; values=pa.concat_arrays(arrays)
        active_prefix = None; record_keys = None; record_job_values = None
        for item in verified:
            if kind=="records":
                m=re.search(r"hash_prefix=([0-9a-f])",item["path"])
                if not m:raise RuntimeError("Records source lacks hash_prefix partition")
                if m.group(1) != active_prefix:
                    record_keys=key_values(base,cfg["key_dir"],m.group(1),True)
                    record_job_values=pa.array([x[0] for x in record_keys],type=pa.string())
                    active_prefix=m.group(1)
            for batch in pq.ParquetFile(item["path"]).iter_batches(batch_size=262144,columns=columns):
                scanned+=batch.num_rows
                mask=pc.fill_null(pc.is_in(batch.column(0),value_set=(values if kind=="onet" else record_job_values)),False)
                filtered=pa.RecordBatch.from_arrays([pc.filter(batch.column(i),mask) for i in range(batch.num_columns)],schema=batch.schema)
                selected=[]
                for row in base.arrow_rows(filtered):
                    if kind=="records" and (row["JOB_HASH"],row["RECORD_SOURCE_ROW"]) not in record_keys:continue
                    if kind=="records": selected.append({"JOB_HASH":row["JOB_HASH"],"RECORD_SOURCE_ROW":row["RECORD_SOURCE_ROW"],
                        "COMPANY_ID":base.clean_string(row.get("COMPANY_ID")),"CREATED":row.get("CREATED"),
                        "LAST_CHECKED":row.get("LAST_CHECKED"),"DELETE_DATE":row.get("DELETE_DATE"),
                        "STATE":base.clean_string(row.get("STATE"))})
                    else:selected.append({"JOB_HASH":row["JOB_HASH"],"ONET_OCCUPATION_CODE":base.clean_string(row.get("ONET_OCCUPATION_CODE"))})
                if selected:writer.write_table(base.rows_table(selected,schema));hits+=len(selected)
        writer.close();os.replace(tmp,output)
    except Exception:
        writer.close();tmp.unlink(missing_ok=True);raise
    atomic(cfg["receipt"],{"version":VERSION,"status":"complete","kind":kind,"batch_spec_sha256":sha(a.batch_spec),
        "pipeline_code_sha256":sha(__file__),"base_code_sha256":sha(a.base_code),
        "source_rows_scanned":scanned,"hit_rows":hits,"staged_input_bytes":total,"output":str(output),"output_bytes":output.stat().st_size,
        "output_sha256":sha(output),"created_utc":dt.datetime.now(dt.timezone.utc).isoformat()})


def finalize(a):
    base=load_base(a.base_code); amap=json.load(open(a.array_map)); entries=amap["entries"]
    hitfiles={"records":[],"onet":[]}
    for e in entries:
        cfg=json.load(open(e["spec"]));rec=json.load(open(cfg["receipt"]));out=Path(cfg["output"])
        if rec.get("status")!="complete" or rec["output_sha256"]!=sha(out):raise RuntimeError("incomplete hit batch")
        hitfiles[e["kind"]].append(out)
    official=base.official_codes(Path(a.official_codes));out64=Path(a.output64);tmp=Path(str(out64)+".tmp");writer=pq.ParquetWriter(tmp,base.FINAL_SCHEMA,compression="zstd")
    counters=collections.Counter();total=0
    try:
        for prefix in PREFIXES:
            rh=collections.defaultdict(list);oh=collections.defaultdict(list)
            for kind,dest,schema in (("records",rh,base.RECORD_HIT_SCHEMA),("onet",oh,base.ONET_HIT_SCHEMA)):
                for path in hitfiles[kind]:
                    for batch in pq.ParquetFile(path).iter_batches(batch_size=65536):
                        for row in base.arrow_rows(batch):
                            if row["JOB_HASH"].startswith(prefix):dest[(row["JOB_HASH"],row["RECORD_SOURCE_ROW"]) if kind=="records" else row["JOB_HASH"]].append(row)
            for batch in pq.ParquetFile(Path(a.key_dir)/("keys_%s.parquet"%prefix)).iter_batches(batch_size=8192):
                rows=[]
                for key in base.arrow_rows(batch):
                    rs=rh.get((key["JOB_HASH"],key["RECORD_SOURCE_ROW"]),[]);os_=oh.get(key["JOB_HASH"],[]);rn,on=len(rs),len(os_)
                    r=rs[0] if rn==1 else None;o=os_[0] if on==1 else None
                    rstatus="matched_one" if rn==1 else ("missing" if rn==0 else "one_to_many_unresolved")
                    ostatus="matched_one" if on==1 else ("missing" if on==0 else "one_to_many_unresolved")
                    company=base.clean_string(r.get("COMPANY_ID")) if r else None; state=base.clean_string(r.get("STATE")) if r else None;region=base.census_region(state)
                    cstatus="record_missing" if rn==0 else ("record_one_to_many_unresolved" if rn>1 else ("company_missing" if company is None else "observed_company_scrape_entity"))
                    gstatus="record_missing" if rn==0 else ("record_one_to_many_unresolved" if rn>1 else ("state_missing" if state is None else ("state_unmapped" if region is None else "mapped_region")))
                    rc=r.get("CREATED") if r else None;pcd=key.get("POSTING_CREATED")
                    crstatus="record_missing" if rn==0 else ("record_one_to_many_unresolved" if rn>1 else ("record_created_missing" if rc is None else ("posting_created_missing" if pcd is None else ("same_calendar_date" if rc.date()==pcd.date() else "calendar_date_disagreement"))))
                    code=base.clean_string(o.get("ONET_OCCUPATION_CODE")) if o else None
                    ostatus2="no_onet_row" if on==0 else ("onet_one_to_many_unresolved" if on>1 else ("blank_code" if code is None else ("placeholder_99-9999.00" if code=="99-9999.00" else ("unofficial_code" if code not in official else "official_code"))))
                    major=code[:2] if ostatus2=="official_code" else None;complete=major is not None and region is not None
                    rows.append({"JOB_HASH":key["JOB_HASH"],"SOURCE_FILE":key["SOURCE_FILE"],"SOURCE_ROW":key["SOURCE_ROW"],"RECORD_SOURCE_ROW":key["RECORD_SOURCE_ROW"],
                        "records_match_count":rn,"records_join_status":rstatus,"COMPANY_ID":company,"company_status":cstatus,"POSTING_CREATED":pcd,"RECORD_CREATED":rc,
                        "created_alignment_status":crstatus,"LAST_CHECKED":r.get("LAST_CHECKED") if r else None,"DELETE_DATE":r.get("DELETE_DATE") if r else None,
                        "RECORD_STATE":state,"CENSUS_REGION":region,"geography_status":gstatus,"onet_match_count":on,"onet_join_status":ostatus,
                        "ONET_OCCUPATION_CODE":code,"official_occupation_status":ostatus2,"OCCUPATION_MAJOR":major,"metadata_complete_for_occ_region":complete,
                        "metadata_complete_for_company_occ_region":complete and company is not None})
                    for label in ("records_"+rstatus,"onet_"+ostatus,"company_"+cstatus,"geography_"+gstatus,"occupation_"+ostatus2,"created_"+crstatus):counters[label]+=1
                    total+=1
                if rows:writer.write_table(base.rows_table(rows,base.FINAL_SCHEMA))
            del rh,oh;gc.collect()
        writer.close()
    except Exception:
        writer.close();tmp.unlink(missing_ok=True);raise
    if total!=EXPECTED_NEW or counters["records_one_to_many_unresolved"] or counters["onet_one_to_many_unresolved"] or counters["created_calendar_date_disagreement"]:
        tmp.unlink(missing_ok=True);raise RuntimeError("metadata64 cardinality/date/denominator gate failed")
    os.replace(tmp,out64)
    combined=Path(a.output69);ctmp=Path(str(combined)+".tmp");cw=pq.ParquetWriter(ctmp,base.FINAL_SCHEMA,compression="zstd");n=0
    try:
        for path in (Path(a.first5_metadata),out64):
            pf=pq.ParquetFile(path)
            if pf.schema_arrow!=base.FINAL_SCHEMA:raise RuntimeError("metadata schema mismatch")
            for batch in pf.iter_batches(batch_size=65536):cw.write_table(pa.Table.from_batches([batch]));n+=batch.num_rows
        cw.close();os.replace(ctmp,combined)
    except Exception:
        cw.close();ctmp.unlink(missing_ok=True);raise
    if n!=EXPECTED_ALL:raise RuntimeError("metadata69 row conservation failed")
    atomic(a.public_receipt,{"version":VERSION,"status":"complete","stage":"finalize64_union_first5","new64_rows":total,"reused_first5_rows":EXPECTED_FIRST5,
        "output_rows":n,"row_conservation":True,"counts64":dict(sorted(counters.items())),
        "output64_sha256":sha(out64),"output64_bytes":out64.stat().st_size,"output_sha256":sha(combined),"output_bytes":combined.stat().st_size,
        "identity":{"pipeline_code_sha256":sha(__file__),"base_code_sha256":sha(a.base_code),"array_map_sha256":sha(a.array_map),
                    "first5_metadata_sha256":sha(a.first5_metadata),"official_codes_sha256":sha(a.official_codes),
                    "records_inventory_sha256":amap["records_inventory_sha256"],"onet_inventory_sha256":amap["onet_inventory_sha256"]},
        "claim_boundary":"current-delivery metadata mapping with explicit missing states; no historical-text or semantic relabeling claim","created_utc":dt.datetime.now(dt.timezone.utc).isoformat()})


def parser():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    q=sub.add_parser("prepare-keys");q.add_argument("--base-code",required=True);q.add_argument("--inputs-manifest",required=True);q.add_argument("--key-dir",required=True);q.add_argument("--public-receipt",required=True)
    q=sub.add_parser("prepare-specs");q.add_argument("--root",required=True);q.add_argument("--key-dir",required=True);q.add_argument("--key-receipt",required=True);q.add_argument("--records-inventory",required=True);q.add_argument("--onet-inventory",required=True);q.add_argument("--array-map",required=True)
    q=sub.add_parser("extract");q.add_argument("--base-code",required=True);q.add_argument("--batch-spec",required=True)
    q=sub.add_parser("finalize");q.add_argument("--base-code",required=True);q.add_argument("--array-map",required=True);q.add_argument("--key-dir",required=True);q.add_argument("--official-codes",required=True);q.add_argument("--first5-metadata",required=True);q.add_argument("--output64",required=True);q.add_argument("--output69",required=True);q.add_argument("--public-receipt",required=True)
    return p


if __name__=="__main__":
    a=parser().parse_args();{"prepare-keys":prepare_keys,"prepare-specs":prepare_specs,"extract":extract,"finalize":finalize}[a.cmd](a)
