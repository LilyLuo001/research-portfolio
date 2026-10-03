#!/usr/bin/env python3
"""Build a locator only for source files named by a frozen selected-key manifest."""
import argparse,json,os
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True);p.add_argument('--raw-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 value=json.loads(a.selection.read_text());rows=value.get('selected')
 if not isinstance(rows,list) or len(rows)>40:raise RuntimeError('selection must contain at most 40 selected rows')
 names=set()
 for row in rows:
  try: parts=json.loads(row['private_key'])
  except (KeyError,TypeError,json.JSONDecodeError):raise RuntimeError('invalid selected private_key')
  if not isinstance(parts,list) or len(parts)!=4:raise RuntimeError('private_key must encode four fields')
  name=parts[1]
  if not isinstance(name,str) or Path(name).name!=name:raise RuntimeError('SOURCE_FILE must be a basename')
  names.add(name)
 records=[]
 for name in sorted(names):
  target=(a.raw_root/name).resolve()
  if target.parent!=a.raw_root.resolve() or not target.is_file():raise RuntimeError('selected source file unavailable: '+name)
  records.append({'SOURCE_FILE':name,'path':str(target)})
 a.output.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(a.output)+'.tmp')
 tmp.write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in records));os.chmod(tmp,0o600);os.replace(tmp,a.output)
 print(json.dumps({'status':'complete','selected_rows':len(rows),'source_files':len(records)}))
if __name__=='__main__':main()
