#!/usr/bin/env python3
"""Materialize reviewer files from an existing selection without rescanning the frame."""
import argparse,hashlib,importlib.util,json,os
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--generator',type=Path,required=True);p.add_argument('--selection',type=Path,required=True);p.add_argument('--selected-text',type=Path,required=True);p.add_argument('--reviewer-schema',type=Path,required=True);p.add_argument('--private-output-dir',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--predictions',type=Path);a=p.parse_args()
 spec=importlib.util.spec_from_file_location('frozen_review_generator',a.generator);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 selection=json.loads(a.selection.read_text());before=sha(a.selection)
 count=mod.materialize(a,selection,a.private_output_dir)
 if sha(a.selection)!=before:raise RuntimeError('frozen selection changed during phase 2')
 value={'status':'complete','selection_sha256':before,'selected_text_sha256':sha(a.selected_text),'reviewer_schema_sha256':sha(a.reviewer_schema),'unique_ads':len(selection['selected']),'core_dual_review':count,'full_frame_rescanned':False}
 tmp=Path(str(a.receipt)+'.tmp');tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');os.replace(tmp,a.receipt)
if __name__=='__main__':main()
