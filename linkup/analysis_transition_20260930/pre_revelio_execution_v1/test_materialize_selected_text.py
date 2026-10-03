#!/usr/bin/env python3
import csv,json,subprocess,sys,tempfile
from pathlib import Path
import pyarrow as pa,pyarrow.parquet as pq
HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as td:
 root=Path(td);source=root/'source.parquet';selection=root/'selection.csv';mapping=root/'map.jsonl';out=root/'private.csv';receipt=root/'receipt.json'
 pq.write_table(pa.table({'JOB_HASH':['a'*32,'b'*32,'c'*32],'DESCRIPTION':['zero','one','two']}),source,row_group_size=2)
 with selection.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['JOB_HASH','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW']);w.writeheader();w.writerow({'JOB_HASH':'c'*32,'SOURCE_FILE':source.name,'SOURCE_ROW':2,'RECORD_SOURCE_ROW':9})
 mapping.write_text(json.dumps({'SOURCE_FILE':source.name,'path':str(source)})+'\n')
 subprocess.run([sys.executable,str(HERE/'materialize_selected_text.py'),'--selection',str(selection),'--source-map',str(mapping),'--output',str(out),'--receipt',str(receipt),'--text-column','DESCRIPTION','--max-rows','40'],check=True)
 assert list(csv.DictReader(out.open()))[0]['ORIGINAL_TEXT']=='two';assert json.loads(receipt.read_text())['row_groups_read']==1
 print('ok: one selected row, one row group, exact hash')
