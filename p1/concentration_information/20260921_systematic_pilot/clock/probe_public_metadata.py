"""Public timestamp-only projection. Never save/print financial page bodies."""
import concurrent.futures
import datetime as dt
import hashlib
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SOURCES = [
    ('P1-2023-08-01','issuer','https://corporate.exxonmobil.com/news/news-releases/2023/0131_exxonmobil-announces-full-year-2022-results'),
    ('P1-2023-08-01','syndicated_wire','https://www.nasdaq.com/press-release/exxonmobil-announces-full-year-2022-results-2023-01-31'),
    ('P1-2023-08-03','issuer','https://corporate.exxonmobil.com/news/news-releases/2023/0728_exxonmobil-announces-second-quarter-2023-results'),
    ('P1-2023-08-03','syndicated_wire','https://www.nasdaq.com/press-release/exxonmobil-announces-second-quarter-2023-results-2023-07-28'),
    ('P1-2023-06-02','issuer','https://www.unitedhealthgroup.com/newsroom/2023/2023-04-14-uhg-reports-first-quarter-results.html'),
    ('P1-2023-06-02','syndicated_wire','https://www.nasdaq.com/press-release/unitedhealth-group-reports-first-quarter-2023-results-2023-04-14'),
    ('P1-2023-06-02','distributor','https://www.businesswire.com/news/home/20230414005084/en/'),
    ('P1-2023-01-01','issuer','https://www.apple.com/newsroom/2023/02/apple-reports-first-quarter-results/'),
    ('P1-2023-01-01','syndicated_wire','https://markets.chroniclejournal.com/thepilotnews/article/bizwire-2023-2-2-apple-reports-first-quarter-results'),
    ('P1-2023-01-03','issuer','https://www.apple.com/newsroom/2023/08/apple-reports-third-quarter-results/'),
    ('P1-2023-01-03','syndicated_wire','https://markets.financialcontent.com/stocks/article/bizwire-2023-8-3-apple-reports-third-quarter-results'),
    ('P1-2023-01-03','distributor','https://www.businesswire.com/news/home/20230803893875/en/'),
    ('P1-2023-02-02','issuer','https://news.microsoft.com/source/2023/04/25/microsoft-earnings-press-release-available-on-investor-relations-website-18/'),
]

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags=[]; self.links=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='meta':
            key=a.get('property',a.get('name',a.get('itemprop','')))
            if re.search(r'publish|modif|date|time',key,re.I):
                val=a.get('content','')
                if len(val)<150: self.tags.append({'field':key,'value':val})
        if tag=='time' and a.get('datetime'): self.tags.append({'field':'time.datetime','value':a['datetime']})
        if tag=='a' and 'businesswire.com/news/home/' in a.get('href',''):
            self.links.append(a['href'])

def fetch(source):
    event,kind,url=source
    row={'event_id':event,'source_type':kind,'url':url,'retrieved_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; academic timestamp metadata check)'})
        with urllib.request.urlopen(req,timeout=20) as r:
            body=r.read(6_000_000); row.update(http_status=r.status,final_url=r.url,response_bytes=len(body),response_sha256=hashlib.sha256(body).hexdigest())
        html=body.decode('utf-8',errors='replace'); p=Metadata(); p.feed(html)
        # Extract datetime strings only, never whole JSON-LD scripts or financial text.
        dates=re.findall(r'"(datePublished|dateModified|uploadDate)"\s*:\s*"([^"]{1,100})"',html)
        visible=re.sub(r'<[^>]+>',' ',html)
        stamps=re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+2023\s+(?:at\s+)?\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*(?:EST|EDT|ET|PST|PDT|UTC)',visible)
        row.update(status='METADATA_FETCHED',metadata=p.tags,json_dates=[{'field':k,'value':v} for k,v in dates],visible_timestamp_strings=sorted(set(stamps)),distributor_links=sorted(set(p.links)))
    except Exception as e:
        row.update(status='FETCH_FAILED',error_type=type(e).__name__,error=str(e)[:200])
    return row

if __name__=='__main__':
    rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(fetch,SOURCES))
    out={'scope':'six existing public announcements; new source URLs explicitly approved; current retrieval is not contemporaneous capture','raw_bodies_saved':False,'rows':rows}
    Path(__file__).with_name('PUBLIC_METADATA_RECEIPT.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
