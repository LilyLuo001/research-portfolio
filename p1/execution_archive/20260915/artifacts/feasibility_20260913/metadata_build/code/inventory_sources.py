"""Portable, outcome-blind inventory for either named P1 exposure source."""
import argparse
import math
import pandas as pd

def inv_cdf(values, p):
    x = sorted(float(v) for v in values if pd.notna(v) and float(v) > 0)
    return x[math.ceil(p * len(x)) - 1] if x else None

def make_inventory(d, source, dose, ready=None):
    rows = []
    for (wave, date), g in d.groupby(["wave_id", "effective_date"], dropna=False):
        x = g.loc[g[dose] > 0, dose]; q1, q2 = inv_cdf(x, 1/3), inv_cdf(x, 2/3)
        low = (x > 0) & (x <= q1) if q1 is not None else pd.Series(False, index=x.index)
        high = x > q2 if q2 is not None else pd.Series(False, index=x.index)
        valid = q1 is not None and q1 < q2 and bool(low.any()) and bool(high.any())
        rows.append({"source":source,"wave_id":wave,"effective_date":date,"stock_wave_cells":len(g),"positive_cells":int((x>0).sum()),"tier_rule_valid":int(valid),"low_cells":int(low.sum()) if valid else 0,"high_cells":int(high.sum()) if valid else 0,"primary_ready_positive_cells":int(((g[dose]>0)&g[ready].fillna(False)).sum()) if ready else ""})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source",choices=["advanced","free"],required=True); ap.add_argument("--input",required=True); ap.add_argument("--out",required=True); ap.add_argument("--compare"); ap.add_argument("--comparison-out")
    a=ap.parse_args()
    if a.source=="advanced":
        d=pd.read_csv(a.input,usecols=["permno","wave_id","effective_date","exposure_ownership","primary_ready"]); out=make_inventory(d,"advanced_reconstructed_csv","exposure_ownership","primary_ready")
    else:
        d=pd.read_parquet(a.input,columns=["cusip","wave_id","effective_date","pre_etf_ownership"]); out=make_inventory(d,"free_parquet","pre_etf_ownership")
    out.to_csv(a.out,index=False)
    if a.compare:
        other=pd.read_csv(a.compare); x=out.merge(other,on="effective_date",how="outer",suffixes=("_this","_other"),indicator=True); x["validated_stock_membership_comparison"]="NOT_AVAILABLE: CUSIP/PERMNO bridge not supplied"; x.to_csv(a.comparison_out,index=False)
if __name__=="__main__": main()
