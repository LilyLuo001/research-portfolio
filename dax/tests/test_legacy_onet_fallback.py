"""Tests for the official O*NET 25.0 taxonomy fallback."""

import csv
import importlib.util
import pathlib


MODULE = (pathlib.Path(__file__).resolve().parents[1]
          / "w2" / "crosswalk" / "build_legacy_onet_fallback.py")
SPEC = importlib.util.spec_from_file_location("build_legacy_onet_fallback", MODULE)
assert SPEC and SPEC.loader
fallback = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fallback)


def test_taxonomy_sources_keep_only_legacy_profiles(tmp_path):
    path = tmp_path / "walk.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "O*NET-SOC 2010 Code", "O*NET-SOC 2010 Title",
            "O*NET-SOC 2019 Code", "O*NET-SOC 2019 Title",
        ])
        writer.writeheader()
        writer.writerow({"O*NET-SOC 2010 Code": "15-1132.00",
                         "O*NET-SOC 2019 Code": "15-1252.00"})
        writer.writerow({"O*NET-SOC 2010 Code": "99-9999.00",
                         "O*NET-SOC 2019 Code": "15-1252.00"})
    sources = fallback.taxonomy_sources(path, {"15-1132.00": [{"task_id": "1"}]})
    assert sources == {"15-1252.00": ["15-1132.00"]}


def test_current_usable_codes_are_not_replaced(tmp_path):
    path = tmp_path / "current.csv"
    path.write_text(
        "onet_soc,primary_usable\n15-1252.00,true\n25-9042.00,false\n",
        encoding="utf-8",
    )
    assert fallback.current_usable_codes(path) == {"15-1252.00"}
