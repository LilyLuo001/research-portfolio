#!/usr/bin/env python3
"""Prove the output filesystem accepts the writes this package will make.

Run before any computation. A quota or permission failure discovered after an
hour of extraction costs the hour; discovered here it costs nothing. The test
covers the three write shapes actually used downstream — a small text file, an
atomic rename, and a Parquet round trip — because a filesystem can accept one
and refuse another.
"""
import os
import sys

import pandas as pd

import ppw


def main():
    for d in (ppw.OUT, ppw.LOGS):
        d.mkdir(parents=True, exist_ok=True)
        print(f"  mkdir ok           {d}")

    t = ppw.OUT / "_writetest.txt"
    t.write_text("write test\n")
    assert t.read_text() == "write test\n"
    print(f"  text round trip ok {t}")

    tmp = t.with_suffix(".tmp")
    tmp.write_text("atomic\n")
    os.replace(tmp, t)
    assert t.read_text() == "atomic\n"
    print("  atomic rename ok   (checkpoints are written this way)")

    p = ppw.OUT / "_writetest.parquet"
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"], "d": pd.to_datetime(["2020-01-02", "2020-01-03"])})
    df.to_parquet(p, index=False)
    back = pd.read_parquet(p)
    assert back.equals(df), "parquet round trip altered the frame"
    print(f"  parquet round trip ok  ({p.stat().st_size} B, dtypes preserved)")

    t.unlink()
    p.unlink()

    st = os.statvfs(ppw.OUT)
    free_gib = st.f_bavail * st.f_frsize / 1024 ** 3
    print(f"\n  free on output filesystem: {free_gib:,.1f} GiB")
    if free_gib < 5:
        print("  WARN  under 5 GiB free; extraction outputs may not fit")

    ppw.provenance("s7_00_write_test", [], {"free_gib": round(free_gib, 1)})
    print("\n  WRITE_TEST = PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
