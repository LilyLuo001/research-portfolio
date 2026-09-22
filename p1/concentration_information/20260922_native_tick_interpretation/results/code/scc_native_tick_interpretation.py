#!/usr/bin/env python3
"""SCC-only DBN aggregation for the 2026-09-22 native-tick interpretation.

Writes fine five-minute cells only to /scratch.  The --export directory receives
only window/cross-window aggregates; no DBN rows, timestamps, or BBO paths leave SCC.
"""
from __future__ import annotations
import argparse, csv, glob, json, math
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import databento as db
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE

NS=1_000_000_000; US=1_000
ROOT=Path('/scratch/qluo/native_tick_pilot_20260922')
BACK=((-1200,-1000),(1000,1200)); HORIZONS=(50*US,200*US,1000*US,10_000*US,NS,5*NS,60*NS)
METRICS=('effective_spread_bp','signed_mid_change_bp','realized_spread_bp','pre_quoted_spread_bp','pre_bid_size','pre_ask_size','pre_displayed_depth','trade_size','buy_share','age_since_valid_bbo_message_ms','age_since_actual_bbo_change_ms')

def val(x): return str(getattr(x,'value',x))
def meta(path):
    n=path.name.removesuffix('_mbp1.dbn.zst')
    if n.endswith('_XNAS_ITCH'): return n[:-10], 'XNAS.ITCH'
    if n.endswith('_ARCX_PILLAR'): return n[:-12], 'ARCX.PILLAR'
    raise ValueError(path)
def bbo(r):
    q=r.levels[0]; b,a,bs,az=map(int,(q.bid_px,q.ask_px,q.bid_sz,q.ask_sz))
    if b==UNDEF_PRICE or a==UNDEF_PRICE or bs==UNDEF_ORDER_SIZE or az==UNDEF_ORDER_SIZE or min(b,a,bs,az)<=0 or a<b: return None
    return b/1e9,a/1e9,bs,az
def mappings(st):
    return {int(x['symbol']):raw.upper().strip() for raw,spans in st.metadata.mappings.items() for x in spans}
def bounds():
    req=json.loads((ROOT/'REQUEST_MANIFEST.json').read_text()); o={}
    for r in req:
        o[Path(r['path']).name]=(int(np.datetime64(r['start'].removesuffix('Z'),'ns').astype(np.int64))+120*NS,int(np.datetime64(r['end'].removesuffix('Z'),'ns').astype(np.int64))-65*NS)
    return o
def write(path,rows):
    if not rows: raise RuntimeError('empty '+str(path))
    fs=[]
    for r in rows:
        for k in r:
            if k not in fs: fs.append(k)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fs,lineterminator='\n'); w.writeheader(); w.writerows(rows)

def decode(path, start, end):
    st=db.DBNStore.from_file(path); mp=mappings(st); syms={x for x in mp.values() if x in {'AAPL','XOM','SPY'}}; stock='AAPL' if 'AAPL' in syms else 'XOM'
    raw={stock:[], 'SPY':[]}
    for i,r in enumerate(st):
        if not isinstance(r,MBP1Msg) or mp.get(int(r.instrument_id)) not in raw: continue
        s=mp[int(r.instrument_id)]; q=bbo(r); raw[s].append((int(r.ts_event),int(r.sequence),i,val(r.action),val(r.side),int(r.price)/1e9 if int(r.price)!=UNDEF_PRICE else math.nan,int(r.size),q))
    out={}
    for s, rows in raw.items():
        rows.sort(key=lambda z:(z[0],z[1],z[2])); last=None; last_msg=None; last_change=None; state_t=[]; state_b=[]; state_a=[]; state_msg=[]; state_change=[]
        t=[]; px=[]; size=[]; sign=[]; source=[]; prem=[]; pres=[]; pbs=[]; pas=[]
        for ts,seq,i,action,side,p,sz,q in rows:
            # Trade observes the strictly prior valid state; clear does not carry stale BBO.
            if action=='T':
                pm=(last[0]+last[1])/2 if last else math.nan; ps=(last[1]-last[0])/pm*1e4 if last else math.nan
                if side=='B': sg,so='B','NATIVE'
                elif side=='A': sg,so='S','NATIVE'
                elif math.isfinite(pm) and math.isfinite(p) and p!=pm: sg,so=('B' if p>pm else 'S'),'MIDPOINT'
                else: sg,so='U','UNKNOWN'
                if start<=ts<end: t.append(ts); px.append(p); size.append(sz); sign.append(sg); source.append(so); prem.append(pm); pres.append(ps); pbs.append(last[2] if last else math.nan); pas.append(last[3] if last else math.nan)
            if action=='R': last=None; last_msg=None; last_change=None
            elif q is not None:
                prior=last; last=q; last_msg=ts
                if q != prior: last_change=ts
            else:
                # An undefined/invalid BBO cannot legally carry the prior book forward.
                last=None; last_msg=None; last_change=None
            # append state after this message: permits a true prior/at-target endpoint lookup.
            state_t.append(ts); state_b.append(last[0] if last else math.nan); state_a.append(last[1] if last else math.nan); state_msg.append(last_msg if last_msg else -1); state_change.append(last_change if last_change else -1)
        out[s]={'times':np.array(t,dtype=np.int64),'price':np.array(px,float),'size':np.array(size,float),'sign':np.array(sign),'source':np.array(source),'prem':np.array(prem,float),'pres':np.array(pres,float),'pbs':np.array(pbs,float),'pas':np.array(pas,float),'st':np.array(state_t,dtype=np.int64),'sb':np.array(state_b,float),'sa':np.array(state_a,float),'sm':np.array(state_msg,dtype=np.int64),'sc':np.array(state_change,dtype=np.int64)}
    return stock,out

def npairs(a,b,lo,hi): return int(np.sum(np.searchsorted(b,a+hi,'left')-np.searchsorted(b,a+lo,'left')))
def has(a,b,lo,hi): return np.searchsorted(b,a+hi,'left')>np.searchsorted(b,a+lo,'left')
def has_reverse(spy,stock):
    """For a SPY centre, d=t_spy-t_stock in [-20,+20): stock in (spy-20, spy+20]."""
    return np.searchsorted(stock,spy+20*US,'right') > np.searchsorted(stock,spy-20*US,'right')
def activity(base, stock, spy):
    rows=[]
    cats={'ALL':np.ones(len(stock['times']),bool),'SAME_DIRECTION':np.zeros(len(stock['times']),bool),'OPPOSITE_DIRECTION':np.zeros(len(stock['times']),bool),'UNKNOWN_STOCK_OR_SPY':np.zeros(len(stock['times']),bool)}
    # all uses all pairs; directional categories enumerate eligible combinations.
    combos={'SAME_DIRECTION':(('B','B'),('S','S')),'OPPOSITE_DIRECTION':(('B','S'),('S','B'))}
    for name in cats:
        if name=='ALL': near=npairs(stock['times'],spy['times'],-20*US,20*US); bg=sum(npairs(stock['times'],spy['times'],l*US,h*US) for l,h in BACK); sm=has(stock['times'],spy['times'],-20*US,20*US); em=has(spy['times'],stock['times'],-20*US,20*US)
        elif name=='UNKNOWN_STOCK_OR_SPY':
            alln=npairs(stock['times'],spy['times'],-20*US,20*US); known=sum(npairs(stock['times'][stock['sign']==a],spy['times'][spy['sign']==b],-20*US,20*US) for a in 'BS' for b in 'BS'); near=alln-known; bg=math.nan; sm=em=np.zeros(0,bool)
            allbg=sum(npairs(stock['times'],spy['times'],l*US,h*US) for l,h in BACK); knownbg=sum(npairs(stock['times'][stock['sign']==a],spy['times'][spy['sign']==b],l*US,h*US) for a in 'BS' for b in 'BS' for l,h in BACK); bg=allbg-knownbg
        else:
            near=sum(npairs(stock['times'][stock['sign']==a],spy['times'][spy['sign']==b],-20*US,20*US) for a,b in combos[name]); bg=sum(npairs(stock['times'][stock['sign']==a],spy['times'][spy['sign']==b],l*US,h*US) for a,b in combos[name] for l,h in BACK); sm=em=np.zeros(0,bool)
        ex=near-.1*bg if math.isfinite(bg) else math.nan
        if name=='ALL': em=has_reverse(spy['times'],stock['times'])
        rows.append({**base,'row_type':'WINDOW','category':name,'near_pairs':near,'background_pairs':bg,'excess_pairs':ex,'excess_per_minute':ex/60 if math.isfinite(ex) else math.nan,'stock_trades':len(stock['times']),'spy_trades':len(spy['times']),'stock_dollar_volume':float(np.nansum(stock['price']*stock['size'])),'spy_dollar_volume':float(np.nansum(spy['price']*spy['size'])),'excess_per_1000_stock':1000*ex/len(stock['times']) if len(stock['times']) and math.isfinite(ex) else math.nan,'excess_per_1000_spy':1000*ex/len(spy['times']) if len(spy['times']) and math.isfinite(ex) else math.nan,'unique_stock_paired':int(sm.sum()) if name=='ALL' else math.nan,'unique_spy_paired':int(em.sum()) if name=='ALL' else math.nan,'unique_stock_paired_share':float(sm.mean()) if name=='ALL' and len(sm) else math.nan,'unique_spy_paired_share':float(em.mean()) if name=='ALL' and len(em) else math.nan,'pair_multiplicity_per_unique_stock':near/sm.sum() if name=='ALL' and sm.sum() else math.nan})
    return rows

def response_cells(base, symbol, src, tgt, src_is_stock):
    ans=[]
    for variant in ('NATIVE_ONLY','NATIVE_PLUS_MIDPOINT'):
      elig=np.isin(src['source'],['NATIVE'] if variant=='NATIVE_ONLY' else ['NATIVE','MIDPOINT'])
      pair=np.zeros(len(src['times']),bool)
      for sg in 'BS':
        tt=tgt['times'][(tgt['sign']==sg)&np.isin(tgt['source'],['NATIVE'] if variant=='NATIVE_ONLY' else ['NATIVE','MIDPOINT'])]
        ix=np.flatnonzero((src['sign']==sg)&elig); pair[ix]=has(src['times'][ix],tt,-20*US,20*US) if src_is_stock else has_reverse(src['times'][ix],tt)
      for hor in HORIZONS:
        pos=np.searchsorted(src['st'],src['times']+hor,'right')-1; valid=pos>=0; post=np.full(len(pos),np.nan); age_message=np.full(len(pos),np.nan); age_change=np.full(len(pos),np.nan); post[valid]=(src['sb'][pos[valid]]+src['sa'][pos[valid]])/2; age_message[valid]=(src['times'][valid]+hor-src['sm'][pos[valid]])/1e6; age_change[valid]=(src['times'][valid]+hor-src['sc'][pos[valid]])/1e6
        sn=np.where(src['sign']=='B',1.,np.where(src['sign']=='S',-1.,np.nan)); eff=2*sn*(src['price']-src['prem'])/src['prem']*1e4; mid=sn*(post-src['prem'])/src['prem']*1e4; rea=2*sn*(src['price']-post)/src['prem']*1e4
        for sg in 'BS':
          for label,pm in (('PAIRED',pair),('UNPAIRED',~pair)):
            bins=((src['times']//NS)%3600//300).astype(int)
            for bn in range(12):
              good=elig&(src['sign']==sg)&pm&np.isfinite(eff)&np.isfinite(mid)&np.isfinite(rea)&np.isfinite(age_message)&np.isfinite(age_change)
              m=good&(bins==bn); n=int(m.sum()); ans.append({**base,'instrument':symbol,'variant':variant,'horizon_ns':hor,'horizon_label':f'{hor/US:g}us' if hor<NS else f'{hor/NS:g}s','direction':sg,'pair_group':label,'bin_5m':bn,'n':n,'effective_spread_bp':float(np.mean(eff[m])) if n else math.nan,'signed_mid_change_bp':float(np.mean(mid[m])) if n else math.nan,'realized_spread_bp':float(np.mean(rea[m])) if n else math.nan,'pre_quoted_spread_bp':float(np.mean(src['pres'][m])) if n else math.nan,'pre_bid_size':float(np.mean(src['pbs'][m])) if n else math.nan,'pre_ask_size':float(np.mean(src['pas'][m])) if n else math.nan,'pre_displayed_depth':float(np.mean(src['pbs'][m]+src['pas'][m])) if n else math.nan,'trade_size':float(np.mean(src['size'][m])) if n else math.nan,'buy_share':float(sg=='B') if n else math.nan,'age_since_valid_bbo_message_ms':float(np.mean(age_message[m])) if n else math.nan,'age_since_actual_bbo_change_ms':float(np.mean(age_change[m])) if n else math.nan,'missing_endpoint_trades':int((elig&(src['sign']==sg)&pm&(bins==bn)&~np.isfinite(post)).sum())})
    return ans

def summarize(cells):
    by=defaultdict(list)
    for r in cells: by[(r['window'],r['dataset'],r['stock'],r['instrument'],r['variant'],r['horizon_ns'],r['horizon_label'],r['direction'],r['bin_5m'])].append(r)
    win=[]
    for k,rs in by.items():
      p=next(x for x in rs if x['pair_group']=='PAIRED'); u=next(x for x in rs if x['pair_group']=='UNPAIRED')
      if p['n'] and u['n']:
        for metric in METRICS: win.append({'comparison':'WITHIN_WINDOW_5M','window':k[0],'dataset':k[1],'stock':k[2],'instrument':k[3],'variant':k[4],'horizon_ns':k[5],'horizon_label':k[6],'direction':k[7],'bin_5m':k[8],'weighting':'EQUAL_BIN','metric':metric,'estimate':p[metric]-u[metric],'paired_n':p['n'],'unpaired_n':u['n'],'support_bins':1,'dropped_bins':0})
    # collapse bin cells (equal, plus paired-n sensitivity)
    group=defaultdict(list)
    for r in win: group[tuple(r[x] for x in ('comparison','window','dataset','stock','instrument','variant','horizon_ns','horizon_label','direction','weighting','metric'))].append(r)
    out=[]
    for k,rs in group.items():
      for wt in ('EQUAL_BIN','PAIRED_N_WEIGHTED'):
        ws=np.ones(len(rs)) if wt=='EQUAL_BIN' else np.array([x['paired_n'] for x in rs],float); est=float(np.average([x['estimate'] for x in rs],weights=ws)); d=dict(zip(('comparison','window','dataset','stock','instrument','variant','horizon_ns','horizon_label','direction','weighting','metric'),k)); d.update(weighting=wt,estimate=est,support_bins=len(rs),dropped_bins=12-len(rs),paired_n_sum=sum(x['paired_n'] for x in rs),unpaired_n_sum=sum(x['unpaired_n'] for x in rs),paired_n_min=min(x['paired_n'] for x in rs),paired_n_median=float(np.median([x['paired_n'] for x in rs])),paired_n_max=max(x['paired_n'] for x in rs)); out.append(d)
    # Matched RTH-control difference: only same clock-bin rows with support on both days.
    lookup={(r['window'],r['dataset'],r['instrument'],r['variant'],r['horizon_ns'],r['direction'],r['bin_5m'],r['metric']):r for r in win}
    cross=defaultdict(list)
    for key,r in lookup.items():
      w,ds,inst,var,hor,direction,bn,metric=key
      if not w.endswith('_RTH'): continue
      ckey=(w[:-4]+'_CTRL',ds,inst,var,hor,direction,bn,metric)
      if ckey in lookup: cross[(w[:-4],ds,inst,var,hor,r['horizon_label'],direction,metric)].append((r,lookup[ckey]))
    emitted_cross=set()
    for k,rs in cross.items():
      for wt in ('EQUAL_BIN','PAIRED_N_WEIGHTED'):
        ws=np.ones(len(rs)) if wt=='EQUAL_BIN' else np.array([a['paired_n']+b['paired_n'] for a,b in rs],float)
        out.append({'comparison':'RTH_MINUS_CONTROL_COMMON_5M','window':k[0],'dataset':k[1],'stock':('AAPL' if k[0].startswith('AAPL') else 'XOM'),'instrument':k[2],'variant':k[3],'horizon_ns':k[4],'horizon_label':k[5],'direction':k[6],'weighting':wt,'metric':k[7],'estimate':float(np.average([a['estimate']-b['estimate'] for a,b in rs],weights=ws)),'support_bins':len(rs),'dropped_bins':12-len(rs),'rth_paired_n_sum':sum(a['paired_n'] for a,b in rs),'rth_unpaired_n_sum':sum(a['unpaired_n'] for a,b in rs),'control_paired_n_sum':sum(b['paired_n'] for a,b in rs),'control_unpaired_n_sum':sum(b['unpaired_n'] for a,b in rs),'rth_paired_n_min':min(a['paired_n'] for a,b in rs),'rth_paired_n_median':float(np.median([a['paired_n'] for a,b in rs])),'rth_paired_n_max':max(a['paired_n'] for a,b in rs),'control_paired_n_min':min(b['paired_n'] for a,b in rs),'control_paired_n_median':float(np.median([b['paired_n'] for a,b in rs])),'control_paired_n_max':max(b['paired_n'] for a,b in rs)})
        emitted_cross.add((k,wt))
    # XOM is low-support: preserve every requested comparison explicitly when no common bin survives.
    for ds in ('ARCX.PILLAR','XNAS.ITCH'):
      for inst in ('XOM','SPY'):
       for var in ('NATIVE_ONLY','NATIVE_PLUS_MIDPOINT'):
        for hor in HORIZONS:
         label=f'{hor/US:g}us' if hor<NS else f'{hor/NS:g}s'
         for direction in 'BS':
          for metric in METRICS:
           k=('XOM_JAN',ds,inst,var,hor,label,direction,metric)
           for wt in ('EQUAL_BIN','PAIRED_N_WEIGHTED'):
            if (k,wt) not in emitted_cross:
             out.append({'comparison':'RTH_MINUS_CONTROL_COMMON_5M','window':'XOM_JAN','dataset':ds,'stock':'XOM','instrument':inst,'variant':var,'horizon_ns':hor,'horizon_label':label,'direction':direction,'weighting':wt,'metric':metric,'estimate':'','support_bins':0,'dropped_bins':12,'rth_paired_n_sum':'','rth_unpaired_n_sum':'','control_paired_n_sum':'','control_unpaired_n_sum':''})
    return out

def matched_activity(rows):
    by={(r['window'],r['dataset'],r['category']):r for r in rows}
    out=[]
    for (w,ds,cat),r in list(by.items()):
      if not w.endswith('_RTH'): continue
      c=by.get((w[:-4]+'_CTRL',ds,cat))
      if not c: continue
      er,ec,nr,nc=r['excess_pairs'],c['excess_pairs'],r['stock_trades'],c['stock_trades']
      out.append({'file':'AGGREGATE','window':w[:-4],'dataset':ds,'stock':r['stock'],'row_type':'MATCHED_RTH_MINUS_CONTROL','category':cat,'rth_near_pairs':r['near_pairs'],'control_near_pairs':c['near_pairs'],'near_pairs_difference':r['near_pairs']-c['near_pairs'],'rth_background_pairs':r['background_pairs'],'control_background_pairs':c['background_pairs'],'rth_excess_pairs':er,'control_excess_pairs':ec,'excess_pairs_difference':er-ec,'rth_stock_trades':nr,'control_stock_trades':nc,'rth_spy_trades':r['spy_trades'],'control_spy_trades':c['spy_trades'],'excess_per_1000_stock_difference':r['excess_per_1000_stock']-c['excess_per_1000_stock'],'excess_per_1000_spy_difference':r['excess_per_1000_spy']-c['excess_per_1000_spy'],'fixed_order_level_term_per_1000_stock':1000*(er-ec)/nc if nc else math.nan,'fixed_order_activity_term_per_1000_stock':1000*er*(1/nr-1/nc) if nr and nc else math.nan,'stock_dollar_volume_difference':r['stock_dollar_volume']-c['stock_dollar_volume'],'spy_dollar_volume_difference':r['spy_dollar_volume']-c['spy_dollar_volume']})
    return out

def main():
 p=argparse.ArgumentParser(); p.add_argument('--export',required=True); p.add_argument('--scratch-out',default=str(ROOT/'interpretation_20260922')); a=p.parse_args(); ex=Path(a.export); ex.mkdir(parents=True,exist_ok=True); sc=Path(a.scratch_out); sc.mkdir(parents=True,exist_ok=True)
 act=[]; dirs=[]; cells=[]; bd=bounds()
 for s in sorted(glob.glob(str(ROOT/'*_mbp1.dbn.zst'))):
  path=Path(s); window,dataset=meta(path); stock,x=decode(path,*bd[path.name]); base={'file':path.name,'window':window,'dataset':dataset,'stock':stock}; act+=activity(base,x[stock],x['SPY'])
  for sym in (stock,'SPY'):
   c=Counter(x[sym]['source']); dirs.append({**base,'instrument':sym,'trades':len(x[sym]['times']),'native_trades':c['NATIVE'],'midpoint_fallback_trades':c['MIDPOINT'],'unknown_trades':c['UNKNOWN'],'native_share':c['NATIVE']/len(x[sym]['times']) if len(x[sym]['times']) else math.nan})
  cells+=response_cells(base,stock,x[stock],x['SPY'],True); cells+=response_cells(base,'SPY',x['SPY'],x[stock],False); print(window,dataset,flush=True)
 act += matched_activity(act)
 write(sc/'WITHIN_BIN_FINE_SCC_ONLY.csv',cells); write(ex/'ACTIVITY_DECOMPOSITION.csv',act); write(ex/'DIRECTION_SOURCE_SUMMARY.csv',dirs); write(ex/'WITHIN_BIN_RESPONSE_SUMMARY.csv',summarize(cells)); (ex/'ENGINEERING_RECEIPT.json').write_text(json.dumps({'files':18,'raw_location':str(ROOT),'fine_cells_location':str(sc/'WITHIN_BIN_FINE_SCC_ONLY.csv'),'horizons_ns':HORIZONS,'status':'COMPUTED_ON_SCC'},indent=2)+'\n')
if __name__=='__main__': main()
