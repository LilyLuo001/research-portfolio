from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import zipfile


HERE = Path(__file__).resolve().parent


def load_downloader():
    spec = importlib.util.spec_from_file_location(
        "yax_bcc_dashboard_downloader", HERE / "download_bcc_public_dashboard.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DOWNLOADER = load_downloader()


def test_manifest_uses_fixed_generations_and_complete_sha256():
    manifest = json.loads((HERE / "BCC_PUBLIC_DASHBOARD_MANIFEST.json").read_text())
    assert len(manifest["archives"]) == 3
    for archive in manifest["archives"]:
        assert f"generation={archive['gcs_generation']}" in archive["url"]
        assert len(archive["sha256"]) == 64
        assert archive["content_length"] > 0
        assert archive["members"]
        assert all(len(value) == 64 for value in archive["members"].values())


def test_manifest_does_not_claim_exact_membership_access():
    disposition = json.loads(
        (HERE / "BCC_PUBLIC_DASHBOARD_MANIFEST.json").read_text()
    )["membership_disposition"]
    assert disposition["occupation_or_soc_field_in_downloads"] is False
    assert disposition["occupation_to_quintile_membership_in_downloads"] is False
    assert disposition["analysis_code_in_downloads"] is False
    assert disposition["paper_says_code_available_upon_request"] is True
    assert disposition["authors_contacted"] is False


def test_safe_member_rejects_traversal_and_subdirectories():
    assert DOWNLOADER.safe_member("result.csv")
    assert not DOWNLOADER.safe_member("../result.csv")
    assert not DOWNLOADER.safe_member("folder/result.csv")
    assert not DOWNLOADER.safe_member("/tmp/result.csv")

