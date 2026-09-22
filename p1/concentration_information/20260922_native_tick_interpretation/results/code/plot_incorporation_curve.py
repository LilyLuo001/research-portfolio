#!/usr/bin/env python3
"""Plot public aggregate native-only RTH-minus-control incorporation estimates."""
import csv
from pathlib import Path
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((root/'WITHIN_BIN_RESPONSE_SUMMARY.csv').open()))
xorder=['50us','200us','1000us','10000us','1s','5s','60s']; xpos=list(range(len(xorder)))
fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
for ax,window in zip(axes,['AAPL_FEB','AAPL_AUG']):
    for venue, color in [('ARCX.PILLAR','#1f77b4'),('XNAS.ITCH','#d62728')]:
        for direction, style in [('B','-'),('S','--')]:
            d={r['horizon_label']:float(r['estimate']) for r in rows if r['comparison']=='RTH_MINUS_CONTROL_COMMON_5M' and r['window']==window and r['instrument']=='AAPL' and r['variant']=='NATIVE_ONLY' and r['weighting']=='EQUAL_BIN' and r['metric']=='signed_mid_change_bp' and r['dataset']==venue and r['direction']==direction}
            ax.plot(xpos,[d.get(h,float('nan')) for h in xorder],style,color=color,marker='o',label=f'{venue.split(".")[0]} {direction}')
    ax.axhline(0,color='0.5',lw=.8); ax.set_title(window.replace('_',' ')); ax.set_xticks(xpos,xorder,rotation=45); ax.set_xlabel('post-trade horizon')
axes[0].set_ylabel('RTH−control: paired−unpaired signed midpoint response (bp)')
axes[1].legend(fontsize=8,ncol=2)
fig.suptitle('Native aggressor side only; equal-weighted supported five-minute bins')
fig.tight_layout()
fig.savefig(root/'native_only_incorporation_curve.png',dpi=180)
