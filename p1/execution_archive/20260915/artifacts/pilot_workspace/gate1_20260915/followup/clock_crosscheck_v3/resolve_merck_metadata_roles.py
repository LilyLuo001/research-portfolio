"""Retain JSON-LD object roles to distinguish page metadata from article metadata."""
import json,re,hashlib
from html.parser import HTMLParser
from pathlib import Path
import requests
O=Path(__file__).resolve().parent
class RoleParser(HTMLParser):
    def __init__(self):super().__init__();self.active=False;self.parts=[];self.nodes=[];self.index=0
    def handle_starttag(self,t,a):
        if t=='script' and dict(a).get('type')=='application/ld+json':self.active=True;self.parts=[];self.index+=1
    def handle_data(self,d):
        if self.active:self.parts.append(d)
    def handle_endtag(self,t):
        if t!='script' or not self.active:return
        self.active=False
        try:
            data=json.loads(''.join(self.parts))
            def walk(x,path):
                if isinstance(x,dict):
                    stamp=x.get('datePublished')
                    if isinstance(stamp,str) and re.fullmatch(r'[0-9TtZz:+. /-]{8,50}',stamp):
                        self.nodes.append(dict(script_index=self.index,json_path=path,object_type=x.get('@type'),datePublished=stamp))
                    for k,v in x.items():
                        if isinstance(v,(dict,list)):walk(v,path+'/'+k)
                elif isinstance(x,list):
                    for i,v in enumerate(x):walk(v,path+'/'+str(i))
            walk(data,'$')
        except ValueError:pass
        self.parts=[]
rows=[]
for t in json.loads((O/'locators.json').read_text()):
    if t['ticker']!='MRK':continue
    p=RoleParser()
    res=requests.get(t['url'],timeout=25,headers={'User-Agent':'Mozilla/5.0'})
    if res.ok:p.feed(res.text)
    rows.append(dict(date=t['date'],url=t['url'],http_status=res.status_code,publication_nodes=p.nodes))
(O/'merck_metadata_roles.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps([dict(date=r['date'],publication_nodes=r['publication_nodes']) for r in rows],indent=2))
