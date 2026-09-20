"""Join cached identity projections to the SCC-private issuer roster, no raw rescan."""
import argparse
import hashlib
import json
from pathlib import Path
import duckdb


def q(p):
    return "'" + str(p).replace("'", "''") + "'"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--network", required=True)
    p.add_argument("--roster", required=True)
    a = p.parse_args()
    root = Path(a.network)
    c = duckdb.connect()
    c.execute("SET threads=1")
    c.execute("SET memory_limit='1GB'")
    c.execute(f"CREATE TEMP TABLE roster AS SELECT DISTINCT permno,permco,issuer_rank FROM read_parquet({q(a.roster)})")
    assert c.execute("SELECT count(*)=count(DISTINCT permno) FROM roster").fetchone()[0]
    out = {"stage":"PRE2023_IDENTITY_COHOLDING_SUPPORT", "weighted_L":"NOT_RUN", "roster_source":a.roster,
           "code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "population":"top8 issuers to top500 receiver companies excluding same issuer", "cohorts":{}}
    n = c.execute("SELECT count(DISTINCT permco) FROM roster").fetchone()[0]
    j = c.execute("SELECT count(DISTINCT permco) FROM roster WHERE issuer_rank<=8").fetchone()[0]
    out["candidate_pair_denominator"] = j*(n-1)
    for name in ["economic_date_only", "vendor_observed_by_cutoff"]:
        c.execute(f"""CREATE OR REPLACE TEMP TABLE links AS SELECT DISTINCT s.crsp_portno,s.classification,r.permco,r.issuer_rank
          FROM read_parquet({q(root/(name+'_membership.parquet'))}) s JOIN roster r USING(permno)""")
        c.execute("""CREATE OR REPLACE TEMP TABLE pairs AS SELECT a.permco issuer_permco,b.permco receiver_permco,a.classification,
          count(DISTINCT a.crsp_portno) shared_recorded_portfolios FROM links a JOIN links b USING(crsp_portno)
          WHERE a.issuer_rank<=8 AND a.permco<>b.permco
          GROUP BY a.permco,b.permco,a.classification""")
        c.execute(f"COPY pairs TO {q(root/(name+'_pair_support.parquet'))} (FORMAT PARQUET)")
        out["cohorts"][name] = {
          "companies_held":c.execute("SELECT count(DISTINCT permco) FROM links").fetchone()[0],
          "issuers_held":c.execute("SELECT count(DISTINCT permco) FROM links WHERE issuer_rank<=8").fetchone()[0],
          "observed_pairs_any_class":c.execute("SELECT count(*) FROM (SELECT DISTINCT issuer_permco,receiver_permco FROM pairs)").fetchone()[0],
          "observed_pairs_by_recorded_class":dict(c.execute("SELECT classification,count(*) FROM pairs GROUP BY classification").fetchall()),
          "candidate_pairs_not_observed_are":"UNKNOWN_FULL_UNIVERSE_EXPOSURE_NOT_ZERO",
        }
    (root/"ROSTER_NETWORK_SUPPORT.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))


if __name__ == "__main__":
    main()
