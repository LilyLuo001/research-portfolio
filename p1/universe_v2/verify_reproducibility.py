"""Check that the universe can be rebuilt from persistent inputs, and hash the result.

The /tmp purge destroyed a parser and every intermediate table, and the register
survived only because one snapshot happened to sit outside the purge path. This
file exists so that the same failure is detectable rather than discovered months
later: it asserts where the data lives, that every artifact carries provenance,
and that the census invariants still hold.

It checks three separable things, and reports them separately because they fail
for different reasons:

  location   no unique input, table or source may live only under a temp path
  provenance every derived artifact has a manifest line with a hash and lineage
  census     the counts a downstream consumer relies on are what they should be

A census difference is not automatically a failure. The pipeline is under active
correction, so an expected count is declared here with the reason it changed; an
undeclared difference is what fails.
"""
import hashlib
import json
import subprocess
import sys

import pandas as pd

import fetchlib
from paths import CACHE, MANIFEST, RAW

TEMP = ("/tmp", "/private/tmp", "/var/folders")

# Derived artifacts and what each is built from. Lineage is declared rather than
# inferred: a table's inputs are a fact about the code, not about the file.
LINEAGE = {
    "n14_index.csv": "raw/index/form_*.idx",
    "n14_mergers.csv": "n14_index.csv + raw/n14_headers/*.hdr.sgml",
    "n14_body_dates.csv": "raw/n14_bodies/*.html",
    "classification_ledger.csv": "n14_mergers.csv + ncen_tables.pkl",
    "events_master_v2_stage1.csv": "n14_mergers.csv + ncen_tables.pkl",
    "events_master_v2_stage2.csv": "events_master_v2_stage1.csv + n14_body_dates.csv",
    "ncen_cease_signal.csv": "events_master_v2_stage2.csv + ncen_tables.pkl",
    "events_master_v2_stage3.csv": ("ncen_cease_signal.csv + sup497_completions.csv"
                                    " + escalation_completions.csv"
                                    " + escalation_resolved.csv"
                                    " + recovered_verified_dates.csv"),
    "recovered_verified_dates.csv": "events_master_v2_stage3.csv + raw completion docs",
    "events_master_v2_stage3.prefold.csv": ("events_master_v2_stage3.csv as it stood"
                                            " before recovered days were folded in"),
    "events_master_v2_frozen.csv": ("events_master_v2_stage3.csv"
                                    " + date_conflict_audit.csv (gate)"),
    "wave_map_v2.csv": "events_master_v2_frozen.csv (verified_exact_day only)",
    "wave_membership_v2.csv": "events_master_v2_frozen.csv (verified_exact_day only)",
    "events_derived_v2.csv": "events_master_v2_stage3.csv",
    "fed_residual_cases.csv": "events_master_v2_stage3.csv + classification_ledger.csv",
    "pair_delta_audit.csv": ("events_master_v2_stage3.csv + snapshot stage3"
                             " + raw/n14_headers/*.hdr.sgml + ncen_tables.pkl"),
    "date_conflict_audit.csv": ("recovered_verified_dates.csv"
                                " + events_master_v2_stage3.csv"
                                " + submissions_flat.parquet + raw completion docs"),
    "attributed_completions.csv": "sup497/escalation completions + submissions_flat.parquet",
    "sup497_completions.csv": "raw/sup497/*.html",
    "escalation_completions.csv": "raw/escalation/*.html",
    "escalation_resolved.csv": "raw/escalation/*.html",
    "inplace_conversions.csv": "ncen_tables.pkl",
    "ncen_cease_signal.csv ": "events_master_v2_stage2.csv",
    "discovery_probe_candidates.csv": "ncen_tables.pkl",
    "discovery_probe_shortlist.csv": "discovery_probe_candidates.csv",
    "discovery_probe_triage.csv": "discovery_probe_shortlist.csv + raw/probe_triage/*.html",
    "fri_flat.pkl": "ncen_tables.pkl",
    "ncen_tables.pkl": "raw/ncen/*_ncen.zip (SEC DERA quarterly bulk)",
    "submissions_flat.parquet": "raw/submissions/CIK*.json (data.sec.gov, paginated)",
}

# What the census should say, and why it is that number rather than an earlier
# one. An undeclared change fails; a declared one is reported and passes.
EXPECT = {
    "structural_pairs": (247,
        "242 before the multi-target MERGER fix: a TARGET-DATA block holding two "
        "<SERIES> lost one predecessor, and gave the survivor the other fund's "
        "share classes. Expanding the pair across series recovered 5 events."),
    "completed": (156,
        "154 before the same fix; the 2 added predecessors are already-completed "
        "pairs, the other 3 are announced_future."),
}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rule(s):
    print("\n" + "=" * 74 + f"\n{s}\n" + "=" * 74)


def check_location(fail):
    rule("LOCATION")
    for name, p in (("cache", CACHE), ("raw inputs", RAW), ("manifest", MANIFEST)):
        bad = str(p).startswith(TEMP)
        print(f"  {'FAIL' if bad else 'ok  '}  {name:<12} {p}")
        if bad:
            fail.append(f"{name} is under a temp path")

    # source must be committed, not merely present on disk
    here = subprocess.run(["git", "status", "--porcelain", "."],
                          capture_output=True, text=True,
                          cwd=str(__file__.rsplit("/", 1)[0]))
    dirty = [l for l in here.stdout.splitlines() if l.strip()]
    print(f"  {'FAIL' if dirty else 'ok  '}  uncommitted pipeline source: {len(dirty)}")
    for d in dirty:
        print(f"          {d}")
    if dirty:
        fail.append(f"{len(dirty)} pipeline source files uncommitted")


def check_provenance(fail):
    rule("PROVENANCE")
    seen = set()
    if MANIFEST.exists():
        with open(MANIFEST) as fh:
            for line in fh:
                seen.add(json.loads(line)["path"])

    added = 0
    for name, lin in sorted(LINEAGE.items()):
        p = CACHE / name.strip()
        if not p.exists():
            continue
        if str(p) not in seen:
            fetchlib.record(p, kind="derived", parser="verify_reproducibility.py",
                            extra={"lineage": lin})
            added += 1
    print(f"  recorded {added} previously unhashed derived artifacts")

    missing = [p.name for p in sorted(CACHE.glob("*"))
               if p.is_file() and p.suffix in (".csv", ".parquet", ".pkl")
               and p.name not in LINEAGE]
    print(f"  {'FAIL' if missing else 'ok  '}  artifacts with no declared lineage: "
          f"{len(missing)}")
    for m in missing:
        print(f"          {m}")
    if missing:
        fail.append(f"{len(missing)} artifacts have no declared lineage")

    rule("FINAL ARTIFACT HASHES")
    for name in ["events_master_v2_stage3.csv", "events_derived_v2.csv",
                 "classification_ledger.csv", "recovered_verified_dates.csv"]:
        p = CACHE / name
        if p.exists():
            print(f"  {sha256(p)[:32]}  {p.stat().st_size:>10,d}  {name}")
        else:
            print(f"  {'-' * 32}  {'absent':>10}  {name}")


def check_census(fail):
    rule("CENSUS")
    ev = pd.read_csv(CACHE / "events_master_v2_stage3.csv")
    done = ev[ev.final_tier.str.startswith(("A_", "B_"), na=False)]
    got = {"structural_pairs": len(ev), "completed": len(done)}
    for k, n in got.items():
        want, why = EXPECT[k]
        ok = n == want
        print(f"  {'ok  ' if ok else 'FAIL'}  {k:<18} {n:>5d}  (expected {want})")
        if not ok:
            fail.append(f"{k} is {n}, expected {want}")
        print(f"          {why}")

    rule("COMPLETION STATUS")
    for k, v in ev.final_tier.value_counts().items():
        print(f"  {v:>5d}   {k}")
    print(f"  {'-' * 40}\n  {len(ev):>5d}   total")

    rule("TIMING CENSUS  (mutually exclusive, must sum to the completed count)")
    CLASSES = ["verified_exact_day", "proposed_exact_day_only", "month_only",
               "bounded_window", "year_only"]
    c = done.date_precision.value_counts()
    tot = 0
    for k in CLASSES:
        print(f"  {int(c.get(k, 0)):>5d}   {k}")
        tot += int(c.get(k, 0))
    other = {k: int(v) for k, v in c.items() if k not in CLASSES}
    print(f"  {'-' * 40}\n  {tot:>5d}   total")
    ok = tot == len(done) and not other
    print(f"  {'ok  ' if ok else 'FAIL'}  sums to the completed count ({len(done)})"
          + (f"; unclassified: {other}" if other else ""))
    if not ok:
        fail.append(f"timing census sums to {tot}, completed is {len(done)}")

    # a verified day must carry the filing that states it
    v = done[done.date_precision == "verified_exact_day"]
    bad = int((v.verified_effective_date.isna()
               | v.verified_date_source_accession.isna()).sum())
    print(f"  {'ok  ' if not bad else 'FAIL'}  verified days carrying source "
          f"accession: {len(v) - bad}/{len(v)}")
    if bad:
        fail.append(f"{bad} verified days lack a source accession")

    # and nothing weaker may populate the verified column
    leak = int((done.verified_effective_date.notna()
                & (done.date_precision != "verified_exact_day")).sum())
    print(f"  {'ok  ' if not leak else 'FAIL'}  weaker precisions leaking into "
          f"verified_effective_date: {leak}")
    if leak:
        fail.append(f"{leak} non-verified events carry a verified date")

    rule("ADVISER / REGISTRANT CENSUS")
    print(f"  {done.post_series_id.nunique():>5d}   successor ETFs")
    print(f"  {done.post_cik.nunique():>5d}   successor registrants")
    print(f"  {done.pre_cik.nunique():>5d}   predecessor registrants")
    if "adviser" in done.columns:
        a = done.adviser.dropna()
        print(f"  {a.nunique():>5d}   advisers ({len(a)}/{len(done)} mapped)")


def main():
    fail = []
    check_location(fail)
    check_provenance(fail)
    check_census(fail)

    rule("RESULT")
    if fail:
        print(f"  REPRODUCIBILITY = FAIL  ({len(fail)})")
        for f in fail:
            print(f"    - {f}")
    else:
        print("  REPRODUCIBILITY = PASS")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
