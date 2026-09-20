"""Tiny synthetic identity/date fixture; no licensed data or response values."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import pandas as pd


def main():
    with tempfile.TemporaryDirectory(prefix="p1_network_fixture_") as t:
        base=Path(t); root=base/"shared"; meta=base/"_migration_meta"
        hp=root/"raw/rescue_remaining/crsp_holdings_etf_2022_b0001/part_00001.parquet"
        cp=root/"raw/rescue_remaining/crsp_fund_hdr_hist_full_max/part_00001.parquet"
        hp.parent.mkdir(parents=True); cp.parent.mkdir(parents=True); meta.mkdir()
        pd.DataFrame([
          [1,"2022-09-30","2022-10-10",101], [1,"2022-09-30","2022-10-10",102],
          [1,"2022-12-20","2022-12-25",101], [1,"2022-12-20","2023-01-05",103],
          [2,"2022-12-20",None,101], [3,"2022-08-31","2022-09-15",101],
          [4,"2022-12-30","2022-12-30",102],
        ],columns=["crsp_portno","report_dt","eff_dt","permno"]).to_parquet(hp,index=False)
        pd.DataFrame([
          [1,11,"F","2020-01-01",None], [1,12,"","2020-01-01",None],
          [2,21,"F","2020-01-01",None],
        ],columns=["crsp_portno","crsp_fundno","et_flag","chgdt","chgenddt"]).to_parquet(cp,index=False)
        (meta/"FINAL_SCC_MANIFEST.tsv").write_text("\n".join(f"{p.stat().st_size}\t{p.relative_to(root)}" for p in [hp,cp])+"\n")
        out=base/"out"
        subprocess.run([sys.executable,str(Path(__file__).with_name("build_network_support.py")),"--root",str(root),"--out",str(out)],check=True,capture_output=True)
        s=json.loads((out/"NETWORK_SUPPORT.json").read_text())
        assert s["cohorts"]["economic_date_only"]["portfolios"]==3
        assert s["cohorts"]["vendor_observed_by_cutoff"]["portfolios"]==2
        v=pd.read_parquet(out/"vendor_observed_by_cutoff_membership.parquet")
        assert set(v.loc[v.crsp_portno==1,"permno"])=={101,102}, "Do not select partial newly available report"
        assert v.loc[v.crsp_portno==1,"classification"].eq("MIXED_RECORDED_CLASSES").all()
        assert v.loc[v.crsp_portno==4,"classification"].eq("UNKNOWN_HEADER").all()
        assert s["weighted_L"]=="NOT_RUN_UNVERIFIED_UNITS_DENOMINATOR_CLASS_ALLOCATION"
        print(json.dumps({"synthetic_tests":"PASS","checks":["string_dates_cast","120_day_boundary","complete_vendor_report_only","null_availability_excluded","mixed_class_not_pure_etf","missing_header_unknown","no_weighted_exposure_claim"]}))


if __name__=="__main__":
    main()
