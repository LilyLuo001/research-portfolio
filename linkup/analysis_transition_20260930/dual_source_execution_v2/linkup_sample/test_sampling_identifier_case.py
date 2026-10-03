#!/usr/bin/env python3
"""Regression fixture for DuckDB's case-insensitive SQL identifiers."""
import duckdb


def main():
    con = duckdb.connect()
    con.execute("CREATE TABLE frame(cell VARCHAR, arm VARCHAR, job_hash VARCHAR)")
    rows = []
    for cell, count_a, count_b in (("x", 2, 9), ("y", 3, 4)):
        rows += [(cell, "A", f"{cell}-a-{i}") for i in range(count_a)]
        rows += [(cell, "B", f"{cell}-b-{i}") for i in range(count_b)]
    con.executemany("INSERT INTO frame VALUES (?,?,?)", rows)
    con.execute("""
      CREATE TABLE cells AS
      SELECT cell,
        count(*) FILTER (WHERE arm='A') AS frame_count_a,
        count(*) FILTER (WHERE arm='B') AS frame_count_b
      FROM frame GROUP BY cell
    """)
    con.execute("""
      CREATE TABLE support AS SELECT *,
        least(frame_count_b,3*frame_count_a) AS sample_count_b,
        least(frame_count_b,3*frame_count_a)::DOUBLE/frame_count_b AS inclusion_probability_b
      FROM cells
    """)
    con.execute("""
      CREATE TABLE selected AS
      SELECT f.*,s.frame_count_a,s.frame_count_b,s.sample_count_b,s.inclusion_probability_b,
        row_number() OVER (PARTITION BY f.cell,f.arm ORDER BY f.job_hash) AS stable_rank
      FROM frame f JOIN support s USING(cell)
      QUALIFY arm='A' OR stable_rank<=sample_count_b
    """)
    counts = con.execute("SELECT cell,arm,count(*) FROM selected GROUP BY 1,2 ORDER BY 1,2").fetchall()
    assert counts == [("x", "A", 2), ("x", "B", 6), ("y", "A", 3), ("y", "B", 4)]
    weighted = con.execute("""
      SELECT cell,sum(1.0/inclusion_probability_b) FROM selected
      WHERE arm='B' GROUP BY cell ORDER BY cell
    """).fetchall()
    assert weighted == [("x", 9.0), ("y", 4.0)]
    columns = [row[0] for row in con.execute("DESCRIBE support").fetchall()]
    assert columns == ["cell", "frame_count_a", "frame_count_b", "sample_count_b", "inclusion_probability_b"]
    print("PASS: distinct identifiers, min(B,3A) cell counts, inverse-probability frame recovery")


if __name__ == "__main__":
    main()
