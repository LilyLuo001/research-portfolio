#!/usr/bin/env python3
"""Build a fixed, outcome-independent P1 procurement manifest. No API calls."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import csv, json, hashlib
import pandas as pd
import exchange_calendars as xc

ROOT = Path(__file__).resolve().parent
NY = ZoneInfo('America/New_York')
CAL = xc.get_calendar('XNYS', start='2019-01-01', end='2024-01-10')
REPO = 'https://github.com/LilyLuo001/research-portfolio/blob/cb36417304b282cda5e38ede13d1af872ad9f346/'
E007_HASH='905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320'

def write_csv(name, rows):
    assert rows, name
    with (ROOT/name).open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def utc(day, clock):
    return datetime.fromisoformat(f'{day}T{clock}:00').replace(tzinfo=NY).astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def shift(day,n):
    s=pd.Timestamp(day)
    assert CAL.is_session(s), day
    for _ in range(abs(n)):
        s = CAL.next_session(s) if n>0 else CAL.previous_session(s)
    return s.strftime('%Y-%m-%d')

stocks=[
 ('JJSF','J & J Snack Foods Corp',10026,'466032109','W002','2021-04-30','Other-than-megacap calibration'),
 ('PLXS','Plexus Corp',10032,'729132100','W002','2021-04-30','Higher old-clock ownership than megacap examples'),
 ('MSFT','Microsoft Corp',10107,'594918104','W002','2021-04-30','Liquid large-cap comparison; not untreated'),
 ('ORCL','Oracle Corp',10104,'68389X105','W002','2021-04-30','Liquid large-cap comparison; not untreated'),
 ('SKYW','SkyWest Inc',10421,'830879102','W016','2022-12-30','Non-Dimensional cohort; earlier conversions may overlap'),
 ('AXL','American Axle & Manufacturing Holdings Inc',86547,'024061103','W016','2022-12-30','Pre-open earnings example; earlier conversions may overlap'),
 ('AROC','Archrock Inc',92245,'03957W106','W016','2022-12-30','Energy-services holding; earlier conversions may overlap'),
 ('BHE','Benchmark Electronics Inc',76224,'08160H101','W016','2022-12-30','Electronics-services holding; earlier conversions may overlap'),
]
stock_rows=[]
for t,n,p,c,w,d,r in stocks:
    stock_rows.append(dict(ticker=t,company=n,permno=p,cusip9_at_repository_snapshot=c,wave_id=w,
       holdings_asof_in_reviewed_crosswalk=d,procurement_membership='VERIFIED_IN_PRE_EFFECTIVE_PREDECESSOR_HOLDINGS',
       pre_announcement_membership='NOT_CERTIFIED',analysis_tier='NOT_ASSIGNED',pilot_role=r,
       repository_commit='cb36417304b282cda5e38ede13d1af872ad9f346',e007_sha256=E007_HASH,
       identity_source=REPO+'p1/exposure/nport_crsp_security_crosswalk.csv'))
write_csv('securities.csv',stock_rows)

cohorts=[dict(wave_id='W002',sponsor='Dimensional Fund Advisors LP',repository_effective_date='2021-06-11',
    public_etf_operation_date='2021-06-14',converted_etfs='DFAC;DFUS;DFAS;DFAT',
    predecessor='T.A. U.S. Core Equity 2; Tax-Managed U.S. Equity; Tax-Managed U.S. Small Cap; Tax-Managed U.S. Targeted Value',
    holding_series='S000016732;S000000972;S000000976;S000000977',
    public_source='https://www.dimensional.com/us-en/newsroom/dimensional-lists-four-new-etfs-following-the-industrys-largest-mutual-fund-to-etf-conversion',
    note='Repository effective date and ETF listing date are different clocks. Neither is the earliest announcement clock.'),
 dict(wave_id='W016',sponsor='Bridgeway Capital Management LLC',repository_effective_date='2023-03-10',
    public_etf_operation_date='2023-03-13',converted_etfs='BSVO',
    predecessor='Omni Tax-Managed Small-Cap Value Fund',holding_series='S000030751',
    public_source='https://bridgewayetfs.com/bsvo/',
    note='Issuer describes reorganization on March 13; repository records March 10. Preserve both, do not silently reconcile them.')]
write_csv('conversion_cohorts.csv',cohorts)

D={
'JJSF':[
 ('2019-07-29','https://www.sec.gov/Archives/edgar/data/785956/000143774919014814/ex_151579.htm','ISSUER_SEC_EXHIBIT'),
 ('2020-01-27','https://ca.marketscreener.com/quote/stock/J-J-SNACK-FOODS-CORP-9780/news/J-J-Snack-Foods-Reports-First-Quarter-Sales-and-Earnings-29897379/','ISSUER_GLOBENEWSWIRE_RELEASE_REPRINT'),
 ('2021-07-26','https://www.sec.gov/Archives/edgar/data/785956/000143774921017562/ex_266908.htm','ISSUER_SEC_EXHIBIT'),
 ('2021-11-15','https://www.globenewswire.com/news-release/2021/11/15/2334770/18519/en/j-j-snack-foods-fourth-quarter-net-sales-increase-28-driving-187-rise-in-net-earnings.html','ISSUER_WIRE')],
'PLXS':[
 ('2019-10-23','https://investor.plexus.com/news/news-details/2019/PLEXUS-ANNOUNCES-FISCAL-FOURTH-QUARTER-AND-FISCAL-YEAR-2019-FINANCIAL-RESULTS-10-23-2019/default.aspx','ISSUER_IR'),
 ('2020-01-22','https://investor.plexus.com/news/news-details/2020/PLEXUS-ANNOUNCES-FISCAL-FIRST-QUARTER-FINANCIAL-RESULTS-01-22-2020/default.aspx','ISSUER_IR'),
 ('2021-07-21','https://investor.plexus.com/news/news-details/2021/PLEXUS-ANNOUNCES-FISCAL-THIRD-QUARTER-FINANCIAL-RESULTS-07-21-2021/default.aspx','ISSUER_IR'),
 ('2021-10-27','https://investor.plexus.com/news/news-details/2021/PLEXUS-ANNOUNCES-FISCAL-FOURTH-QUARTER-AND-FISCAL-YEAR-2021-FINANCIAL-RESULTS-10-27-2021/default.aspx','ISSUER_IR')],
'MSFT':[
 ('2019-10-23','https://www.microsoft.com/en-us/investor/earnings/fy-2020-q1/press-release-webcast','ISSUER_IR'),
 ('2020-01-29','https://www.microsoft.com/en-us/Investor/earnings/FY-2020-Q2/press-release-webcast','ISSUER_IR'),
 ('2021-07-27','https://news.microsoft.com/source/2021/07/27/microsoft-cloud-strength-fuels-fourth-quarter-results-2/','ISSUER_RELEASE'),
 ('2021-10-26','https://news.microsoft.com/source/2021/10/26/microsoft-cloud-strength-drives-first-quarter-results-4/','ISSUER_RELEASE')],
'ORCL':[
 ('2019-09-11','https://investor.oracle.com/investor-news/news-details/2019/Q1-FY20-GAAP-EPS-Up-11-To-063-And-Non-GAAP-EPS-Up-14-To-081/default.aspx','ISSUER_IR'),
 ('2019-12-12','https://investor.oracle.com/investor-news/news-details/2019/Oracle-Sets-the-Date-for-its-Second-Quarter-Fiscal-Year-2020-Earnings-Announcement/default.aspx','ISSUER_SCHEDULE_DATE_CORROBORATED_BY_EARNINGS_HISTORY'),
 ('2021-09-13','https://investor.oracle.com/investor-news/news-details/2021/Oracle-Announces-Fiscal-2022-First-Quarter-Financial-Results/default.aspx','ISSUER_IR'),
 ('2021-12-09','https://investor.oracle.com/investor-news/news-details/2021/Oracle-Announces-Fiscal-2022-Second-Quarter-Financial-Results/default.aspx','ISSUER_IR')],
'SKYW':[
 ('2021-10-28','https://www.sec.gov/Archives/edgar/data/793733/000155837021013721/skyw-20211028xex99d1.htm','ISSUER_SEC_EXHIBIT'),
 ('2022-04-28','https://www.sec.gov/Archives/edgar/data/793733/000155837022006267/skyw-20220428xex99d1.htm','ISSUER_SEC_EXHIBIT'),
 ('2023-07-27','https://www.sec.gov/Archives/edgar/data/793733/000155837023012401/skyw-20230727xex99d1.htm','ISSUER_SEC_EXHIBIT'),
 ('2023-10-26','https://www.sec.gov/Archives/edgar/data/793733/000155837023016844/skyw-20231026xex99d1.htm','ISSUER_SEC_EXHIBIT')],
'AXL':[
 ('2021-11-05','https://www.aam.com/media/story/aam-reports-third-quarter-2021-financial-results','ISSUER_RELEASE'),
 ('2022-02-11','https://www.aam.com/media/story/aam-reports-fourth-quarter-and-full-year-2021-financial-results','ISSUER_RELEASE'),
 ('2023-08-04','https://www.aam.com/media/story/aam-reports-second-quarter-2023-financial-results','ISSUER_RELEASE'),
 ('2023-11-03','https://www.aam.com/media/story/aam-reports-third-quarter-2023-financial-results','ISSUER_RELEASE')],
'AROC':[
 ('2021-11-01','https://investors.archrock.com/news/news-details/2021/Archrock-Reports-Third-Quarter-2021-Results/default.aspx','ISSUER_IR'),
 ('2022-05-09','https://www.sec.gov/Archives/edgar/data/1389050/000138905022000016/aroc-20220509ex9919f9989.htm','ISSUER_SEC_EXHIBIT'),
 ('2023-07-31','https://investors.archrock.com/news/news-details/2023/Archrock-Reports-Second-Quarter-2023-Results-Increases-2023-Guidance-and-Updates-Capital-Allocation/default.aspx','ISSUER_IR'),
 ('2023-11-01','https://investors.archrock.com/news/news-details/2023/Archrock-Reports-Third-Quarter-2023-Results/default.aspx','ISSUER_IR')],
'BHE':[
 ('2021-10-27','https://www.sec.gov/Archives/edgar/data/863436/000095017021002381/bhe-ex99_1.htm','ISSUER_SEC_EXHIBIT'),
 ('2022-04-26','https://www.sec.gov/Archives/edgar/data/863436/000095017022006223/bhe-ex99_1.htm','ISSUER_SEC_EXHIBIT'),
 ('2023-07-31','https://ir.bench.com/news/news-details/2023/BENCHMARK-REPORTS-SECOND-QUARTER-2023-RESULTS/default.aspx','ISSUER_IR'),
 ('2023-10-25','https://ir.bench.com/news/news-details/2023/BENCHMARK-REPORTS-THIRD-QUARTER-2023-RESULTS/default.aspx','ISSUER_IR')],
}
# Prespecified balanced smaller order only if the complete order does not fit.
minimum_pre={'JJSF':'2020-01-27','PLXS':'2020-01-22','MSFT':'2019-10-23','ORCL':'2019-12-12',
             'SKYW':'2022-04-28','AXL':'2021-11-05','AROC':'2022-05-09','BHE':'2022-04-26'}
events=[]
for sr in stock_rows:
 for i,(date,url,kind) in enumerate(D[sr['ticker']]):
  focal='PRE_FOCAL' if i<2 else 'POST_FOCAL'
  events.append(dict(event_id=f"{sr['wave_id']}_{sr['ticker']}_{date.replace('-','')}",ticker=sr['ticker'],
   permno=sr['permno'],wave_id=sr['wave_id'],earnings_release_date=date,
   focal_conversion_position=focal,full32=True,
   minimum16=(date==minimum_pre[sr['ticker']] or i==2),
   source_kind=kind,release_date_source=url,exact_release_clock_status='NOT_CERTIFIED_BY_THIS_ORDER',
   analysis_access='DEVELOPMENT_PRE_FOCAL_ONLY' if i<2 else 'ARCHIVE_ONLY_NO_RESPONSE_ANALYSIS',
   other_conversion_cleanliness='NOT_CERTIFIED',
   note='Fixed procurement selection. PRE_FOCAL is not a certified never-treated/control status.'))
write_csv('earnings_events.csv',events)

legs=[('D_MINUS_1',-1,'15:40','16:10'),('D_RELEASE',0,'04:00','20:00'),
      ('D_PLUS_1',1,'04:00','20:00'),('D_PLUS_2',2,'15:40','16:10')]

def build_requests(selected, role, prefix):
 intervals={}
 rawmap=[]
 for e in selected:
  syms=[e['ticker'],'SPY'] if role=='CORE' else ['IWM'] + ([] if e['focal_conversion_position']=='PRE_FOCAL' else ['DFAC' if e['wave_id']=='W002' else 'BSVO'])
  for leg,off,a,b in legs:
   date=shift(e['earnings_release_date'],off)
   for sym in syms:
    key=(sym,date)
    intervals.setdefault(key,[]).append((a,b,e['event_id'],leg,e['analysis_access']))
    rawmap.append((e['event_id'],sym,date,a,b,leg))
 out=[]; lookup={}
 for (sym,date),ints in sorted(intervals.items(),key=lambda x:(x[0][1],x[0][0])):
  ints=sorted(ints)
  merged=[]
  for a,b,e,leg,access in ints:
   if merged and a<=merged[-1][1]:
    x=merged[-1]; x[1]=max(x[1],b); x[2].add(e);x[3].add(access)
   else: merged.append([a,b,{e},{access}])
  for a,b,es,acc in merged:
   rid=f'{prefix}_{len(out)+1:04d}'
   out.append(dict(request_id=rid,bundle=role,dataset='XNAS.ITCH',schema='bbo-1s',symbols=sym,
      stype_in='raw_symbol',start=utc(date,a),end=utc(date,b),local_date=date,
      local_start=a,local_end=b,timezone='America/New_York',
      event_ids=';'.join(sorted(es)),analysis_access='ARCHIVE_ONLY_NO_RESPONSE_ANALYSIS' if any('ARCHIVE_ONLY' in t for t in acc) else 'DEVELOPMENT_PRE_FOCAL_ONLY'))
   lookup[(sym,date,a,b)]=rid
 mapping=[]
 for e,s,d,a,b,l in rawmap:
  matches=[r for r in out if r['symbols']==s and r['local_date']==d and r['local_start']<=a and r['local_end']>=b]
  assert len(matches)==1,(e,s,d,l)
  mapping.append(dict(event_id=e,symbol=s,leg=l,local_date=d,required_start_local=a,required_end_local=b,request_id=matches[0]['request_id']))
 return out,mapping
core,mapping=build_requests(events,'CORE','C32')
mini,minmap=build_requests([e for e in events if e['minimum16']],'CORE','C16')
extra,emap=build_requests(events,'EXTRA_ETFS','EX')
write_csv('core32_requests.csv',core);write_csv('core32_event_request_map.csv',mapping)
write_csv('core16_budget_reduction_requests.csv',mini);write_csv('core16_event_request_map.csv',minmap)
write_csv('extra_etf_requests.csv',extra);write_csv('extra_event_request_map.csv',emap)
validation=[]
for t,date,a,b in [('PLXS','2020-01-22','15:30','18:00'),('MSFT','2019-10-23','15:30','18:00'),
                    ('AXL','2021-11-05','06:00','10:30'),('BHE','2022-04-26','15:30','18:00')]:
 for dataset,schema,bundle in [('XNAS.ITCH','mbp-1','QUOTE_UPDATE_VALIDATION'),('ARCX.PILLAR','bbo-1s','SECOND_VENUE_VALIDATION')]:
  for sym in [t,'SPY']:
   validation.append(dict(request_id=f'V_{len(validation)+1:03d}',bundle=bundle,dataset=dataset,schema=schema,
     symbols=sym,stype_in='raw_symbol',start=utc(date,a),end=utc(date,b),
     local_date=date,local_start=a,local_end=b,timezone='America/New_York',
     event_ids=f'{t}_{date}',analysis_access='DEVELOPMENT_PRE_FOCAL_ONLY'))
write_csv('validation_requests.csv',validation)

# Validate windows, identity, uniqueness and separation from continuous history.
assert len(events)==32 and len({e['ticker'] for e in events})==8
assert sum(e['minimum16'] for e in events)==16
for rows in [core,mini,extra,validation]:
 keys=[]
 for r in rows:
  a=datetime.fromisoformat(r['start'].replace('Z','+00:00'));b=datetime.fromisoformat(r['end'].replace('Z','+00:00'))
  assert a<b and (b-a).total_seconds()<=16*3600
  assert a.astimezone(NY).strftime('%Y-%m-%d %H:%M')==f"{r['local_date']} {r['local_start']}"
  keys.append((r['dataset'],r['schema'],r['symbols'],r['start'],r['end']))
 assert len(keys)==len(set(keys))
assert utc('2021-11-05','04:00').endswith('08:00:00Z')
assert utc('2021-11-08','04:00').endswith('09:00:00Z')
summary=dict(order_date='2026-09-14',purpose='P1_CONVERSION_MATCHED_QUOTATION_DEVELOPMENT',
    full_events=len(events),minimum_events=16,stocks=8,conversion_waves=['W002','W016'],
    core_symbols=sorted({r['symbols'] for r in core}),optional_symbols=['IWM','DFAC','BSVO'],
    core32_atomic_requests=len(core),core16_atomic_requests=len(mini),extra_atomic_requests=len(extra),validation_atomic_requests=len(validation),
    earliest_requested_date=min(r['local_date'] for r in core),latest_requested_date=max(r['local_date'] for r in core),
    core32_distinct_dates=len(set(r['local_date'] for r in core)),
    core32_symbol_hours=sum((datetime.fromisoformat(r['end'].replace('Z','+00:00'))-datetime.fromisoformat(r['start'].replace('Z','+00:00'))).total_seconds()/3600 for r in core),
    estimated_cost_status='NOT_QUOTED_ACCOUNT_REQUIRED',market_data_downloaded=False,
    planning_limit_usd=100,hard_total_limit_usd=125,reserve_usd=25,
    calendar_package_version=xc.__version__,calendar='XNYS; selected requested days checked for regular closes',
    limitations=['single_venue_core_not_NBBO','pre_effective_membership_not_pre_announcement_eligibility',
                 'pre_focal_does_not_mean_never_treated','two_waves_not_empirical_power',
                 'release_dates_supported_but_intraday_release_clocks_not_certified'])
for day in set(r['local_date'] for r in core):
 close=CAL.session_close(pd.Timestamp(day)).tz_convert('America/New_York')
 assert close.strftime('%H:%M')=='16:00',f'Early close requires correction {day}'
(ROOT/'order_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
