"""Read-only SCC audit. Reads only inventories, schemas, and existing metadata.

Run through ssh stdin; emit aggregates only. No financial-value source is opened.
"""
import csv, hashlib, json, re
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

ROOT = Path('/projectnb/econdept/qluo/P1_Refraction_WRDS')
MIRROR = ROOT / 'WRDS_MIRROR_20260902'
SHARED = MIRROR / 'p1_refraction_wrds_shared'
METADATA = ROOT / 'p1_roster_earnings_20260913/ibes_metadata_projection_v2/ibes_announcement_metadata.csv'
EXPECTED = '97a3c35c1f59013047924b89859df67ff361327a61b7bec0a28bdf3412c562cb'
SEEDS = {'JJSF':'46603210','PLXS':'72913210','MSFT':'59491810','ORCL':'68389X10',
         'SKYW':'83087910','AXL':'02406110','AROC':'03957W10','BHE':'08160H10'}
PUBLIC_DATES = {
 'JJSF':['2019-07-29','2020-01-27','2021-07-26','2021-11-15'],
 'PLXS':['2019-10-23','2020-01-22','2021-07-21','2021-10-27'],
 'MSFT':['2019-10-23','2020-01-29','2021-07-27','2021-10-26'],
 'ORCL':['2019-09-11','2019-12-12','2021-09-13','2021-12-09'],
 'SKYW':['2021-10-28','2022-04-28','2023-07-27','2023-10-26'],
 'AXL':['2021-11-05','2022-02-11','2023-08-04','2023-11-03'],
 'AROC':['2021-11-01','2022-05-09','2023-07-31','2023-11-01'],
 'BHE':['2021-10-27','2022-04-26','2023-07-31','2023-10-25']}

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()

def main():
 assert digest(METADATA)==EXPECTED, 'Pinned metadata changed'
 allowed={'ticker','cusip','pends','pdicity','anndats','anntims','actdats','acttims','source_partition'}
 by_symbol={s:[] for s in SEEDS}
 total=0
 with METADATA.open(newline='') as f:
  reader=csv.DictReader(f)
  assert set(reader.fieldnames)<=allowed, 'Unexpected metadata column'
  for row in reader:
   total+=1
   for symbol,cusip in SEEDS.items():
    if row['cusip'].strip().upper()==cusip: by_symbol[symbol].append(row)
 summaries=[]
 for symbol,rows in by_symbol.items():
  hits=[r for r in rows if r['anndats'][:10] in PUBLIC_DATES[symbol]]
  dates={r['anndats'][:10] for r in hits}
  summaries.append({'symbol':symbol,'matching_source_rows_all_dates':len(rows),
   'public_order_dates':4,'order_dates_with_source_match':len(dates),
   'source_rows_on_order_dates':len(hits),'periodicity_on_order_dates':dict(Counter(r['pdicity'] for r in hits)),
   'accounting_period_keys_on_order_dates':len({(r['pends'],r['pdicity']) for r in hits}),
   'date_clock_keys_on_order_dates':len({(r['anndats'],r['anntims']) for r in hits}),
   'unmatched_public_order_dates':[d for d in PUBLIC_DATES[symbol] if d not in dates],
   'unmatched_dates_adjacent_day_source_counts':{d:sum(r['anndats'][:10] in {
     (datetime.strptime(d,'%Y-%m-%d')+timedelta(days=offset)).strftime('%Y-%m-%d') for offset in [-1,1]} for r in rows)
     for d in PUBLIC_DATES[symbol] if d not in dates},
   'parseable_clock_rows_on_order_dates':sum(bool(re.fullmatch(r'\d{2}:\d{2}:\d{2}(\.\d+)?',r['anntims'].strip())) for r in hits),
   'event_date_link_certification':'NOT_TESTED_BY_THIS_CUSIP_MATCH',
   'timezone_and_session':'UNKNOWN_NOT_INFERRED_FROM_CLOCK_STRING'})
 manifest=MIRROR/'_migration_meta/FINAL_SCC_MANIFEST.tsv'
 paths=[]
 with manifest.open() as f:
  for line in f:
   parts=line.rstrip('\n').split('\t',1)
   if len(parts)==2: paths.append(parts[1])
 patterns={'nport':r'nport|n-port','actuals':r'ibes_actuals_eps_20(19|20|21|22|23|24)\.parquet$',
  'forecast_detail':r'ibes_detu_eps_20(19|20|21|22|23|24)\.parquet$',
  'daily_stock':r'crsp_dsf_20(19|20|21|22|23|24)\.parquet$',
  'shares_history':r'crsp_dseshares_20(19|20|21|22|23|24)\.parquet$',
  'exchange_calendars':r'metaexchangecalendar.*\.parquet$'}
 inventory={k:[p for p in paths if re.search(pattern,p,re.I)] for k,pattern in patterns.items()}
 schemas={}
 for name in ['schema__ibes__actu_epsus.csv','schema__ibes__detu_epsus.csv','schema__crsp__dseshares.csv']:
  p=SHARED/'meta'/name
  if p.exists():
   with p.open() as f: schemas[name]={'sha256':digest(p),'fields':list(csv.DictReader(f))}
 prior=ROOT/'p1_roster_earnings_20260913/event_calendar_v1'
 receipts={}
 for version in ['run','run_v2']:
  p=prior/version/'event_calendar_aggregate_receipt.json'
  if p.exists(): receipts[version]={'sha256':digest(p),'aggregate':json.loads(p.read_text())}
 print(json.dumps({'status':'EXECUTED_METADATA_ONLY','source_rows':total,'metadata_sha256':EXPECTED,
  'seed_scope':'FIXED_EIGHT_PROCUREMENT_CUSIPS_NOT_FINAL_ANALYSIS_POPULATION',
  'per_stock':summaries,'inventory_manifest_sha256':digest(manifest),'inventory_hits':inventory,
  'schemas':schemas,'prior_event_receipts':receipts,'raw_financial_sources_opened':False,
  'remote_inputs_modified':False,'post_quote_records_decoded':False},indent=2))

if __name__=='__main__': main()
