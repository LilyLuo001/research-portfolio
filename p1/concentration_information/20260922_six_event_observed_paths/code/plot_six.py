import csv
from pathlib import Path
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((R/'PATHS.csv').open()))
keys=[('P1-2023-08-01','06:30_ET','XOM, 2023-01-31'),('P1-2023-08-03','06:00_ET','XOM, 2023-07-28 (06:00)'),('P1-2023-08-03','06:30_ET','XOM, 2023-07-28 (06:30)'),('P1-2023-06-02','05:55_ET','UNH, 2023-04-14'),('P1-2023-01-01','16:30_ET','AAPL, 2023-02-02'),('P1-2023-01-03','16:30_ET','AAPL, 2023-08-03'),('P1-2023-02-02','16:07_ET','MSFT availability notice, 2023-04-25')]
fig,axs=plt.subplots(2,4,figsize=(16,7),sharex=True,sharey=True)
for ax,(eid,anchor,title) in zip(axs.flat,keys):
 x=[r for r in rows if r['event_id']==eid and r['anchor']==anchor]
 if x:
  m=[int(r['minute_from_anchor']) for r in x]
  sb=[float(r['SPY_bid_index']) if r['SPY_bid_index'] else float('nan') for r in x];sa=[float(r['SPY_ask_index']) if r['SPY_ask_index'] else float('nan') for r in x]
  ib=[float(r['issuer_bid_index']) if r['issuer_bid_index'] else float('nan') for r in x];ia=[float(r['issuer_ask_index']) if r['issuer_ask_index'] else float('nan') for r in x]
  ax.fill_between(m,sb,sa,color='#3567a8',alpha=.16);ax.fill_between(m,ib,ia,color='#e6550d',alpha=.16)
  ax.plot(m,[float(r['SPY_mid_index']) if r['SPY_mid_index'] else None for r in x],label='SPY mid',color='#3567a8')
  ax.plot(m,[float(r['issuer_mid_index']) if r['issuer_mid_index'] else None for r in x],label=x[0]['stock']+' mid',color='#e6550d')
 else: ax.text(.5,.5,'No common issuer/ETF DBN\nwindow available',ha='center',va='center',transform=ax.transAxes)
 ax.axhline(100,color='.6',lw=.7);ax.axvline(0,color='.4',lw=.7);ax.set_title(title);ax.grid(axis='y',color='.9')
axs.flat[-1].axis('off');axs[0,0].legend(frameon=False);fig.supxlabel('Minutes from operational anchor');fig.supylabel('Midquote index (baseline −5 minutes = 100)');fig.suptitle('Six fixed events + July clock variant: XNAS.ITCH venue-specific BBO states',y=.98);fig.tight_layout();fig.savefig(R/'SIX_EVENT_PATHS.png',dpi=180)
