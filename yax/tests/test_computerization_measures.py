import csv
import importlib.util
import io
import pathlib
import sys
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "measurement" / "build_computerization_measures.py"
SPEC = importlib.util.spec_from_file_location("build_computerization_measures", PATH)
B = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = B
SPEC.loader.exec_module(B)


def test_onet_element_uses_base_and_falls_back_to_detail_mean(tmp_path):
    path = tmp_path / "db_24_3_text.zip"
    fields = ["O*NET-SOC Code", "Element ID", "Element Name", "Scale ID",
              "Data Value"]
    rows = [
        ["11-1011.00", B.ONET_ELEMENT, B.ONET_OFFICIAL_LABEL, "IM", "4"],
        ["11-1011.01", B.ONET_ELEMENT, B.ONET_OFFICIAL_LABEL, "IM", "2"],
        ["11-1011.00", B.ONET_ELEMENT, B.ONET_OFFICIAL_LABEL, "LV", "3"],
        ["11-2020.01", B.ONET_ELEMENT, B.ONET_OFFICIAL_LABEL, "IM", "2"],
        ["11-2020.02", B.ONET_ELEMENT, B.ONET_OFFICIAL_LABEL, "IM", "4"],
        ["11-2020.01", B.ONET_ELEMENT, B.ONET_OFFICIAL_LABEL, "LV", "1"],
        ["11-2020.02", B.ONET_ELEMENT, B.ONET_OFFICIAL_LABEL, "LV", "3"],
    ]
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(fields)
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("db_24_3_text/Work Activities.txt", out.getvalue())
    scores, rules, n = B.parse_onet24(path)
    assert n == 7
    assert scores["11-1011"]["onet_computers_importance"] == 4
    assert scores["11-2020"]["onet_computers_importance"] == 3
    assert scores["11-2020"]["onet_computers_level"] == 2
    assert rules["IM:published_base_00"] == 1
    assert rules["IM:equal_mean_detail_children"] == 1


def test_frey_parser_requires_all_702_ranked_rows():
    text = "\n".join(
        f"{rank}.    0.50          {11 + rank % 10:02d}-{rank:04d}      Job {rank}"
        for rank in range(1, 703)
    )
    rows = B.parse_frey_text(text)
    assert len(rows) == 702
    assert rows[0]["rank"] == 1
    assert rows[-1]["rank"] == 702


def test_soc_merge_with_different_scores_fails_closed():
    source = {
        "11-1011": {"score": 1.0},
        "11-1012": {"score": 2.0},
        "11-2020": {"score": 3.0},
    }
    crosswalk = [
        {"soc_2010": "11-1011", "soc_2018": "11-1010", "soc_2018_title": "A"},
        {"soc_2010": "11-1012", "soc_2018": "11-1010", "soc_2018_title": "A"},
        {"soc_2010": "11-2020", "soc_2018": "11-2021", "soc_2018_title": "B"},
        {"soc_2010": "11-2020", "soc_2018": "11-2022", "soc_2018_title": "C"},
    ]
    rows, diagnostic = B.harmonize_soc2010(source, crosswalk, ("score",))
    assert rows["11-1010"]["score"] is None
    assert rows["11-1010"]["harmonization_status"] == "merge_ambiguous_fail_closed"
    assert rows["11-2021"]["score"] == 3.0
    assert rows["11-2021"]["harmonization_status"] == "split_inherited_from_2010_parent"
    assert diagnostic["n_source_codes_mapped"] == 3


def test_census_bridge_never_renormalizes_missing_children():
    bridge = [
        {"census_2010": "0010", "census_2018": "0011", "bridge_weight": ".6",
         "soc_2018_pattern": "11-1011"},
        {"census_2010": "0010", "census_2018": "0012", "bridge_weight": ".4",
         "soc_2018_pattern": "11-1012"},
    ]
    census = {
        "0011": {"score": 2.0, "score_covered_weight": 1.0,
                 "score_partial_sum": 2.0},
        "0012": {"score": None, "score_covered_weight": 0.0,
                 "score_partial_sum": None},
    }
    row = B.bridge_census2010(bridge, census, ("score",))["0010"]
    assert row["score"] is None
    assert row["score_covered_route_mass"] == .6
    assert row["score_partial_sum"] == 1.2


def test_direct_dorn_uses_software_and_documented_rti_formula():
    rows = B.direct_dorn_rows(
        [{"occ": "10", "occ1990dd": "100"}],
        [{"occ1990dd": "100", "occ1990dd_title": "A", "pct_software": "80"}],
        [{"occ1990dd": "100", "task_abstract": "2", "task_routine": "8",
          "task_manual": "4"}],
    )
    assert rows["0010"]["webb_pct_software"] == 80
    assert abs(rows["0010"]["rti_autor_dorn"]) < 1e-12
