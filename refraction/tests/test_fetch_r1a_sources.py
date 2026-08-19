"""R1a fetcher: exercised with an injected fetcher, so the tests never touch the
network — and so the failure paths (which are the whole point) can be driven.

The script's job is to turn a manual paste task into a mechanical one. What must
be true: it records what it actually received, it says UNKNOWN when it received
nothing, and it never fabricates a fact it did not fetch.
"""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch_r1a_sources as fr  # noqa: E402

CSV_BODY = (b"date,fomc_surprise,scheduled\n"
            b"2022-06-15,0.25,1\n2022-07-27,-0.10,1\n2022-09-21,0.05,1\n")
PAGE = (b'<html><a href="/files/usmpd.csv">data</a>'
        b'<a href="/docs/readme.pdf">doc</a></html>')


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(fr, "REGISTRY", tmp_path / "r1a_registry.csv")
    monkeypatch.setattr(fr, "HEADS", tmp_path / "r1a_file_heads.md")
    monkeypatch.setattr(fr, "LINKS", tmp_path / "r1a_links.csv")
    monkeypatch.setattr(fr, "urlopen", lambda *a, **k:
                        (_ for _ in ()).throw(AssertionError("real network call")))
    return tmp_path


def fake(mapping, default=(404, b"", "HTTPError 404")):
    def _f(url, timeout=60):
        return mapping.get(url, default)
    return _f


def test_a_tabular_download_yields_the_column_list_and_first_rows(isolate):
    seed = fr.SEEDS["usmpd"][0]
    data_url = "https://www.frbsf.org/files/usmpd.csv"
    rows, links, heads = fr.run(["usmpd"], fetcher=fake({
        seed: (200, PAGE, ""), data_url: (200, CSV_BODY, "")}))
    assert len(heads) == 1
    h = heads[0]
    assert h["columns"] == ["date", "fomc_surprise", "scheduled"]
    assert len(h["rows"]) == 3
    assert h["url"] == data_url
    assert any(l["discovered_url"] == data_url for l in links)


def test_head_extraction_answers_the_paste_list_items(isolate):
    seed = fr.SEEDS["usmpd"][0]
    fr.write_outputs(*fr.run(["usmpd"], fetcher=fake({
        seed: (200, PAGE, ""), "https://www.frbsf.org/files/usmpd.csv": (200, CSV_BODY, "")})))
    md = (isolate / "r1a_file_heads.md").read_text()
    assert "fomc_surprise" in md
    # and it must NOT claim to have answered the judgement item
    assert "item 4" in md.lower() or "deliberately NOT answered" in md


def test_an_unreachable_source_becomes_UNKNOWN_carrying_the_url_and_error(isolate):
    rows, _, heads = fr.run(["usmpd"], fetcher=fake({}, (403, b"", "HTTPError 403")))
    assert heads == []
    r = rows[0]
    assert r["conclusion"] == "UNKNOWN"
    assert r["source_url"] == fr.SEEDS["usmpd"][0]
    assert "403" in r["unknown"] and r["sha256"] == ""


def test_a_wrong_seed_url_surfaces_as_a_404_row_not_a_silent_gap(isolate):
    rows, _, _ = fr.run(["cpi_schedule"], fetcher=fake({}))
    assert rows[0]["http_status"] == 404 and rows[0]["conclusion"] == "UNKNOWN"


def test_every_row_carries_a_locator_and_a_retrieval_timestamp(isolate):
    seed = fr.SEEDS["fomc_calendar"][0]
    rows, _, _ = fr.run(["fomc_calendar"], fetcher=fake({seed: (200, PAGE, "")}))
    for r in rows:
        assert r["source_url"].startswith("http") and r["retrieved_at"].endswith("+00:00")


def test_checksum_is_of_the_bytes_actually_received(isolate):
    import hashlib
    seed = fr.SEEDS["usmpd"][0]
    rows, _, _ = fr.run(["usmpd"], fetcher=fake({seed: (200, PAGE, "")}))
    assert rows[0]["sha256"] == hashlib.sha256(PAGE).hexdigest()
    assert rows[0]["bytes"] == len(PAGE)


def test_confidence_high_means_provenance_only_never_verified_content(isolate):
    """The registry says where bytes came from; whether their content is correct
    is R1a's reading step, not this script's."""
    src = (Path(fr.__file__)).read_text()
    assert "never that" in src and "CONTENT has been verified" in src


def test_downloads_are_cached_under_a_url_keyed_name(isolate):
    seed = fr.SEEDS["usmpd"][0]
    fr.run(["usmpd"], fetcher=fake({seed: (200, PAGE, "")}))
    cached = list((isolate / "cache").rglob("*"))
    assert any(p.suffix == ".html" for p in cached)


def test_a_page_with_no_data_file_lists_what_it_did_contain(isolate):
    """'No data file exists' would be a claim; 'here is every link I saw' is a
    fact a human can act on."""
    seed = fr.SEEDS["usmpd"][0]
    page = b'<html><a href="/about">about</a><a href="/contact">contact</a></html>'
    _, links, heads = fr.run(["usmpd"], fetcher=fake({seed: (200, page, "")}))
    assert heads == []
    assert {l["discovered_url"].rsplit("/", 1)[-1] for l in links} == {"about", "contact"}


def test_one_failing_source_does_not_abort_the_sweep(isolate):
    def flaky(url, timeout=60):
        if "bls.gov" in url:
            raise_ = RuntimeError("boom")
            return 0, b"", f"RuntimeError: {raise_}"
        return 200, PAGE, ""
    rows, _, _ = fr.run(fetcher=flaky)
    kinds = {r["kind"] for r in rows}
    assert "usmpd" in kinds and "cpi_schedule" in kinds and "employment_schedule" in kinds


def test_seed_urls_are_landing_pages_not_deep_file_paths():
    """Deep file URLs from memory are the failure mode this avoids: a seed page
    is fetched and its links discovered, so a stale guess shows as a 404."""
    for urls in fr.SEEDS.values():
        for u in urls:
            assert not u.lower().endswith((".csv", ".xlsx", ".zip", ".dta"))
