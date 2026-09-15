"""Outcome-blind publication metadata probe; no article body retained/exported."""
import csv,json,hashlib,re,sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from check_public_clock_metadata import ClockParser
O=Path(__file__).resolve().parent
B=O.parents[2]
EVENTS=B/'missing_data_round_20260914/union_v2_earnings_inputs/selected_event_metadata.csv'
def safe_clock_text(s):
    s=' '.join(s.split())
    # Clock/date lexicon only; financial prose cannot pass.
    words=re.findall(r'[A-Za-z]+',s)
    allowed={'january','february','march','april','may','june','july','august','september','october','november','december','jan','feb','mar','apr','jun','jul','aug','sep','sept','oct','nov','dec','monday','tuesday','wednesday','thursday','friday','saturday','sunday','am','pm','et','est','edt','utc','gmt','at','updated','published','on'}
    return s if len(s)<=130 and re.search(r'\d{1,2}:\d{2}',s) and all(w.lower() in allowed for w in words) else None

class PublicClockParser(ClockParser):
    def __init__(self):
        super().__init__();self.captures=[];self.visible=[]
    def handle_starttag(self,tag,attrs):
        super().handle_starttag(tag,attrs)
        classes=set(dict(attrs).get('class','').split())
        selected=classes&{'release-date','article-published-date','article-date','date','module_date-text','press-release-date'}
        if tag=='time' or selected:self.captures.append((tag,'time' if tag=='time' else sorted(selected)[0],[]))
    def handle_data(self,data):
        super().handle_data(data)
        for _,_,buf in self.captures:buf.append(data)
    def handle_endtag(self,tag):
        super().handle_endtag(tag)
        pending=[]
        for close,field,buf in self.captures:
            if close==tag:
                value=safe_clock_text(' '.join(buf))
                if value:self.visible.append({'field':'visible:'+field,'value':value})
            else:pending.append((close,field,buf))
        self.captures=pending

def fetch(t):
    out=dict(t)
    try:
        res=requests.get(t['url'],timeout=25,headers={'User-Agent':'Mozilla/5.0'})
        out['http_status']=res.status_code;out['final_host']=urlparse(res.url).netloc
        p=PublicClockParser(); candidates=[]
        if res.ok:
            p.feed(res.text)
            for field,value in sorted(set(p.items)):
                if re.fullmatch(r'[0-9TtZz:+. /-]{8,50}',value):candidates.append({'field':field,'value':value})
            candidates.extend(p.visible)
        out['clock_candidates']=candidates
        out['status']='PUBLICATION_CLOCK_CANDIDATES' if candidates else 'NO_CLOCK_FOUND' if res.ok else 'HTTP_FAILURE'
    except Exception as e:out.update(status='FETCH_ERROR',error_type=type(e).__name__)
    return out

def main():
    tasks=json.loads((O/'locators.json').read_text())
    with EVENTS.open(newline='') as f:events=[{k:r[k] for k in ['date_valid_raw_symbol','announcement_date','announcement_times_all','sample_period','wave_id']} for r in csv.DictReader(f)]
    for t in tasks:
        match=[e for e in events if e['date_valid_raw_symbol']==t['ticker'] and e['announcement_date']==t['date'] and e['sample_period']=='PRE']
        assert len(match)==1,(t['ticker'],t['date'],len(match))
        t['source_clock_string']=match[0]['announcement_times_all'];t['wave_id']=match[0]['wave_id']
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,tasks))
    (O/'public_timestamp_candidates.json').write_text(json.dumps(results,indent=2)+'\n')
    receipt=dict(utc=datetime.now(timezone.utc).isoformat(),status='CANDIDATES_REQUIRE_SOURCE_INTERPRETATION',locators=len(tasks),status_counts=dict(Counter(r['status'] for r in results)),sample='eight located PRE dates in existing852 population; nonrandom documentary check, not new research sample',raw_body_saved_or_exported=False,financial_values_exported=False,gate1='NOT_PASSED',code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),event_manifest_sha256=hashlib.sha256(EVENTS.read_bytes()).hexdigest())
    (O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
