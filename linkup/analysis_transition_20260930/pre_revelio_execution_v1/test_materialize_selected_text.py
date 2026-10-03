#!/usr/bin/env python3
import csv,json,subprocess,sys,tempfile
from pathlib import Path
import pyarrow as pa,pyarrow.parquet as pq
HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as td:
 root=Path(td);source=root/'source.parquet';selection=root/'selection.json';mapping=root/'map.jsonl';out=root/'private.csv';receipt=root/'receipt.json'
 pq.write_table(pa.table({'JOB_HASH':['a'*32,'b'*32,'c'*32],'DESCRIPTION':['zero','one','two']}),source,row_group_size=2)
 private_key=json.dumps(['c'*32,source.name,2,9],separators=(',',':'))
 selection.write_text(json.dumps({'seed':'20261003','selected':[{'private_key':private_key}]})+'\n')
 mapping.write_text(json.dumps({'SOURCE_FILE':source.name,'path':str(source)})+'\n')
 subprocess.run([sys.executable,str(HERE/'materialize_selected_text.py'),'--selection',str(selection),'--source-map',str(mapping),'--output',str(out),'--receipt',str(receipt),'--text-column','DESCRIPTION','--max-rows','40'],check=True)
 row=list(csv.DictReader(out.open()))[0]
 assert row['ORIGINAL_TEXT']=='two' and row['original_text']=='two' and row['private_key']==private_key
 assert json.loads(receipt.read_text())['row_groups_read']==1
 print('ok: frozen JSON selection, one selected row, one row group, exact hash, phase2-compatible columns')
