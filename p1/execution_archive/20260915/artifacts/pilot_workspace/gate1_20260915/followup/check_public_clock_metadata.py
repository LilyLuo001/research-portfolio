"""Check pre-existing issuer locators for PRE dates; export timestamps only.
Never output/store article text, EPS, forecasts, quotes or returns.
No URL discovery, market-data API, or POST response reading.
"""
import csv,hashlib,json,re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import requests

O=Path(__file__).resolve().parent/'clock_sources_v2'
B=O.parents[2]
class ClockParser(HTMLParser):
    def __init__(self):
        super().__init__();self.items=[];self.in_json=False;self.buf=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='meta':
            k=a.get('property',a.get('name',a.get('itemprop','')))
            if k.lower() in {'article:published_time','datepublished','date','pubdate','publishdate','datecreated'}:
                self.items.append((k,a.get('content','')))
        if tag=='time' and 'datetime' in a:self.items.append(('time.datetime',a['datetime']))
        if tag=='script' and a.get('type')=='application/ld+json':self.in_json=True;self.buf=[]
    def handle_data(self,data):
        if self.in_json:self.buf.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.in_json:
            self.in_json=False
            try:
                value=json.loads(''.join(self.buf))
                def visit(x):
                    if isinstance(x,dict):
                        for k,v in x.items():
                            if k in {'datePublished','dateCreated'} and isinstance(v,str):self.items.append(('jsonld.'+k,v))
                            elif isinstance(v,(list,dict)):visit(v)
                    elif isinstance(x,list):
                        for v in x:visit(v)
                visit(value)
            except (ValueError,TypeError):pass
            self.buf=[]

def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
def fetch(task):
    r=dict(task)
    try:
        u=requests.get(task['url'],timeout=25,headers={'User-Agent':'Mozilla/5.0 (compatible; metadata-verification)'})
        r['http_status']=u.status_code
        r['final_host']=urlparse(u.url).netloc
        p=ClockParser()
        if u.ok:p.feed(u.text)
        safe=[]
        for k,v in sorted(set(p.items)):
            if re.fullmatch(r'[0-9TtZz:+. /-]{8,50}',v):safe.append(dict(field=k,value=v))
        r['publication_timestamp_candidates']=safe
        r['status']='METADATA_CANDIDATES_NOT_CERTIFIED_FIRST_RELEASE' if safe else 'NO_MACHINE_READABLE_PUBLICATION_TIMESTAMP' if u.ok else 'HTTP_FAILURE'
    except Exception as e:r.update(status='FETCH_FAILED',error_type=type(e).__name__)
    return r

def main():
    O.mkdir(exist_ok=True)
    current=read(B/'missing_data_round_20260914/union_v2_earnings_inputs/selected_event_metadata.csv')
    keys={(r['permno'],r['announcement_date']) for r in current if r['sample_period']=='PRE'}
    tasks=[]
    for r in read(B/'earnings_events.csv'):
        if (r['permno'],r['earnings_release_date']) not in keys:continue
        tasks.append(dict(ticker=r['ticker'],public_release_date=r['earnings_release_date'],url=r['release_date_source']))
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,tasks))
    (O/'public_metadata_candidates.json').write_text(json.dumps(results,indent=2)+'\n')
    from collections import Counter
    receipt=dict(utc=datetime.now(timezone.utc).isoformat(),candidate_locators=len(tasks),status_counts=dict(Counter(r['status'] for r in results)),selection='existing fixed-order issuer/date locators intersect current852 PRE associations; no new sample selection',article_body_exported=False,headline_or_response_values_exported=False,first_public_release_certified=False,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (O/'public_metadata_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
