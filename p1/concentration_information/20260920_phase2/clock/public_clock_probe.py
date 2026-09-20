"""Public Apple newsroom metadata probe. Does not parse or emit financial values.

Full HTML is fetched transiently on SCC; only publication metadata is retained.
This is independent publisher-clock evidence, not an earliest-public-time certificate.
"""
import argparse
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import pandas as pd

URLS = [
    "https://www.apple.com/newsroom/2023/02/apple-reports-first-quarter-results/",
    "https://www.apple.com/newsroom/2023/05/apple-reports-second-quarter-results/",
    "https://www.apple.com/newsroom/2023/08/apple-reports-third-quarter-results/",
    "https://www.apple.com/newsroom/2023/11/apple-reports-fourth-quarter-results/",
]


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta={}; self.ld=[]; self.active=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="meta":
            name=a.get("property",a.get("name",""))
            if name in ["article:published_time","article:modified_time","datePublished","dateModified","og:title"]:
                self.meta[name]=a.get("content","")
        if tag=="script" and a.get("type")=="application/ld+json":
            self.active=True
    def handle_endtag(self,tag):
        if tag=="script": self.active=False
    def handle_data(self,data):
        if self.active:
            try:
                self.ld.append(json.loads(data))
            except json.JSONDecodeError:
                pass


def dates(node,out):
    if isinstance(node,dict):
        for k,v in node.items():
            if k in {"datePublished","dateModified"} and isinstance(v,str): out.setdefault(k,[]).append(v)
            elif isinstance(v,(dict,list)): dates(v,out)
    elif isinstance(node,list):
        for v in node: dates(v,out)


def main():
    p=argparse.ArgumentParser(); p.add_argument("--root",required=True); p.add_argument("--out",required=True)
    a=p.parse_args(); root=Path(a.root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    evidence=[]
    for url in URLS:
        row={"url":url,"retrieved_utc":datetime.now(ZoneInfo("UTC")).isoformat()}
        try:
            with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (research metadata verification)"}),timeout=25) as r:
                payload=r.read(); row["http_status"]=r.status; row["resolved_url"]=r.url
            parser=Metadata(); parser.feed(payload.decode("utf-8",errors="replace"))
            row["document_sha256"]=hashlib.sha256(payload).hexdigest()
            row["metadata"]=parser.meta; extracted={}; dates(parser.ld,extracted); row["jsonld_dates"]=extracted
        except Exception as e:
            row["error_type"]=type(e).__name__
        evidence.append(row)
    # Match public publisher evidence to existing SCC calendar via historical company identity.
    events=pd.read_parquet(root/"derived/p1_concentration_information/20260920/roster/private_2023_top8_earnings_release_group_candidates.parquet",columns=["permco","anndats","anntims"])
    names=pd.read_parquet(root/"raw/crsp_dsenames_full.parquet",columns=["permco","comnam","namedt","nameendt"])
    names=names[names.comnam.str.upper().eq("APPLE INC")].copy()
    names["namedt"]=pd.to_datetime(names.namedt); names["nameendt"]=pd.to_datetime(names.nameendt)
    e=events.merge(names,on="permco",how="inner"); e["anndats"]=pd.to_datetime(e.anndats)
    e=e[(e.namedt<=e.anndats)&(e.nameendt>=e.anndats)].drop_duplicates(["permco","anndats","anntims"])
    comparable=0; exact=0; deltas=[]
    for row in evidence:
        ds=set(row.get("jsonld_dates",{}).get("datePublished",[]))
        if row.get("metadata",{}).get("article:published_time"):
            ds.add(row["metadata"]["article:published_time"])
        if len(ds)!=1: continue
        try:
            t=pd.Timestamp(next(iter(ds)))
            if t.tzinfo is None: continue
            ny=t.tz_convert("America/New_York")
        except (ValueError,TypeError): continue
        matches=e[e.anndats.dt.date==ny.date()]
        if len(matches)!=1: continue
        rec=matches.iloc[0]
        nominal=pd.Timestamp(f"{rec.anndats.date()} {rec.anntims}").tz_localize("America/New_York")
        delta=(nominal-ny).total_seconds(); deltas.append(delta); comparable+=1; exact+=int(delta==0)
    summary={"public_pages":len(URLS),"http_success_pages":sum(r.get("http_status")==200 for r in evidence),
      "public_issuer":"Apple Inc.","matching_source_groups":len(e),"comparable_public_timestamps":comparable,
      "same_second_count":exact,"absolute_difference_seconds_max":max(map(abs,deltas)) if deltas else None,
      "clock_accepted_for_purchase":False,"earliest_public_accuracy_bound":"UNKNOWN",
      "limitation":"Publisher webpage timestamps do not alone prove first dissemination, second-level accuracy, or absence of subsequent metadata edits.",
      "financial_values_parsed_or_returned":False,"public_evidence":evidence}
    (out/"PUBLIC_CLOCK_PROBE.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!="public_evidence"},indent=2))


if __name__=="__main__": main()
