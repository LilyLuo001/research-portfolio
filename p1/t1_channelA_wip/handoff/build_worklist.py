#!/usr/bin/env python3
"""Parse ops/l1/P1-T1-events.yaml, dedupe items by identical excerpt text,
emit a worklist of unique excerpts (with member ids) for in-session extraction.
Deterministic prep only — extraction judgment stays with the channel-A model."""
import hashlib, json, re, sys, pathlib

ROOT = pathlib.Path("/home/user/research-portfolio")
SPEC = ROOT / "ops/l1/P1-T1-events.yaml"
OUTDIR = pathlib.Path(__file__).parent
HDR = re.compile(
    r"文件: (?P<accession>\S+) \(form (?P<form>[^,]+), filed (?P<filed>[\d-]+), "
    r"(?P<company>.*?)\)\nsource_url: (?P<url>\S+)\n节选:\n(?P<excerpt>.*)\Z",
    re.S)

import yaml
spec = yaml.safe_load(SPEC.read_text())
items = spec["items"]
print(f"items: {len(items)}", file=sys.stderr)

groups = {}   # excerpt-hash -> {"excerpt":..., "members":[...]}
bad = []
for it in items:
    m = HDR.search(it["prompt"])
    if not m:
        bad.append(it["id"]); continue
    d = m.groupdict()
    ex = d.pop("excerpt").strip()
    h = hashlib.sha1(ex.encode()).hexdigest()[:12]
    g = groups.setdefault(h, {"excerpt": ex, "members": []})
    g["members"].append({"id": it["id"], **{k: d[k].strip() for k in d}})
assert not bad, f"unparseable prompts: {bad}"
assert sum(len(g["members"]) for g in groups.values()) == len(items)

order = sorted(groups.items(),
               key=lambda kv: (kv[1]["members"][0]["company"],
                               kv[1]["members"][0]["filed"]))
with open(OUTDIR / "worklist.jsonl", "w") as f:
    for h, g in order:
        f.write(json.dumps({"h": h, "n": len(g["members"]),
                            "members": g["members"]},
                           ensure_ascii=False) + "\n")

# batches of unique excerpts for reading (cap ~45KB per batch file)
CAP = 45_000
batch, size, bn = [], 0, 0
def flush():
    global batch, size, bn
    if not batch: return
    bn += 1
    with open(OUTDIR / f"batch_{bn:03d}.txt", "w") as f:
        f.write("\n".join(batch))
    batch, size = [], 0
for h, g in order:
    m0 = g["members"][0]
    head = (f"=== {h} n={len(g['members'])} | {m0['company']} | form {m0['form']} "
            f"filed {m0['filed']} | acc {m0['id']}")
    others = [f"{m['form']}@{m['filed']}" for m in g["members"][1:]]
    if others:
        head += f" | dups: {', '.join(others[:6])}" + (" …" if len(others) > 6 else "")
    entry = head + " ===\n" + g["excerpt"]
    if size + len(entry) > CAP:
        flush()
    batch.append(entry); size += len(entry)
flush()
print(f"unique excerpts: {len(groups)}  batches: {bn}", file=sys.stderr)
tot = sum(len(g["excerpt"]) for g in groups.values())
print(f"total unique excerpt bytes: {tot}", file=sys.stderr)
