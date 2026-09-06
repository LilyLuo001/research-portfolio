"""Tests for stage0_discover.

These run with no WRDS access at all: the fixture builds a miniature archive
with the same shape as the real one (manifest, migration-verification report,
Parquet files under raw/rescue/). That is the point — the discovery logic has
to be trustworthy before it is pointed at data nobody can re-check by eye.
"""
import json
import pathlib
import sys

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import stage0_discover as s0  # noqa: E402


@pytest.fixture
def archive(tmp_path):
    """A miniature mirror: two families, one overlap trap, one bad manifest line."""
    root = tmp_path / "WRDS_MIRROR_20260902"
    proj = root / "p1_refraction_wrds_shared"
    meta = root / "_migration_meta"
    (proj / "raw" / "rescue").mkdir(parents=True)
    meta.mkdir(parents=True)

    def write_parquet(rel, table):
        p = proj / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, p)
        return p

    dsi = pa.table({"date": pa.array([1, 2]), "vwretd": pa.array([0.1, 0.2])})
    legacy = pa.table({"permno": pa.array([84398]), "date": pa.array([1]),
                       "ret": pa.array([0.01]), "retx": pa.array([0.01])})
    ciz = pa.table({"permno": pa.array([84398]), "dlycaldt": pa.array([1])})

    files = {
        "raw/rescue/crsp_dsi_2019.parquet": dsi,
        "raw/rescue/crsp_dsf_2019.parquet": legacy,
        "raw/rescue/newcrsp_crsp_dsf_v2_2024.parquet": ciz,
    }
    lines = []
    for rel, tbl in files.items():
        p = write_parquet(rel, tbl)
        lines.append(f"{p.stat().st_size}\tp1_refraction_wrds_shared/{rel}")

    # A path in the manifest that is not on disk, and a malformed line.
    lines.append("12345\tp1_refraction_wrds_shared/raw/rescue/crsp_dsi_1999.parquet")
    lines.append("this is not a manifest line")
    (meta / "FINAL_SCC_MANIFEST.tsv").write_text("\n".join(lines) + "\n")

    (meta / "FINAL_VERIFY_REPORT.txt").write_text(
        "PATH_SIZE_CHECK = PASS\nPARQUET_COUNT_CHECK = PASS\n"
        "CHECKSUM_CHECK = RUNNING\nSAFE_TO_DELETE_WRDS = NO\n")

    cfg = {
        "archive": {
            "root": str(root),
            "project_subdir": "p1_refraction_wrds_shared",
            "migration_meta_subdir": "_migration_meta",
            "manifest": "FINAL_SCC_MANIFEST.tsv",
            "verify_reports": ["FINAL_VERIFY_REPORT.txt"],
        },
        "families": {
            "crsp_dsi": {"patterns": ["dsi"], "needed_for": "3A benchmark"},
            "crsp_dsf_legacy": {"patterns": ["crsp_dsf", "_dsf"],
                                "exclude": ["newcrsp", "_v2_"],
                                "needed_for": "daily returns"},
            "crsp_dsf_ciz": {"patterns": ["newcrsp"], "needed_for": "overlap check"},
        },
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    return {"root": root, "meta": meta, "cfg": cfg_path, "tmp": tmp_path}


# ---------------------------------------------------------------- manifest ---
def test_manifest_skips_malformed_lines_rather_than_guessing(archive):
    rows = s0.read_manifest(archive["meta"] / "FINAL_SCC_MANIFEST.tsv")
    assert len(rows) == 4
    assert s0.read_manifest.skipped == 1
    assert all(isinstance(b, int) for b, _ in rows)


def test_unresolvable_path_is_reported_not_dropped(archive):
    rows = s0.read_manifest(archive["meta"] / "FINAL_SCC_MANIFEST.tsv")
    bases = [archive["root"], archive["root"] / "p1_refraction_wrds_shared"]
    resolved = [s0.resolve_rel(rel, bases)[0] for _, rel in rows]
    assert resolved.count(None) == 1


def test_resolve_rel_reports_which_base_worked(archive):
    bases = [archive["root"], archive["root"] / "p1_refraction_wrds_shared"]
    p, base = s0.resolve_rel(
        "p1_refraction_wrds_shared/raw/rescue/crsp_dsi_2019.parquet", bases)
    assert p is not None and base == str(archive["root"])


# ---------------------------------------------------------------- families ---
def test_legacy_family_excludes_the_ciz_lookalike(archive):
    cfg = yaml.safe_load(archive["cfg"].read_text())
    rows = s0.read_manifest(archive["meta"] / "FINAL_SCC_MANIFEST.tsv")
    hits = s0.match_families(rows, cfg["families"])
    legacy = [h["manifest_path"] for h in hits
              if h["logical_family"] == "crsp_dsf_legacy"]
    assert any("crsp_dsf_2019" in p for p in legacy)
    assert not any("newcrsp" in p for p in legacy)


def test_partition_hint_and_stage_are_storage_facts_only():
    assert s0.partition_hint("raw/rescue/compna_secd_2025_03.parquet") == "month:2025-03"
    assert s0.partition_hint("raw/rescue/crsp_holdings_etf_2019_b0135.parquet") \
        == "portfolio_batch:0135"
    assert s0.partition_hint("raw/rescue/x_2025.parquet") == "year:2025"
    assert s0.partition_hint("raw/x.parquet") == "none"
    assert s0.stage_of("p1/raw/rescue_remaining/a.parquet") == "rescue_remaining"
    assert s0.stage_of("p1/raw/maximal/a.parquet") == "maximal"


# ---------------------------------------------------------------- metadata ---
def test_parquet_metadata_reads_footer_without_loading_rows(archive):
    p = archive["root"] / "p1_refraction_wrds_shared/raw/rescue/crsp_dsi_2019.parquet"
    meta = s0.parquet_metadata(p)
    assert meta["n_rows"] == 2
    assert meta["columns"] == ["date", "vwretd"]
    assert len(meta["schema_sha1"]) == 12


def test_corrupt_parquet_is_a_finding_not_a_crash(archive, tmp_path):
    bad = archive["root"] / "p1_refraction_wrds_shared/raw/rescue/bad_dsi.parquet"
    bad.write_bytes(b"not parquet at all")
    hits = [{"logical_family": "crsp_dsi",
             "manifest_path": "p1_refraction_wrds_shared/raw/rescue/bad_dsi.parquet",
             "bytes": 18, "needed_for": ""}]
    rows, counts = s0.build_catalog(
        hits, [archive["root"]], progress_every=0)
    assert counts["parquet_error"] == 1
    assert rows[0]["read_error"]


# ------------------------------------------------------------- preflight -----
def test_preflight_write_leaves_no_probe_behind(tmp_path):
    out = tmp_path / "nested" / "out"
    s0.preflight_write(out)
    assert out.is_dir()
    assert not (out / ".write_probe").exists()


# ------------------------------------------------------------- end to end ----
def test_end_to_end_writes_catalog_report_and_lineage(archive):
    out = archive["tmp"] / "out"
    rc = s0.main(["--out", str(out), "--config", str(archive["cfg"]),
                  "--progress-every", "0"])
    assert rc == 0

    catalog = (out / "source_catalog.tsv").read_text().splitlines()
    assert catalog[0].split("\t") == s0.CATALOG_COLUMNS
    assert len(catalog) - 1 == 4  # 3 resolved + 1 unresolved manifest hit

    report = json.loads((out / "stage0_report.json").read_text())
    assert report["manifest_unparseable_lines"] == 1
    assert report["counts"]["unresolved"] == 1
    assert report["migration_verification"]["FINAL_VERIFY_REPORT.txt"]["statuses"] \
        ["CHECKSUM_CHECK"] == "RUNNING"
    # Stage 0 observes; it must never pre-empt the stage-5 decision.
    assert report["purchase_recommendation"] is None

    for name in ("source_catalog.tsv", "stage0_report.json"):
        lin = json.loads((out / f"{name}.lineage.json").read_text())
        assert lin["output_sha256"]
        assert any("FINAL_SCC_MANIFEST" in i["path"] for i in lin["inputs"])


def test_one_alternative_value_weighted_return_satisfies_the_gate(archive):
    """vwretd and vwretx are alternatives, so either alone must satisfy 3A.

    Requiring both would report a usable benchmark as BLOCKED and push the
    module into a needless "adaptation" label.
    """
    out = archive["tmp"] / "out2"
    s0.main(["--out", str(out), "--config", str(archive["cfg"]),
             "--progress-every", "0"])
    report = json.loads((out / "stage0_report.json").read_text())
    cap = report["families"]["crsp_dsi"]["capability"]
    assert cap["match_mode"] == "any"
    assert cap["satisfied"] is True
    assert cap["columns_observed"] == ["vwretd"]


def test_all_of_gate_still_requires_every_column(archive):
    """The link table's sdate/edate/score are not alternatives."""
    assert s0.CAPABILITY_COLUMNS["crsp_ibes_link"]["mode"] == "all"
    rows = [{"logical_family": "crsp_ibes_link", "resolved": True,
             "columns_csv": "ticker,permno,sdate,edate", "n_rows": 10,
             "schema_sha1": "abc", "source_download_stage": "raw_or_other"}]
    fams = {"crsp_ibes_link": {"needed_for": ""}}
    cap = s0.summarise(rows, fams)["crsp_ibes_link"]["capability"]
    assert cap["satisfied"] is False
    assert cap["columns_missing"] == ["score"]


def test_missing_vw_column_blocks_the_hou_moskowitz_gate(archive):
    """If crsp.dsi carries no value-weighted return, 3A must read BLOCKED.

    The instruction is explicit that the original-style baseline is then
    unavailable and a substitute has to be labelled an adaptation — so this flag
    must not quietly pass on a file that merely exists.
    """
    p = archive["root"] / "p1_refraction_wrds_shared/raw/rescue/crsp_dsi_2019.parquet"
    pq.write_table(pa.table({"date": pa.array([1]), "sprtrn": pa.array([0.1])}), p)
    out = archive["tmp"] / "out3"
    s0.main(["--out", str(out), "--config", str(archive["cfg"]),
             "--progress-every", "0"])
    report = json.loads((out / "stage0_report.json").read_text())
    assert report["families"]["crsp_dsi"]["capability"]["satisfied"] is False


def test_absent_archive_returns_need_human_not_an_empty_catalog(archive, tmp_path):
    cfg = yaml.safe_load(archive["cfg"].read_text())
    cfg["archive"]["root"] = str(tmp_path / "nope")
    bad_cfg = tmp_path / "bad.yaml"
    bad_cfg.write_text(yaml.safe_dump(cfg))
    out = tmp_path / "out4"
    assert s0.main(["--out", str(out), "--config", str(bad_cfg)]) == 3
    assert not (out / "source_catalog.tsv").exists()
