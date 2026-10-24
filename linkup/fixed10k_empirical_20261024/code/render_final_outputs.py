#!/usr/bin/env python3
"""Output-only repair: readable core figures and explicit T2 indicator labels."""
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

EXP=("general_work","occupation_task","industry_domain","tool_specific")
DUTY=("independent_judgment","client_ownership","people_supervision","training_mentoring","any")
FRAMES=("complete_fixed10k","original9282eligible")

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--public",required=True);a=ap.parse_args();p=Path(a.public)
 q1p=p/"T5_Q1_DIRECT_COMPARISONS.csv";q2p=p/"T5_Q2_DIRECT_COMPARISONS.csv";t2p=p/"T2_EXPERIENCE_CLAUSES.csv"
 q1=pd.read_csv(q1p);q2=pd.read_csv(q2p);t2=pd.read_csv(t2p)
 # Mechanical schema repair: the original output emitted the three alternative
 # indicators consecutively (generic, OR, AND) but omitted their names.
 t2["indicator"]=pd.NA
 t2.loc[(t2.family_attribute=="overlapping_ad_indicator")&t2.strength.notna(),"indicator"]="strength_"+t2.loc[(t2.family_attribute=="overlapping_ad_indicator")&t2.strength.notna(),"object"].astype(str)+"_"+t2.loc[(t2.family_attribute=="overlapping_ad_indicator")&t2.strength.notna(),"strength"].astype(str)
 t2.loc[(t2.family_attribute=="overlapping_ad_indicator")&(t2.years_relation=="numeric_present"),"indicator"]="numeric_years_"+t2.loc[(t2.family_attribute=="overlapping_ad_indicator")&(t2.years_relation=="numeric_present"),"object"].astype(str)
 t2.loc[(t2.family_attribute=="overlapping_ad_indicator")&(t2.conditionality=="conditional"),"indicator"]="conditional_"+t2.loc[(t2.family_attribute=="overlapping_ad_indicator")&(t2.conditionality=="conditional"),"object"].astype(str)
 alt=t2.index[(t2.family_attribute=="overlapping_ad_indicator")&t2.strength.isna()&t2.conditionality.isna()&t2.years_relation.isna()].tolist()
 groups={}
 for i in alt:groups.setdefault((t2.at[i,"frame"],t2.at[i,"domain"],t2.at[i,"object"]),[]).append(i)
 for key,ix in groups.items():
  if len(ix)!=3:raise RuntimeError(f"alternative indicator triplet malformed: {key} {len(ix)}")
  obj=key[2]
  for i,name,rel in zip(ix,(f"alternative_branch_{obj}",f"alternative_or_branch_{obj}",f"alternative_and_branch_{obj}"),("ANY","OR","AND")):
   t2.at[i,"indicator"]=name;t2.at[i,"alternative_relation"]=rel
 t2out=p/"T2_EXPERIENCE_CLAUSES_INTERPRETABLE.csv";t2.to_csv(t2out,index=False)
 colors={FRAMES[0]:"#1768AC",FRAMES[1]:"#D1495B"};labels={FRAMES[0]:"complete 10k",FRAMES[1]:"original eligible 9,282"}
 # FIG1: four frozen experience outcomes only, two offset frame series.
 z=q1[(q1.row_type=="difference")&(q1.scope=="equal_0.25_major_standardization")&q1.measure.isin(["experience_"+x for x in EXP])]
 fig,ax=plt.subplots(figsize=(9,4.8));base=np.arange(len(EXP));off={FRAMES[0]:-.12,FRAMES[1]:.12}
 for frame in FRAMES:
  d=z[z.frame==frame].set_index("measure").loc[["experience_"+x for x in EXP]]
  y=base+off[frame];v=d.point.to_numpy();lo=d.lower.to_numpy();hi=d.upper.to_numpy()
  ax.errorbar(v,y,xerr=[v-lo,hi-v],fmt="o",capsize=4,color=colors[frame],label=labels[frame])
 ax.axvline(0,color="black",lw=.8);ax.set_yticks(base,["General work","Occupation task","Industry domain","Tool specific"]);ax.set_xlabel("GenAI minus traditional-software rate\n(point and recorded-field-unknown bounds; not confidence intervals)");ax.legend(frameon=False);fig.tight_layout();f1=p/"figures"/"FIG1_Q1_CORE_RECORDED_UNKNOWN_BOUNDS_FINAL.png";fig.savefig(f1,dpi=200);plt.close(fig)
 # FIG2: explicit graduate and explicit no-experience domains as two panels.
 defs=("explicit_new_graduate","explicit_no_experience");titles=("Explicit new-graduate wording","Explicit no-experience wording")
 fig,axes=plt.subplots(1,2,figsize=(13,5),sharex=True,sharey=True);base=np.arange(len(DUTY))
 for ax,ed,title in zip(axes,defs,titles):
  z=q2[(q2.eligibility_definition==ed)&q2.measure.isin(["duty_"+x for x in DUTY])]
  for frame in FRAMES:
   d=z[z.frame==frame].set_index("measure").loc[["duty_"+x for x in DUTY]];y=base+off[frame];v=d.point.to_numpy();lo=d.lower.to_numpy();hi=d.upper.to_numpy()
   ax.errorbar(v,y,xerr=[v-lo,hi-v],fmt="o",capsize=4,color=colors[frame],label=labels[frame])
  ax.set_title(title);ax.set_xlim(0,1);ax.grid(axis="x",alpha=.2)
 axes[0].set_yticks(base,["Independent judgment","Client ownership","People supervision","Training / mentoring","Any strict current duty"]);axes[0].legend(frameon=False,loc="lower right")
 fig.supxlabel("Rate among eligibility-positive ads (point and recorded-duty-unknown bounds; not confidence intervals)",y=.02);fig.tight_layout(rect=(0,.05,1,1));f2=p/"figures"/"FIG2_Q2_CORE_RECORDED_UNKNOWN_BOUNDS_FINAL.png";fig.savefig(f2,dpi=200);plt.close(fig)
 receipt={"version":"fixed10k-empirical-output-render-v1","status":"pass","created_utc":datetime.now(timezone.utc).isoformat(),"scheduler":{"job_id":os.getenv("SLURM_JOB_ID"),"node":os.uname().nodename},"code_sha256":sha(Path(__file__)),"inputs":{x.name:sha(x) for x in (q1p,q2p,t2p)},"outputs":{x.name:sha(x) for x in (t2out,f1,f2)},"notes":["numeric analysis unchanged","original run receipt and figures unchanged","bounds are recorded-field-unknown ranges, not confidence intervals"]}
 (p/"FINAL_RENDER_RECEIPT_PUBLIC.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
