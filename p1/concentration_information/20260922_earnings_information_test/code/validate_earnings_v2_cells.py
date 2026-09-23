#!/usr/bin/env python3
"""Fail closed unless all four corrected earnings model cells match final code."""
import argparse, hashlib, json
from pathlib import Path

CELLS=("XNAS_ITCH_0","XNAS_ITCH_500","ARCX_PILLAR_0","ARCX_PILLAR_500")
def sha(path):
 h=hashlib.sha256();
 with Path(path).open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""): h.update(x)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--parts-root",type=Path,required=True);p.add_argument("--code",type=Path,required=True);a=p.parse_args(); expected=sha(a.code); rows=[]
 for cell in CELLS:
  path=a.parts_root/cell/"MODEL_RECEIPT.json"
  if not path.is_file(): raise RuntimeError("missing corrected receipt: "+str(path))
  x=json.loads(path.read_text());
  if x.get("status")!="COMPLETE_EARNINGS_MODELS_ON_SCC" or x.get("code_sha256")!=expected: raise RuntimeError("receipt status/code mismatch: "+cell)
  rows.append({"cell":cell,"loss_rows":x.get("loss_rows"),"code_sha256":x.get("code_sha256")})
 print(json.dumps({"status":"PASS_ALL_FOUR_V2_CELLS","code_sha256":expected,"cells":rows},sort_keys=True))
if __name__=="__main__":main()
