"""Read-only inventory of the pinned O*NET zip. Reports layout; infers nothing."""
import csv, hashlib, io, json, pathlib, re, sys, zipfile
from collections import Counter

ZIP = pathlib.Path(sys.argv[1])
ID_LIKE = re.compile(r"(id|code|soc|element|title|type)", re.I)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def delim(header_line):
    return "\t" if header_line.count("\t") >= header_line.count(",") else ","


tables = []
with zipfile.ZipFile(ZIP) as z:
    names = [n for n in z.namelist() if not n.endswith("/")]
    for name in sorted(names):
        with z.open(name) as fh:
            raw = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
            try:
                first = raw.readline()
            except Exception as e:
                tables.append({"file": name, "error": str(e)})
                continue
            if not first.strip():
                tables.append({"file": name, "error": "empty"})
                continue
            d = delim(first)
            cols = next(csv.reader([first], delimiter=d))
            cols = [c.strip() for c in cols]
            rdr = csv.DictReader(raw, fieldnames=cols, delimiter=d)
            n = 0
            distinct = {c: set() for c in cols if ID_LIKE.search(c)}
            scales = Counter()
            for row in rdr:
                n += 1
                for c in distinct:
                    v = row.get(c)
                    if v:
                        distinct[c].add(v)
                if "Scale ID" in row and row.get("Scale ID"):
                    scales[row["Scale ID"]] += 1
            tables.append({
                "file": name,
                "delimiter": "tab" if d == "\t" else "comma",
                "columns": cols,
                "rows": n,
                "distinct": {c: len(v) for c, v in sorted(distinct.items())},
                "scale_ids": dict(sorted(scales.items())) if scales else None,
            })

print(json.dumps({"zip": str(ZIP), "zip_sha256": sha(ZIP),
                  "n_members": len(names), "tables": tables},
                 indent=2, sort_keys=True))
