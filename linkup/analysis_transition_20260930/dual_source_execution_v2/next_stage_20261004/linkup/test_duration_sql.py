#!/usr/bin/env python3
"""Focused synthetic checks for overall NULL-year joins and bound separation."""
import duckdb

con = duckdb.connect()
con.execute("CREATE TABLE sample(arm VARCHAR,created_year INTEGER,JOB_HASH VARCHAR)")
con.execute("INSERT INTO sample VALUES ('A',2024,'a1'),('A',2024,'a2'),('B',2024,'b1')")
con.execute("CREATE TABLE detected(arm VARCHAR,OBJECT_TYPE VARCHAR,created_year INTEGER,JOB_HASH VARCHAR)")
con.execute("INSERT INTO detected VALUES ('A','general_work',2024,'a1')")
rows = con.execute("""
WITH denom AS (
 SELECT arm,'overall' scope,NULL::INTEGER created_year,count(*) ads FROM sample GROUP BY arm
), numer AS (
 SELECT arm,OBJECT_TYPE,'overall' scope,NULL::INTEGER created_year,count(DISTINCT JOB_HASH) detected_ads
 FROM detected GROUP BY arm,OBJECT_TYPE
)
SELECT d.arm,coalesce(n.detected_ads,0),d.ads
FROM denom d LEFT JOIN numer n ON d.arm=n.arm AND n.OBJECT_TYPE='general_work' AND d.scope=n.scope
 AND d.created_year IS NOT DISTINCT FROM n.created_year ORDER BY d.arm
""").fetchall()
assert rows == [('A', 1, 2), ('B', 0, 1)], rows

con.execute("CREATE TABLE matched(arm VARCHAR,OBJECT_TYPE VARCHAR,created_year INTEGER,REQUIREMENT_STRENGTH VARCHAR,BOUND_TYPE VARCHAR,JOB_HASH VARCHAR,MIN_YEARS DOUBLE)")
con.execute("INSERT INTO matched VALUES ('A','general_work',2024,'required','minimum','a1',3),('A','general_work',2024,'required','range','a2',3),('A','general_work',2024,'required','exact_or_unspecified','a3',3)")
bounds = con.execute("SELECT BOUND_TYPE,count(*) FROM matched GROUP BY 1 ORDER BY 1").fetchall()
assert bounds == [('exact_or_unspecified', 1), ('minimum', 1), ('range', 1)], bounds
assert sum(n for _, n in bounds) == 3

con.execute("CREATE TABLE sample_key(JOB_HASH VARCHAR,SOURCE_FILE VARCHAR,SOURCE_ROW BIGINT,RECORD_SOURCE_ROW BIGINT)")
con.execute("INSERT INTO sample_key VALUES ('dup','right',2,20)")
con.execute("CREATE TABLE duration_key(JOB_HASH VARCHAR,SOURCE_FILE VARCHAR,SOURCE_ROW BIGINT,RECORD_SOURCE_ROW BIGINT,DURATION_UNIT VARCHAR,MIN_YEARS DOUBLE,MAX_YEARS DOUBLE)")
con.execute("INSERT INTO duration_key VALUES ('dup','wrong',1,10,'years',99,NULL),('dup','right',2,20,'year',NULL,4),('x','x',3,30,'months',12,NULL)")
joined = con.execute("""
 SELECT d.DURATION_UNIT,coalesce(d.MIN_YEARS,d.MAX_YEARS)
 FROM sample_key s JOIN duration_key d USING (JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW)
 WHERE lower(d.DURATION_UNIT) IN ('year','years') AND coalesce(d.MIN_YEARS,d.MAX_YEARS) IS NOT NULL
""").fetchall()
assert joined == [('year', 4.0)], joined
print('ok: NULL-year overall join, bound separation, year/years units, maximum-only value, and canonical occurrence join')
