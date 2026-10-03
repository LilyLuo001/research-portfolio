#!/usr/bin/env python3
import hashlib, json, os
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

ROOT=Path('/public/home/lilysharp/linkup_release_v1/full_semantic_v1')
OUT=Path('/public/home/lilysharp/linkup_analysis_execution_oct02/results/fixed3_private_keys')
IDS=['a253a8c15266c684ad353c0e152b72edc9260a5d92205530c1415cbfc27ead29','2a05d0dec58380170039977909bfac25c2cc192dba00b42271d1ac7bf8091453','653675e006082b16b24bdd2c98979b221e1db5459ff09a19701e45f5482959ee']
COLS=['JOB_HASH','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW']
OUT.mkdir(parents=True,exist_ok=False)
tables=[]; per={}
for sid in IDS:
    paths=sorted((ROOT/sid).glob('chunk_*/ad_status.parquet'))
    if not paths: raise FileNotFoundError(sid)
    table=pq.read_table(paths,columns=COLS); tables.append(table); per[sid]=table.num_rows
combined=pa.concat_tables(tables)
if combined.num_rows!=sum(per.values()): raise RuntimeError('row conservation')
dest=OUT/'fixed3_keys.parquet'; temp=OUT/'fixed3_keys.parquet.tmp'
pq.write_table(combined,temp,compression='zstd',row_group_size=65536); os.replace(temp,dest)
receipt={'status':'complete','rows':combined.num_rows,'per_shard_rows':per,'columns':COLS,
         'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'privacy':'private key-only projection; not for Git'}
(OUT/'PROJECTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
