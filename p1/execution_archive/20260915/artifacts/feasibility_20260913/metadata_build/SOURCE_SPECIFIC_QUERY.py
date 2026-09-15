"""SCC free-path census with explicit metadata projections and aggregate outputs."""
import argparse, hashlib, math
from pathlib import Path
import pandas as pd

PINNED_INPUTS = {
    "p1/conv_exposure_free.parquet": "350c3c7aed6d1bf047a8970f4d5940f37f1ec89e012876cb0f081668a5d2b4e7",
    "p1/events_merged.csv": "758b2aeb5655ab48f50f53717e2c74d0b35f4a8fcae8df9f1f30b61b2023a821",
}

def verify_source_hashes(root):
    """Reject changed metadata versions before parsing or creating outputs."""
    for relative, expected in PINNED_INPUTS.items():
        with (root / relative).open("rb") as stream:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            actual = digest.hexdigest()
        if actual != expected:
            raise ValueError(f"Source hash mismatch for {relative}: expected {expected}, got {actual}")

def inv_cdf(x,p):
    a=sorted(float(v) for v in x if pd.notna(v) and float(v)>0)
    return a[math.ceil(p*len(a))-1] if a else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=Path("/usr3/graduate/qluo/dax-codex")); ap.add_argument("--out-dir",type=Path,required=True); a=ap.parse_args()
    verify_source_hashes(a.root)
    a.out_dir.mkdir(parents=True,exist_ok=True)
    d=pd.read_parquet(a.root/"p1/conv_exposure_free.parquet",columns=["cusip","wave_id","effective_date","pre_etf_ownership"])
    assert not d.duplicated(["cusip","wave_id"]).any(), "source must be unique stock-wave cells"
    e=pd.read_csv(a.root/"p1/events_merged.csv",usecols=["effective_date","announce_date","date_precision","effective_date_approx"],dtype=str).fillna("")
    if d[["cusip", "wave_id", "effective_date"]].isna().any().any() or d.duplicated(["cusip", "wave_id"]).any():
        raise ValueError("Missing or duplicate stock-wave keys")
    if d.groupby("wave_id").effective_date.nunique().ne(1).any():
        raise ValueError("Wave maps to more than one effective date")
    e=e.loc[e.effective_date.isin(d.effective_date.astype(str).unique())].copy()
    rows=[]
    for (w,date),g in d.groupby(["wave_id","effective_date"]):
        x=g.loc[g.pre_etf_ownership>0,"pre_etf_ownership"]; q1,q2=inv_cdf(x,1/3),inv_cdf(x,2/3)
        low=(x>0)&(x<=q1) if q1 is not None else pd.Series(False,index=x.index)
        high=x>q2 if q2 is not None else pd.Series(False,index=x.index)
        valid=q1 is not None and q1<q2 and low.any() and high.any()
        rows.append({"source":"free_parquet","wave_id":w,"effective_date":date,"stock_wave_cells":len(g),"positive_cells":len(x),"tier_rule_valid":int(valid),"low_cells":int(low.sum()) if valid else 0,"high_cells":int(high.sum()) if valid else 0})
    pd.DataFrame(rows).to_csv(a.out_dir/"free_source_inventory.csv",index=False)
    reuse=d.groupby("cusip").wave_id.nunique(); pd.DataFrame([{ "unique_stock_ids":len(reuse),"reused_stock_ids":int((reuse>1).sum()),"max_waves_per_stock":int(reuse.max())}]).to_csv(a.out_dir/"free_reuse_summary.csv",index=False)
    e=e.loc[e.effective_date.isin(set(d.effective_date))]
    multi=int(e.groupby("effective_date").announce_date.nunique().gt(1).sum())
    pd.DataFrame([{ "selected_event_rows":len(e),"selected_waves":e.effective_date.nunique(),"multi_announcement_dates":multi,"announcement_time_available":"","new_clock_eligibility":""}]).to_csv(a.out_dir/"free_chronology_summary.csv",index=False)
if __name__=="__main__": main()
