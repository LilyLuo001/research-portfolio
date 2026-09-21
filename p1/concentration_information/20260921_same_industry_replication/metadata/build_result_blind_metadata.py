#!/usr/bin/env python3
"""Build the H2 replication design without reading any outcome fields.

This SCC-only program deliberately projects CRSP 2023 as (permno, permco,
date) and I/B/E/S actuals as identity/date/timing metadata.  It never reads
RET, DLRET, PRC, quote, EPS value, or forecast columns.  Row-level products
remain below OUT/private; only aggregate-safe summaries are copied to Git.
"""
from __future__ import annotations

import hashlib, json
from collections import Counter
from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared')
OUT=ROOT/'derived/p1_concentration_information/20260921_same_industry_replication/metadata'
R=ROOT/'derived/p1_concentration_information/20260920/roster'
N=ROOT/'derived/p1_concentration_information/20260920_phase3/network_selection/results'
RAW=ROOT/'raw'
OFFSETS=(-28,-21,-14,14,21,28)
H2A,H2B=pd.Timestamp('2023-07-01'),pd.Timestamp('2023-12-31')
XOM=pd.Timestamp('2023-07-28')
CUTOFF=pd.Timestamp('2022-12-30')

def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dt(x): return pd.to_datetime(x,errors='coerce').dt.normalize()
def inside(d,a,b): return d.notna() & ((a.isna()| (a<=d)) & (b.isna() | (b>=d)))
def writej(p,x): p.write_text(json.dumps(x,indent=2,default=str)+'\n')

def main():
  OUT.mkdir(parents=True,exist_ok=True); private=OUT/'private'; private.mkdir(exist_ok=True)
  # Explicit projection boundary: no price/return/outcome columns below.
  trading=pd.read_parquet(RAW/'crsp_dsf_2023.parquet',columns=['permno','permco','date'])
  trading['date']=dt(trading['date']); tdates=sorted(trading.date.dropna().unique())
  tset=set(tdates)
  nxt={d:tdates[i+1] for i,d in enumerate(tdates[:-1])}
  names=pd.read_parquet(RAW/'crsp_dsenames_full.parquet',columns=['permno','permco','namedt','nameendt','ticker','siccd'])
  for c in ['namedt','nameendt']: names[c]=dt(names[c])
  # Avoid rescanning the entire historical-name table for every pair.
  name_groups={int(k):v[['namedt','nameendt','ticker','siccd']].copy()
               for k,v in names.groupby('permco',sort=False)}
  rel=pd.read_parquet(R/'private_2023_top8_earnings_release_group_candidates.parquet')
  rel['anndats']=dt(rel['anndats'])
  syms=pd.read_parquet(R/'private_2023_top8_release_security_historical_symbol_candidates.parquet')
  syms['anndats']=dt(syms['anndats'])
  pairs=pd.read_parquet(N/'private_pair_scores.parquet')
  pairs=pairs[pairs.variant.eq('PURE_D')].copy()
  recv=pd.read_parquet(N/'private_receiver_scores.parquet')
  recv=recv[recv.variant.eq('PURE_D') & recv.issuer_rank.between(9,500)].copy()
  if recv.receiver_permco.duplicated().any() or pairs.duplicated(['issuer_permco','receiver_permco']).any():
    raise RuntimeError('PURE_D receiver or pair keys are not unique')
  # actuals projection omits value; historical link prevents use of current symbol.
  actual=pd.read_parquet(RAW/'ibes_actuals_eps_2023.parquet',columns=['ticker','pends','measure','pdicity','anndats','anntims','actdats','acttims','usfirm'])
  actual['anndats']=dt(actual['anndats'])
  actual=actual[actual.anndats.notna() & actual.usfirm.eq(1) & actual.measure.str.upper().eq('EPS')].copy()
  link=pd.read_parquet(RAW/'crsp_ibes_link_full.parquet',columns=['ticker','permno','sdate','edate','score'])
  link['sdate']=dt(link['sdate']); link['edate']=dt(link['edate'])
  actual['_aid']=range(len(actual)); own=actual.merge(link,on='ticker',how='left')
  own=own[inside(own.anndats,own.sdate,own.edate)].merge(names[['permno','permco','namedt','nameendt']],on='permno',how='left')
  own=own[inside(own.anndats,own.namedt,own.nameendt)][['_aid','permco','anndats']].drop_duplicates()
  # issuer identity is date-valid name record; tied active identities stay unknown.
  def identity(permco,d):
    base=name_groups.get(int(permco))
    if base is None: return (np.nan,'HISTORICAL_SYMBOL_AMBIGUOUS')
    q=base[(base.namedt.isna() | (base.namedt<=d)) & (base.nameendt.isna() | (base.nameendt>=d))]
    sic=q.siccd.dropna().astype(int); sic2=sorted(set((sic//100).tolist()))
    symbol=sorted(set(q.ticker.dropna().astype(str)))
    return (sic2[0] if len(sic2)==1 else np.nan, symbol[0] if len(symbol)==1 else 'HISTORICAL_SYMBOL_AMBIGUOUS')
  rows=[]
  for _,x in rel.iterrows():
    d=x.anndats
    if not (H2A<=d<=H2B): continue
    start=next((z for z in tdates if z>=d),pd.NaT)
    sic2,symbol=identity(x.permco,CUTOFF)
    timing=str(x.anntims) if pd.notna(x.anntims) else 'UNKNOWN'
    reason=''
    if d==XOM: reason='EXCLUDE_PREVIOUSLY_EXPOSED_XOM_TECHNICAL_RESPONSE_DATE'
    elif start not in nxt or start>H2B: reason='EXCLUDE_NO_H2_TWO_SESSION_WINDOW'
    rows.append(dict(event_id=f"E{x.issuer_rank}_{d:%Y%m%d}",issuer_id=int(x.permco),issuer_symbol=symbol,historical_sic2=sic2,announcement_date=d,announcement_timing=timing,event_start=start,event_end=nxt.get(start,pd.NaT),exclusion_reason=reason,exposure_class='H2_DELIST_SOURCE_PROCESS_LOADED_NO_ANALYTIC_USE_NOT_PRISTINE'))
  ev=pd.DataFrame(rows).drop_duplicates('event_id').sort_values(['announcement_date','issuer_id']).reset_index(drop=True)
  # Eliminate adjacent distinct date blocks deterministically (earlier date survives); same-day issuers form a block.
  accepted_dates=[]
  for d in sorted(ev.loc[ev.exclusion_reason.eq(''),'event_start'].unique()):
    if any(d in {z,nxt.get(z)} or nxt.get(d) in {z,nxt.get(z)} for z in accepted_dates):
      ev.loc[(ev.event_start.eq(d)) & ev.exclusion_reason.eq(''),'exclusion_reason']='EXCLUDE_EVENT_WINDOW_OVERLAPS_EARLIER_DATE_BLOCK'
    else: accepted_dates.append(d)
  # Every known H2 top8 window, including excluded/exposed windows, blocks a control.
  all_reserved=set(ev.event_start.dropna())|set(ev.event_end.dropna())
  # Only the known 2023-07-28 technical-response window makes a retained
  # neighbouring event ineligible. Other excluded windows still reserve
  # controls but cannot cascade-remove the earlier chronological winner.
  xomrows=ev.loc[ev.announcement_date.eq(XOM)]
  exposed_windows=set(xomrows.event_start.dropna())|set(xomrows.event_end.dropna())
  retained=ev[ev.exclusion_reason.eq('')].copy()
  retained=retained[~retained.event_start.isin(exposed_windows)&~retained.event_end.isin(exposed_windows)].copy()
  reserved=all_reserved
  # Named macro coverage only; flags do not choose events, and are not exhaustive.
  macro=json.loads((Path(__file__).resolve().parents[5]/'p1/concentration_information/20260921_empirical_decision/public_macro_calendar.json').read_text()) if False else None
  # The calendar is embedded solely as labels so SCC does not depend on laptop paths.
  macro_dates={'CPI':{'2023-07-12','2023-08-10','2023-09-13','2023-10-12','2023-11-14','2023-12-12'},'EMPLOYMENT_SITUATION':{'2023-07-07','2023-08-04','2023-09-01','2023-10-06','2023-11-03','2023-12-08'},'FOMC_STATEMENT':{'2023-07-26','2023-09-20','2023-11-01','2023-12-13'}}
  used=set(reserved); controls=[]; keep_events=[]; selected_by_date={}
  # Date blocks chronological; within date issuer IDs are separate outcome units but share controls.
  for d in sorted(retained.event_start.unique()):
    before=set(used)
    candidates=[]
    for off in OFFSETS:
      c=d+pd.Timedelta(days=off)
      if c in tset and c in nxt and H2A<=c<=H2B and H2A<=nxt[c]<=H2B:
        # candidate lexical key implements |offset|, past-before-future, date ordering.
        candidates.append((abs(off),0 if off<0 else 1,c,off,nxt[c]))
    candidates.sort()
    selected=[]
    for _,_,c,off,cend in candidates:
      if c in used or cend in used: continue
      # Own-news: inclusive preceding trading date through end date; this is
      # deliberately conservative for date-only timing metadata.
      prev=tdates[tdates.index(c)-1] if tdates.index(c)>0 else c
      block=retained[retained.event_start.eq(d)]
      receivers=set(pairs[pairs.issuer_permco.isin(block.issuer_id)].receiver_permco)
      bad=set(own[(own.anndats>=prev)&(own.anndats<=cend)].permco)
      # keep assignment at event block level; receiver flags materialized separately.
      selected.append((c,cend,off,prev,len(receivers),len(receivers&bad)))
      used.update({c,cend})
      # Continue beyond two nominal controls: some receiver/pair rows may be
      # own-news-ineligible, and eligibility requires two *receiver-specific*
      # controls.  This is results-blind and only uses announced dates.
      pairset=pairs[pairs.issuer_permco.isin(block.issuer_id)][['issuer_permco','receiver_permco']].drop_duplicates()
      okcounts=[]
      for _,p in pairset.iterrows():
        n=0
        for cc,ee,_,pp,_,_ in selected:
          if not ((own.permco.eq(p.receiver_permco))&(own.anndats.ge(pp))&(own.anndats.le(ee))).any(): n+=1
        okcounts.append(n)
      if okcounts and min(okcounts)>=2: break
    if len(selected)<2:
      used=before
      ev.loc[(ev.event_start.eq(d))&ev.exclusion_reason.eq(''),'exclusion_reason']='EXCLUDE_FEWER_THAN_TWO_GLOBAL_NONREUSED_H2_CONTROLS'
    else:
      keep_events.extend(retained[retained.event_start.eq(d)].event_id.tolist())
      selected_by_date[d]=selected
      for c,cend,off,prev,nr,nb in selected:
        for eid in retained[retained.event_start.eq(d)].event_id:
          controls.append(dict(event_id=eid,control_id=f'C{c:%Y%m%d}',control_start=c,control_end=cend,weekday_offset=off,calendar_same_weekday=True,own_news_interval_start=prev,own_news_interval_end=cend,receiver_candidates=nr,receiver_own_news_excluded=nb,conflict_reuse_status='GLOBAL_NONREUSED'))
  retained=ev[ev.event_id.isin(keep_events)].copy()
  ctl=pd.DataFrame(controls)
  # Date-valid receiver identity and design.  No missing pair is turned into zero.
  design=[]; receiver_controls=[]
  for _,e in retained.iterrows():
    pp=pairs[pairs.issuer_permco.eq(e.issuer_id)].merge(recv,left_on='receiver_permco',right_on='receiver_permco',how='inner')
    ep=tdates[tdates.index(e.event_start)-1] if tdates.index(e.event_start)>0 else e.event_start
    own_bad=set(own[(own.anndats>=ep)&(own.anndats<=e.event_end)].permco)
    for _,x in pp.iterrows():
      sic2,_=identity(x.receiver_permco,CUTOFF)
      valid_controls=[]
      for c,cend,off,prev,_,_ in selected_by_date[e.event_start]:
        bad=((own.permco.eq(x.receiver_permco))&(own.anndats.ge(prev))&(own.anndats.le(cend))).any()
        if not bad: valid_controls.append((c,cend,off,prev))
      eligible=(int(x.receiver_permco) not in own_bad and len(valid_controls)>=2 and pd.notna(sic2) and pd.notna(e.historical_sic2))
      if eligible:
        design.append(dict(event_id=e.event_id,block_id=f'B{e.event_start:%Y%m%d}',issuer_id=int(e.issuer_id),receiver_id=int(x.receiver_permco),pair_strength=x.pair_strength,same_sic2=bool(sic2==e.historical_sic2),log_size=np.log(x.company_market_cap) if x.company_market_cap>0 else np.nan,log_liquidity=np.log(x.avg_daily_dollar_volume) if x.avg_daily_dollar_volume>0 else np.nan,event_start=e.event_start,event_end=e.event_end,n_controls=len(valid_controls)))
        for c,cend,off,prev in valid_controls:
          receiver_controls.append(dict(event_id=e.event_id,receiver_id=int(x.receiver_permco),control_start=c,control_end=cend,weekday_offset=off,own_news_interval_start=prev,own_news_interval_end=cend))
  design=pd.DataFrame(design)
  if len(design) and design.duplicated(['event_id','receiver_id']).any():
    raise RuntimeError('final result-blind design has duplicate event/receiver keys')
  # Private row-level artifacts only.
  ev.to_csv(private/'event_candidates.csv',index=False); ctl.to_csv(private/'control_assignment_event_level.csv',index=False); pd.DataFrame(receiver_controls).to_parquet(private/'control_assignment.parquet',index=False); design.to_parquet(private/'receiver_event_design.parquet',index=False)
  # Aggregate support/attrition safe to publish; no IDs/dates/tickers.
  attr=[{'stage':'raw_h2_release_groups','count':int(len(rows))},{'stage':'after_initial_event_validity','count':int((ev.exclusion_reason=='').sum())},{'stage':'retained_after_global_control_assignment','count':int(len(retained))},{'stage':'event_date_blocks_retained','count':int(retained.event_start.nunique())},{'stage':'issuer_event_receiver_pairs_eligible','count':int(len(design))},{'stage':'same_sic2_pairs','count':int(design.same_sic2.sum())},{'stage':'outside_sic2_pairs','count':int((~design.same_sic2).sum())},{'stage':'receiver_event_control_rows','count':int(len(receiver_controls))},{'stage':'pairs_excluded_missing_baseline_sic','count':int(sum(pd.isna(identity(x.receiver_permco,CUTOFF)[0]) for _,x in pairs.iterrows()))}]
  pd.DataFrame(attr).to_csv(OUT/'SUPPORT_AND_ATTRITION.csv',index=False)
  # Calendar support graph: each date block is isolated under global date nonreuse; report components, never ESS.
  bydate=retained.groupby('event_start').event_id.nunique()
  cdf=pd.DataFrame(receiver_controls)
  control_dates=set(cdf.control_start)|set(cdf.control_end) if len(cdf) else set()
  event_dates=set(retained.event_start)|set(retained.event_end)
  reuse=int(cdf.groupby(['receiver_id','control_start','control_end']).size().gt(1).sum()) if len(cdf) else 0
  leave=[]
  for b,g in design.groupby('block_id'):
    remain=design.loc[design.block_id.ne(b),'pair_strength']
    leave.append({'omitted_block':b,'remaining_rows':int(len(remain)),'fixed_h1_scale_rank':int(pd.Series(np.log(remain)).rank().max()) if len(remain) else 0,'remaining_log_pair_strength_sd':float(np.log(remain).std(ddof=1)) if len(remain)>1 else None})
  diagnostics={'fixed_h1_log_pair_strength_mean':-7.120058696390034,'fixed_h1_log_pair_strength_sd':1.575275281258204,'main_columns':['intercept','same_sic2','fixed_H1_standardized_log_pair_strength','interaction','log_size','log_liquidity','event_fixed_effects'],'main_design_rank_metadata_only':int(np.linalg.matrix_rank(np.column_stack([np.ones(len(design)),design.same_sic2.astype(float),((np.log(design.pair_strength)+7.120058696390034)/1.575275281258204),design.same_sic2.astype(float)*((np.log(design.pair_strength)+7.120058696390034)/1.575275281258204),design.log_size.fillna(0),design.log_liquidity.fillna(0)]))) if len(design) else 0,'leave_one_block':leave,'max_equal_event_block_weight_share':float(design.groupby('block_id').size().max()/len(design)) if len(design) else None}
  writej(OUT/'DESIGN_MATRIX_DIAGNOSTICS.json',diagnostics)
  dep={'algorithm':'absolute offset; past before future; date ascending; chronological global greedy; reserve all known top8 H2 event dates first; prohibit any event/control trading-date intersection across date blocks','offsets_days':list(OFFSETS),'minimum_controls_per_receiver_event':2,'minimum_observed_receiver_controls':int(cdf.groupby(['event_id','receiver_id']).size().min()) if len(cdf) else 0,'all_event_and_control_response_dates_h2_only':True,'event_level_control_assignments':int(len(ctl)),'receiver_control_assignments':int(len(cdf)),'distinct_control_windows':int(ctl.control_id.nunique()) if len(ctl) else 0,'reused_receiver_control_keys':reuse,'event_control_date_intersections':len(event_dates&control_dates),'allocation_claim':'This is the predeclared deterministic greedy allocation, not a proof of global feasibility or optimality; exact result-blind feasibility check NOT_RUN because allocation retained support.','support_graph_components_by_date_count':[1]*int(len(bydate)),'components_are_not_effective_sample_size':True,'residual_dependence':['same receivers repeat across issuer-events','same issuer can appear more than once','common macro shocks beyond three named labels','calendar nonreuse does not establish shock independence'],'macro_coverage_limit':'CPI, Employment Situation, FOMC statement labels only; incomplete news calendar','event_timing_rule':'unknown timing treated conservatively; own-news predicate inclusively spans prior_trading_date <= own_anndats <= second_window_date','same_industry_support':{'pairs':int(design.same_sic2.sum()),'unique_receivers':int(design.loc[design.same_sic2,'receiver_id'].nunique()),'log_pair_strength_sd':float(np.log(design.loc[design.same_sic2,'pair_strength']).std(ddof=1)) if design.same_sic2.any() else None},'outside_industry_support':{'pairs':int((~design.same_sic2).sum()),'unique_receivers':int(design.loc[~design.same_sic2,'receiver_id'].nunique()),'log_pair_strength_sd':float(np.log(design.loc[~design.same_sic2,'pair_strength']).std(ddof=1)) if len(design) else None},'status':'SUPPORT_READY' if len(retained) else 'STOP_SUPPORT'}
  writej(OUT/'CONTROL_ASSIGNMENT_AND_DEPENDENCE_SUMMARY.json',dep)
  manifest={'result_blind':True,'prohibited_columns_not_read':['RET','DLRET','PRC','quote fields','EPS value','forecast fields'],'sources':[{'path':str(R/'private_2023_top8_earnings_release_group_candidates.parquet'),'purpose':'candidate issuer/date/timing metadata'},{'path':str(N/'private_pair_scores.parquet'),'purpose':'PURE_D positive pair strengths'},{'path':str(N/'private_receiver_scores.parquet'),'purpose':'baseline mcap/liquidity and receiver identities'},{'path':str(RAW/'crsp_dsf_2023.parquet'),'columns':['permno','permco','date'],'purpose':'trading-date presence only'},{'path':str(RAW/'crsp_dsenames_full.parquet'),'purpose':'historical identity and SIC2'},{'path':str(RAW/'ibes_actuals_eps_2023.parquet'),'columns':['ticker','pends','measure','pdicity','anndats','anntims','actdats','acttims','usfirm'],'purpose':'own-announcement date metadata only'},{'path':str(RAW/'crsp_ibes_link_full.parquet'),'purpose':'historical ticker/PERMNO linkage'}],'private_outputs':[str(private/'event_candidates.csv'),str(private/'control_assignment.parquet'),str(private/'receiver_event_design.parquet')],'sha256_inputs':{str(p):h(p) for p in [R/'private_2023_top8_earnings_release_group_candidates.parquet',N/'private_pair_scores.parquet',N/'private_receiver_scores.parquet']},'known_exposure':'452 H2 delisting rows were process-loaded in the prior stage but did not enter estimates, outputs, or selection; H2 is not a strictly pristine holdout. This program did not read delisting or return fields.'}
  writej(OUT/'SOURCE_MANIFEST.json',manifest)
  ledger={'scope':'bounded metadata-only review for 2023H2','classes':[{'class':'entered_existing_statistical_estimate','scope':'2023H1 daily outcomes only; excluded from this candidate pool'},{'class':'process_loaded_not_analytic_use','scope':'452 H2 delisting-source rows in prior full-year process; disclosed, no outcome values read by this program'},{'class':'metadata_only_this_stage','scope':'H2 event, identity, calendar, network and availability metadata'}],'strict_pristine_holdout':False,'new_outcome_fields_read':False,'excluded_previously_exposed_date':'2023-07-28 Exxon technical-response date'}
  writej(OUT/'EXPOSURE_LEDGER.json',ledger)
  print(json.dumps({'events_retained':len(retained),'date_blocks':int(retained.announcement_date.nunique()),'controls':int(len(ctl)),'pairs':len(design),'same_sic2':int(design.same_sic2.sum())}))
if __name__=='__main__': main()
