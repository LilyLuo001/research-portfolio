#!/usr/bin/env python3
"""Count quote-manifest metadata only; never opens DBN payloads."""
import argparse, csv, collections, json
from pathlib import Path
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('manifest',type=Path); ap.add_argument('--out',type=Path); a=ap.parse_args()
    c=collections.Counter(); n=0; fields=[]
    with a.manifest.open(newline='') as f:
        rd=csv.DictReader(f); fields=rd.fieldnames or []
        aliases={'dataset':['dataset','data_set'],'schema':['schema','data_schema'],'start':['start','requested_start_utc','start_utc'],'status':['completion_status','finalization_status','status']}
        missing=[k for k,v in aliases.items() if not any(x in fields for x in v)]
        if missing: raise SystemExit('missing required metadata columns: '+','.join(missing)+'; found='+','.join(fields))
        def val(r,k):
            for x in aliases[k]:
                if r.get(x): return r[x]
            return 'UNKNOWN'
        for r in rd:
            n+=1; c[(val(r,'dataset'),val(r,'schema'),val(r,'start')[:4] or 'UNKNOWN',val(r,'status'))]+=1
    out={'manifest':str(a.manifest),'rows':n,'columns':fields,'dbn_opened':False,'counts':[{'dataset':d,'schema':s,'year':y,'status':st,'n':k} for (d,s,y,st),k in sorted(c.items())]}
    t=json.dumps(out,indent=2,sort_keys=True)+'\n'
    if a.out:a.out.write_text(t)
    else: print(t,end='')
if __name__=='__main__':main()
