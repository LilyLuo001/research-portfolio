import json, sys, hashlib, pathlib
import pyarrow.parquet as pq
p = pathlib.Path(sys.argv[1])
f = pq.ParquetFile(p)
sch = f.schema_arrow
t = f.read()
out = {"path": str(p), "rows": t.num_rows, "n_columns": t.num_columns,
       "columns": [{"name": n, "type": str(sch.field(n).type)} for n in sch.names]}
import re
TIME = re.compile(r"(time|dur|hour|minute|hrs|min\b|effort|elapsed|speed|cost)", re.I)
out["time_like_columns"] = [n for n in sch.names if TIME.search(n)]
# non-text summaries only
summ = {}
for n in sch.names:
    col = t.column(n)
    ty = str(sch.field(n).type)
    d = {"nulls": col.null_count}
    if ty in ("int64", "double", "float", "int32"):
        py = [v for v in col.to_pylist() if v is not None]
        if py: d.update(min=min(py), max=max(py))
    elif ty == "string":
        py = [v for v in col.to_pylist() if v is not None]
        d["n_distinct"] = len(set(py))
        d["max_len"] = max((len(v) for v in py), default=0)
        if d["n_distinct"] <= 60 and d["max_len"] <= 120:
            d["values"] = sorted(set(py))
    summ[n] = d
out["column_summaries"] = summ
print(json.dumps(out, indent=1))
