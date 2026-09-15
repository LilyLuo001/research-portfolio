"""Diagnostic comparison, not a release-eligibility or estimator amendment."""
import csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
O=Path(__file__).resolve().parent
NY=ZoneInfo('America/New_York')
data=json.loads((O/'public_timestamp_candidates.json').read_text())
roles={r['date']:r for r in json.loads((O/'merck_metadata_roles.json').read_text())}
def aware(text):
    if 'T' not in text or ':' not in text:raise ValueError('date-only')
    dt=datetime.fromisoformat(text.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('timezone-absent')
    return dt.astimezone(NY)
def article_clock(nodes):
    vals={n['datePublished'] for n in nodes if n['object_type']=='NewsArticle'}
    if len(vals)!=1:raise ValueError('ambiguous article timestamps')
    return aware(next(iter(vals)))

# Golden parser fixtures: failures are intentional, not silent timezone guesses.
tests={}
tests['summer_offset']=aware('2021-09-13T20:05:00Z').hour==16
tests['winter_offset']=aware('2021-12-09T21:05:00Z').hour==16
tests['article_not_page']=article_clock([dict(object_type='WebPage',datePublished='2020-07-31T06:45:00+00:00'),dict(object_type='NewsArticle',datePublished='2020-07-31T06:45:00-04:00')]).hour==6
for label,value in [('reject_date_only','2022-01-27Z'),('reject_naive','2021-05-10T17:47:00')]:
    try:aware(value);tests[label]=False
    except ValueError:tests[label]=True
try:
    article_clock([dict(object_type='NewsArticle',datePublished='2020-07-31T06:45:00+00:00'),dict(object_type='NewsArticle',datePublished='2020-07-31T06:45:00-04:00')]);tests['reject_conflicting_articles']=False
except ValueError:tests['reject_conflicting_articles']=True
assert all(tests.values())

out=[]
for r in data:
    label='NO_TIME_ON_CHECKED_SOURCE';dt=None
    if r['ticker']=='ORCL':
        values={n['value'] for n in r['clock_candidates'] if n['field'] in {'date','jsonld.datePublished'}}
        assert len(values)==1
        dt=aware(next(iter(values)));label='PRNEWSWIRE_PUBLICATION_METADATA'
    elif r['ticker']=='MRK':
        dt=article_clock(roles[r['date']]['publication_nodes']);label='ISSUER_NEWSARTICLE_NOT_WEBPAGE_METADATA'
    elif r['ticker']=='REI':
        visible=[n['value'] for n in r['clock_candidates'] if n['field']=='visible:time']
        assert visible==['May 10, 2021 5:47pm EDT']
        dt=datetime.strptime(visible[0],'%B %d, %Y %I:%M%p EDT').replace(tzinfo=NY)
        assert dt.utcoffset().total_seconds()==-14400
        label='ISSUER_VISIBLE_EDT_PUBLICATION_TIME'
    elif r['ticker']=='REGI':
        external=json.loads((O/'regi_wire_timestamp.json').read_text())
        assert external['timestamps']==['March 05, 2019 16:05 ET']
        dt=datetime.strptime(external['timestamps'][0],'%B %d, %Y %H:%M ET').replace(tzinfo=NY)
        label='ORIGINAL_WIRE_VISIBLE_ET_TIME'
    row=dict(ticker=r['ticker'],date=r['date'],wave_id=r['wave_id'],source_url=r['url'],source_basis=label,source_clock_string=r['source_clock_string'],public_eastern_clock=dt.isoformat() if dt else '',public_minus_source_seconds='',status='UNKNOWN_TIME')
    if dt:
        source=datetime.fromisoformat(r['date']+'T'+r['source_clock_string']).replace(tzinfo=NY)
        difference=(dt-source).total_seconds()
        row.update(public_minus_source_seconds=int(difference),status='DISPLAYED_MINUTE_MATCH' if difference==0 else 'DISPLAYED_TIME_DISAGREEMENT')
    out.append(row)
with (O/'clock_comparison.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
receipt=dict(status='BOUNDED_PUBLIC_CLOCK_COMPARISON_NOT_GLOBAL_CERTIFICATION',locators=len(out),time_bearing=sum(r['status']!='UNKNOWN_TIME' for r in out),displayed_minute_matches=sum(r['status']=='DISPLAYED_MINUTE_MATCH' for r in out),disagreements=sum(r['status']=='DISPLAYED_TIME_DISAGREEMENT' for r in out),unknown=sum(r['status']=='UNKNOWN_TIME' for r in out),parser_golden_tests=tests,first_public_release_certified=False,rounding_rule_certified=False,full_sample_timezone_certified=False,source_clock_values_modified=False,post_response_read=False,new_agent_dispatches=0,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(O/'comparison_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
print(json.dumps([dict(ticker=r['ticker'],date=r['date'],status=r['status'],difference_seconds=r['public_minus_source_seconds']) for r in out]))
