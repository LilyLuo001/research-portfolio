#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

DFA = "S000001015"
JPM = "S000003858"

def classify(s: set[str]) -> str:
    if s == {DFA}: return "DFA_ONLY"
    if s == {JPM}: return "JPM_ONLY"
    if s == {DFA, JPM}: return "BOTH_DFA_AND_JPM"
    if not s: return "NEITHER_IN_PINNED_PRE_AGGREGATION_SOURCE"
    return "UNKNOWN_UNEXPECTED_SERIES_SET"

def sha(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def run(sidecar: Path, mapping: Path, out: Path) -> None:
    s = pd.read_csv(sidecar, usecols=["candidate_id","wave_id_focal","provisional_tier","permno","other_wave_id","candidate_other_wave_pair_key"], dtype=str)
    s = s[s.other_wave_id == "W006"].copy()
    s["permno"] = pd.to_numeric(s.permno, errors="raise").astype(int)
    m = pd.read_csv(mapping, usecols=["permno","event_id","pre_series_id"], dtype={"permno":int,"event_id":str,"pre_series_id":str})
    by_permno = m.groupby("permno").pre_series_id.apply(lambda x:set(x)).to_dict()
    s["w006_pre_series_ids"] = s.permno.map(lambda x:";".join(sorted(by_permno.get(x,set()))))
    s["w006_attribution_status"] = s.permno.map(lambda x:classify(by_permno.get(x,set())))
    s["interpretation"] = "PRE_AGGREGATION_HOLDINGS_MEMBERSHIP_NOT_PACKAGE_APPROVAL_OR_COMPETING_EXCLUSION"
    s = s.sort_values(["wave_id_focal","provisional_tier","candidate_id"])
    assert len(s) == 12 and s.candidate_other_wave_pair_key.nunique() == 12
    assert not s.w006_attribution_status.eq("UNKNOWN_UNEXPECTED_SERIES_SET").any()
    protected = out / "protected_w006_candidate_series_attribution.csv"
    s.to_csv(protected,index=False)
    agg = s.groupby(["wave_id_focal","provisional_tier","w006_attribution_status"],as_index=False).agg(candidate_date_bucket_pairs=("candidate_other_wave_pair_key","nunique"))
    total = s.groupby("w006_attribution_status",as_index=False).agg(candidate_date_bucket_pairs=("candidate_other_wave_pair_key","nunique"))
    agg.to_csv(out/"w006_attribution_by_focal_wave_tier.csv",index=False)
    total.to_csv(out/"w006_attribution_total.csv",index=False)
    inv={"exact_12_pairs":len(s)==12,"all_pair_keys_unique":s.candidate_other_wave_pair_key.nunique()==12,"aggregate_sum_12":int(total.candidate_date_bucket_pairs.sum())==12,"no_unexpected_series_set":not s.w006_attribution_status.eq("UNKNOWN_UNEXPECTED_SERIES_SET").any()}
    receipt={"status":"W006_PRE_AGGREGATION_ATTRIBUTION_COMPLETE","counts":{"candidate_date_bucket_pairs":12,**{r.w006_attribution_status:int(r.candidate_date_bucket_pairs) for r in total.itertuples(index=False)}},"invariants":inv,"inputs_sha256":{"protected_candidate_other_wave_sidecar":sha(sidecar),"protected_w006_permno_series_projection":sha(mapping),"code":sha(Path(__file__))},"protected_output_sha256":sha(protected),"interpretation":"DATE_BUCKET_LINKAGE_ATTRIBUTED_TO_PREDECESSOR_HOLDINGS_SOURCE_ONLY_NOT_SHARED_PACKAGE_OR_SPONSOR","backend_telemetry":"NOT_OBSERVED"}
    (out/"w006_attribution_receipt.json").write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--sidecar',type=Path,required=True); ap.add_argument('--mapping',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True); run(a.sidecar,a.mapping,a.out)
