#!/usr/bin/env python3
"""The one manifest search. Builds the file index every later stage reads.

The instruction allows searching the manifest once; repeated ad-hoc greps are
how a project ends up silently reading a different copy of a table in stage 4
than it validated in stage 2. So this resolves each logical dataset the
exercise needs, records every candidate path it found, and leaves the choice
between overlapping copies to a later stage that compares them on real rows.

It deliberately does not pick a winner. Legacy CRSP, CIZ-style rescue files,
and maximal/rescue duplicates can differ in schema, in date field names, and in
whether a return column is a price return or a total return. Choosing between
them from filenames would be exactly the mistake the archive manual warns about.
"""
import sys

import pandas as pd

import ppw

# Logical dataset -> substrings that identify candidate files. Kept deliberately
# broad: over-collecting candidates is recoverable, missing a copy is not.
WANTED = {
    "crsp_daily_stock_legacy":   ["crsp_dsf", "crsp.dsf", "_dsf_"],
    "crsp_daily_stock_ciz":      ["newcrsp", "a_stock_dsf", "dsf_v2"],
    "crsp_daily_index":          ["dsi"],
    "crsp_monthly_stock":        ["msf"],
    "crsp_distributions":        ["dsedist"],
    "crsp_delist":               ["dsedelist"],
    "crsp_shares":               ["dseshares"],
    "crsp_fund_header":          ["fund_hdr", "fund_summary", "fund_header"],
    "crsp_holdings":             ["holdings"],
    "ibes_actuals":              ["actu", "act_epsus", "actu_epsus"],
    "ibes_summary":              ["statsum"],
    "ibes_detail":               ["detu"],
    "ibes_idsum":                ["idsum"],
    "crsp_ibes_link":            ["ibcrsp", "crsp_ibes"],
    "ccm_link":                  ["ccmxpf", "lnkhist", "ccm_link"],
    "fama_french":               ["fama", "_ff_", "factors_daily"],
    "index_data":                ["idx", "index_"],
    "midas":                     ["midas"],
    "crsp_taq_link_legacy":      ["tclink", "crsp_taq"],
}


def main():
    idx = pd.concat([ppw.load_manifest(), ppw.scan_near_taq()], ignore_index=True)
    ppw.OUT.mkdir(parents=True, exist_ok=True)
    idx.to_csv(ppw.INDEX, sep="\t", index=False)

    print(f"  index rows: {len(idx):,}  "
          f"(baseline {int((idx.source == 'baseline_manifest').sum()):,} + "
          f"near_taq {int((idx.source == 'near_taq_scan').sum()):,})")
    print(f"  total size: {idx.bytes.sum() / 1024**3:.3f} GiB\n")

    low = idx.path.str.lower()
    rows = []
    print("=" * 96)
    print(f"{'logical dataset':<28}{'files':>7}{'GiB':>9}  distinct raw trees")
    print("=" * 96)
    for name, keys in WANTED.items():
        hit = idx[low.apply(lambda p: any(k.lower() in p for k in keys))]
        trees = sorted({p.split("/")[1] if p.startswith("raw/") and "/" in p[4:]
                        else p.split("/")[0] for p in hit.path})
        print(f"{name:<28}{len(hit):>7}{hit.bytes.sum()/1024**3:>9.3f}  "
              f"{', '.join(trees[:6]) if trees else '-'}")
        for r in hit.itertuples(index=False):
            rows.append({"logical": name, "path": r.path, "bytes": r.bytes,
                         "mib": round(r.mib, 3), "source": r.source})
    print("=" * 96)

    cand = pd.DataFrame(rows)
    cand.to_csv(ppw.OUT / "s7_candidates.tsv", sep="\t", index=False)

    multi = cand.groupby("path").logical.nunique()
    amb = multi[multi > 1]
    print(f"\n  {len(amb)} files matched more than one logical dataset "
          f"(keyword overlap, resolved later on real rows, not here)")

    ppw.provenance("s7_01_manifest_search", [ppw.MANIFEST],
                   {"index_rows": int(len(idx)), "candidate_rows": int(len(cand)),
                    "near_taq_files": int((idx.source == "near_taq_scan").sum())})
    print(f"\n  written: {ppw.INDEX.name}, s7_candidates.tsv")
    print("  no source selected yet; selection happens in s7_02 on sampled rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
