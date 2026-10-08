#!/usr/bin/env python3
"""Aggregate frozen-export failures; optionally remove only recognized runtime tokens."""
import argparse,collections,hashlib,json,sys
from pathlib import Path

TOKENS=("[end of text]","<|im_end|>","<|endoftext|>","</s>")
OBJECTS=("general_work","occupation_task","industry_domain")
def rows(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x]
def category(e):
 for p in ("raw_output_invalid_json","raw_output_root_not_object","raw_output_root_additional_properties","findings_missing_or_not_array","finding_not_object","finding_unknown_object","row_structure","structure","state_shape","quote","duration_structure"):
  if e.startswith(p): return p
 return e.split(":",1)[0]
def current_unwrap(raw):
 try: v,n=json.JSONDecoder().raw_decode(raw.lstrip())
 except json.JSONDecodeError:return raw,"invalid_json"
 tail=raw.lstrip()[n:].strip()
 if tail=="[end of text]": return json.dumps(v,ensure_ascii=False,separators=(",",":")),"current_marker"
 if not tail:return json.dumps(v,ensure_ascii=False,separators=(",",":")),"strict_json"
 return raw,"other_tail"
def known_token_unwrap(raw):
 s=raw.lstrip()
 try:v,n=json.JSONDecoder().raw_decode(s)
 except json.JSONDecodeError:return None,None
 tail=s[n:].strip(); parts=[]
 while tail:
  hit=next((t for t in TOKENS if tail.startswith(t)),None)
  if hit is None:return None,None
  parts.append(hit); tail=tail[len(hit):].strip()
 return json.dumps(v,ensure_ascii=False,separators=(",",":")),"+".join(parts) if parts else "strict_json"
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); a=ap.parse_args(); root=Path(a.root); out=root/'diagnostic'; out.mkdir(exist_ok=False)
 sys.path.insert(0,str(root/'bundle/archive/production_standard_20261008')); import export_candidates as ex
 src=rows(root/'imported/prepared/SOURCE32_PRIVATE.jsonl'); prior=rows(root/'results/qualification/FIELD_CANDIDATES_PRIVATE.jsonl')
 parse=collections.Counter(); rowerr=collections.Counter(); objerr=collections.Counter(); outcomes=collections.Counter(); wrappers=[]; proposed=[]; detail=[]
 for i,s in enumerate(src,1):
  raw=(root/'run/merged/tasks'/f'record_{i:02d}'/'raw.stdout').read_text()
  normalized,mode=current_unwrap(raw); parse[mode]+=1
  alt,token=known_token_unwrap(raw); proposed.append((alt,token))
  rid=str(s['record_id']); h=hashlib.sha256(s['original_text'].encode()).hexdigest(); wrappers.append({'processing_position_1based':i,'record_id':rid,'source_text_sha256':h,'raw_output_line_sha256':hashlib.sha256(normalized.encode()).hexdigest(),'raw_output':normalized})
  detail.append({'index':i,'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'raw_bytes':len(raw.encode()),'parse_mode':mode,'recognized_runtime_tokens':token})
 exports=ex.export_rows(src,wrappers)
 for r in exports:
  for e in r['row_errors']:rowerr[category(e)]+=1
  for o in r['objects']:
   outcomes[(o['object'],o['outcome_status'])]+=1
   for e in o['errors']:objerr[(o['object'],category(e))]+=1
 systematic=[]
 systematic += [{'level':'row','category':k,'count':v,'denominator':32} for k,v in rowerr.items() if v==32]
 systematic += [{'level':'object','object':o,'category':k,'count':v,'denominator':32} for (o,k),v in objerr.items() if v==32]
 correction=all(x[0] is not None for x in proposed) and any(d['parse_mode']=='other_tail' for d in detail) and all((d['recognized_runtime_tokens'] or '') for d in detail if d['parse_mode']=='other_tail')
 correction_reason='recognized_runtime_token_envelope_only' if correction else 'no_uniform_lossless_transport_adapter_proven'
 corrected_receipt=None
 if correction:
  fixed=[]
  for i,(s,(raw,token)) in enumerate(zip(src,proposed),1):
   rid=str(s['record_id']); h=hashlib.sha256(s['original_text'].encode()).hexdigest(); fixed.append({'processing_position_1based':i,'record_id':rid,'source_text_sha256':h,'raw_output_line_sha256':hashlib.sha256(raw.encode()).hexdigest(),'raw_output':raw})
  corrected=ex.export_rows(src,fixed); p=out/'CORRECTED_FIELD_CANDIDATES_PRIVATE.jsonl'; p.write_text(ex.serialize_jsonl(corrected))
  corrected_receipt=ex.build_public_receipt(corrected,hashlib.sha256((root/'imported/prepared/SOURCE32_PRIVATE.jsonl').read_bytes()).hexdigest(),hashlib.sha256(p.read_bytes()).hexdigest())
  (out/'CORRECTED_EXPORT_PUBLIC.json').write_text(json.dumps(corrected_receipt,indent=2,sort_keys=True)+'\n')
 public={'schema_version':'linkup-bu-export-diagnostic-v1','records':32,'parse_mode_counts':dict(parse),'row_error_category_counts':dict(rowerr),'object_outcome_counts':{f'{o}.{s}':n for (o,s),n in outcomes.items()},'object_error_category_counts':{f'{o}.{e}':n for (o,e),n in objerr.items()},'first_systematic_causes':systematic,'lossless_adapter_reexport_performed':correction,'adapter_decision':correction_reason,'semantic_repairs':0,'raw_outputs_changed':False}
 (out/'DIAGNOSTIC_PUBLIC.json').write_text(json.dumps(public,indent=2,sort_keys=True)+'\n'); (out/'DIAGNOSTIC_PRIVATE.json').write_text(json.dumps({'records':detail},indent=2)+'\n')
if __name__=='__main__':main()
