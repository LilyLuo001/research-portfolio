#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

SRC = Path("/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/nport_crsp_security_crosswalk.csv")
OUT = Path(__file__).resolve().parent / "protected_w006_permno_series_projection.csv"

d = pd.read_csv(SRC, usecols=["wave_id", "event_id", "pre_series_id", "mapping_status", "permno"], dtype=str)
d = d[(d.wave_id == "W006") & (d.mapping_status == "exact_matched") & d.permno.notna()].copy()
d["permno"] = pd.to_numeric(d.permno, errors="raise").astype(int)
d = d[["permno", "event_id", "pre_series_id"]].drop_duplicates().sort_values(["permno", "pre_series_id"])
assert set(d.pre_series_id) == {"S000001015", "S000003858"}
d.to_csv(OUT, index=False)
print(len(d), OUT)
