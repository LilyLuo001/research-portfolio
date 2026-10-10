#!/usr/bin/env python3
"""Public-output arithmetic and provenance QA for the D63 comparison."""
import argparse, csv, datetime as dt, hashlib, json, os

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def readcsv(path):
    with open(path,encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def num(x): return None if x in ('',None,'None') else float(x)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--public',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    rec=json.load(open(os.path.join(a.public,'RUN_RECEIPT_PUBLIC.json')))
    if rec['status']!='pass' or rec['coverage_posting_denominator']!=424226 or rec['analysis_posting_denominator']!=424225: raise RuntimeError('receipt denominator/status')
    for name,meta in rec['outputs'].items():
        if sha(os.path.join(a.public,name))!=meta['sha256']:raise RuntimeError('output hash '+name)
    tech=readcsv(os.path.join(a.public,'TECHNOLOGY_GROUPS_PUBLIC.csv'))
    tc={r['technology_group']:int(r['posting_count']) for r in tech}
    if set(tc)!={'software_only','ai_only','software_and_ai','neither_observed'} or sum(tc.values())!=424225:raise RuntimeError('tech partition')
    raw=readcsv(os.path.join(a.public,'RAW_OUTCOME_RATES_PUBLIC.csv'))
    den={'software_only':tc['software_only'],'ai_only':tc['ai_only'],'software_and_ai':tc['software_and_ai'],'neither_observed':tc['neither_observed'],'any_ai':tc['ai_only']+tc['software_and_ai'],'all_first5':424225}
    for r in raw:
        if int(r['denominator'])!=den[r['technology_group']]:raise RuntimeError('raw denominator')
        if not 0<=int(r['numerator'])<=int(r['denominator']):raise RuntimeError('raw bounds')
        d=int(r['denominator']); observed=num(r['fraction'])
        if d == 0:
            if observed is not None: raise RuntimeError('zero-denominator raw fraction')
        elif observed is None or abs(observed-int(r['numerator'])/d)>1e-12:raise RuntimeError('raw fraction arithmetic')
    for name in ('OCCUPATION_STANDARDIZED_COMPARISONS_PUBLIC.csv','COMPANY_OCCUPATION_SENSITIVITY_PUBLIC.csv'):
        for r in readcsv(os.path.join(a.public,name)):
            for side in ('left','right'):
                if int(r[side+'_retained_n'])>int(r[side+'_valid_occupation_n']):raise RuntimeError('retained bounds')
            if r['status']=='estimated':
                l=num(r['left_standardized_rate']); rr=num(r['right_standardized_rate']); d=num(r['difference_right_minus_left_percentage_points'])
                if l is None or rr is None or not (-1e-12<=l<=1+1e-12 and -1e-12<=rr<=1+1e-12) or abs(d-(rr-l)*100)>1e-9:raise RuntimeError('standardized difference')
    entry=readcsv(os.path.join(a.public,'ENTRY_RESPONSIBILITY_COOCCURRENCE_PUBLIC.csv'))
    for r in entry:
        cells=sum(int(r[x]) for x in ('marker_yes_outcome_yes','marker_yes_outcome_no_observed','marker_no_observed_outcome_yes','marker_no_observed_outcome_no_observed'))
        if cells!=424225 or int(r['marker_population_n'])!=int(r['marker_yes_outcome_yes'])+int(r['marker_yes_outcome_no_observed']):raise RuntimeError('entry 2x2')
    result={'version':'d63-first5-public-output-qa-v1','status':'pass','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'producer_receipt_sha256':sha(os.path.join(a.public,'RUN_RECEIPT_PUBLIC.json')),'checks':{'output_hashes':True,'technology_partition_424225':True,'raw_denominators':True,'standardized_arithmetic':True,'entry_2x2_denominators':True},'scope':'public aggregates only; no private rows/text read; not semantic validation'}
    tmp=a.output+'.tmp';json.dump(result,open(tmp,'w'),indent=2,sort_keys=True);open(tmp,'a').write('\n');os.replace(tmp,a.output)
if __name__=='__main__':main()
