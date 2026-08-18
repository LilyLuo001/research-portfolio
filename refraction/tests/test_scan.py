"""REFR-R13a collision-monitor tests.

Synthetic records only — per the iron rule these exercise the machinery and
never assert about the world (no network is touched; the API legs are not
called). What is under test is the part manual §R13b makes non-negotiable:
毛刺节 membership and the 40%/60% ALERT split are mechanical, not a judgement
the downstream cheap model is trusted to make.
"""
import json
import re
import sys
from pathlib import Path

import pytest

# Same explicit insert as test_prereg_guard.py: under a bare `pytest` (what CI
# runs) the repo root is not on sys.path, and relying on a sibling test file
# being collected first to put it there makes this module's import order-dependent.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from refraction import scan  # noqa: E402


def mk(title="A paper on ETFs", authors="Jane Doe", src="arXiv", hid=None,
       date="2026-08-01", keyword="conversion comovement"):
    return scan.classify_hit({
        "id": hid or ("arxiv:" + title[:8].replace(" ", "")),
        "title": title, "authors": authors, "date": date,
        "abstract": "", "url": "http://example.invalid/x", "source": src,
        "keyword": keyword,
    })


# ---------------------------------------------------------------- hair trigger

@pytest.mark.parametrize("authors", [
    "Ada Marta",                 # surname, single author
    "B. C. Riva",                # initials + surname
    "Jane Doe; Ada Marta",       # second position
    "MARTA, Ada",                # comma form, upper case (regression: took "Ada")
    "Marta A.",                  # surname + trailing initial
    "Ada Marta, Bo Riva",        # comma-separated list, no semicolons
])
def test_hair_trigger_fires_on_marta_riva_authors(authors):
    h = mk(authors=authors)
    assert h["hair_trigger"] is True
    assert h["alert_threshold_pct"] == scan.ALERT_HAIR == 40
    assert "author:" in h["hair_reason"]


@pytest.mark.parametrize("title", [
    "Replication technique and comovement",
    "A replication switch in European ETFs",
    "REPLICATION   SWITCH effects",       # case + whitespace tolerant
])
def test_hair_trigger_fires_on_replication_titles(title):
    h = mk(title=title, authors="Someone Else")
    assert h["hair_trigger"] is True
    assert h["alert_threshold_pct"] == 40
    assert "title:replication-technique/switch" in h["hair_reason"]


def test_ordinary_hit_keeps_the_60_percent_line():
    h = mk(title="ETF baskets and macro news", authors="Jane Doe")
    assert h["hair_trigger"] is False
    assert h["hair_reason"] == ""
    assert h["alert_threshold_pct"] == scan.ALERT_DEFAULT == 60


def test_watchlist_author_alone_does_not_hair_trigger():
    # plan §11 tracks Greenwood, but §R13b's hair trigger is Marta/Riva only.
    h = mk(authors="Robin Greenwood")
    assert h["watchlist"] == "greenwood"
    assert h["hair_trigger"] is False
    assert h["alert_threshold_pct"] == 60


def test_watchlist_uses_surnames_not_every_token():
    # "Da" is on plan §11's watchlist and is also a common given-name token;
    # the watchlist must not fire on "Da-Wei Zhang" the way the hair trigger would.
    assert scan._surnames("Da-Wei Zhang") == ["zhang"]
    assert scan.classify_hit(mk(authors="Da-Wei Zhang"))["watchlist"] == ""


def test_both_rules_reported_together():
    h = mk(title="A replication switch study", authors="Ada Marta; Bo Riva")
    assert h["hair_trigger"] is True
    assert "author:marta+riva" in h["hair_reason"]
    assert "title:replication-technique/switch" in h["hair_reason"]


def test_missing_author_field_does_not_crash():
    for bad in (None, "", "   ", ";;"):
        h = mk(authors=bad)
        assert h["hair_trigger"] is False


# ---------------------------------------------------------------------- dedup

def test_same_paper_from_two_sources_collapses_once():
    a = mk(title="One Shock Many Prices", src="arXiv", hid="arxiv:1")
    b = mk(title="one shock many prices", src="SemanticScholar", hid="s2:xyz",
           keyword="s2-bulk")
    out = scan.dedup([a, b], seen={})
    assert len(out) == 1
    assert "s2-bulk" in out[0]["keyword"]      # keyword union, not a second row


def test_seen_registry_suppresses_repeat_hits():
    a = mk(title="Old news", hid="arxiv:9")
    assert len(scan.dedup([a], seen={})) == 1
    assert scan.dedup([a], seen={"arxiv:9": "2026-07-01"}) == []
    assert scan.dedup([a], seen={scan.norm_key("Old news"): "2026-07-01"}) == []


def test_hits_sort_newest_first():
    out = scan.dedup([mk(title="older", hid="arxiv:1", date="2026-07-01"),
                      mk(title="newer", hid="arxiv:2", date="2026-08-10")],
                     seen={})
    assert [h["title"] for h in out] == ["newer", "older"]


# ------------------------------------------------------------- 毛刺节 rendering

def test_hairtrigger_section_is_written_even_when_empty():
    md = scan.render_hairtrigger([mk()], "20260818")
    assert "empty this run" in md
    assert "边界表影响评估" not in md


def test_hairtrigger_section_lists_entry_with_full_text_link():
    md = scan.render_hairtrigger([mk(authors="Ada Marta"), mk()], "20260818")
    assert "http://example.invalid/x" in md          # §R13b: 给全文链接
    assert "40%" in md
    # §R13b: 毛刺节非空 → triage must add the boundary-table impact section
    assert "边界表影响评估" in md


# ------------------------------------------------------------------ spec shape

def test_keyword_list_is_bilingual_and_carries_the_six_spec_strings():
    for kw in ["ETF basket comovement announcement", "conversion comovement",
               "announcement day beta ETF", "ETF replication switch comovement",
               "creation basket transmission", "passive macro news cross-section"]:
        assert kw in scan.KEYWORDS
    assert any(re.search(r"[一-鿿]", k) for k in scan.KEYWORDS), "中英双语"


def test_window_is_monthly_not_e2_biweekly():
    # manual §R13 title is 月度碰撞监测; E2-T11's 21-day window must not be inherited.
    assert scan.WINDOW_DAYS == 31


def test_ssrn_urls_are_generated_not_scraped():
    urls = scan.ssrn_manual_urls()
    assert len(urls) == len(scan.KEYWORDS)
    assert all(u.startswith("https://www.ssrn.com/") for u in urls)


def test_jsonl_record_is_serializable_with_the_new_fields():
    rec = json.loads(json.dumps(mk(authors="Ada Marta"), ensure_ascii=False))
    for field in ("hair_trigger", "hair_reason", "alert_threshold_pct", "watchlist"):
        assert field in rec



# ------------------------------------------- source parsers (fixtures, no net)

ATOM_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2608.00001v1</id>
    <published>{recent}T00:00:00Z</published>
    <title>A replication switch
    study</title>
    <summary>Basket   comovement.</summary>
    <author><name>Ada Marta</name></author>
    <author><name>Bo Riva</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2501.00002v1</id>
    <published>2025-01-01T00:00:00Z</published>
    <title>Too old to be in window</title>
    <summary>x</summary>
    <author><name>Jane Doe</name></author>
  </entry>
</feed>"""


def test_arxiv_parser_normalizes_and_applies_the_window(monkeypatch):
    import datetime
    today = datetime.date(2026, 8, 18)
    cutoff = today - datetime.timedelta(days=scan.WINDOW_DAYS)
    monkeypatch.setattr(scan, "http_get",
                        lambda *a, **k: ATOM_FIXTURE.format(recent="2026-08-10"))
    hits = scan.arxiv_search("conversion comovement", cutoff)

    assert len(hits) == 1, "the 2025 entry is outside the 31-day window"
    h = hits[0]
    assert h["id"] == "arxiv:2608.00001v1"
    assert h["title"] == "A replication switch study"   # newline collapsed
    assert h["abstract"] == "Basket comovement."        # whitespace collapsed
    assert h["authors"] == "Ada Marta; Bo Riva"
    assert h["hair_trigger"] is True                    # classified at parse time
    assert h["alert_threshold_pct"] == 40


S2_FIXTURE = json.dumps({"data": [
    {"title": "Creation baskets and transmission", "publicationDate": "2026-08-05",
     "authors": [{"name": "Robin Greenwood"}], "abstract": "a b",
     "url": "https://s2/x", "externalIds": {"DOI": "10.1/abc"}},
    {"title": "No date at all", "publicationDate": None, "authors": [],
     "abstract": "", "url": "", "externalIds": {}},
]})


def test_s2_parser_keys_on_doi_and_drops_undated(monkeypatch):
    import datetime
    monkeypatch.setattr(scan, "http_get", lambda *a, **k: S2_FIXTURE)
    hits = scan.s2_search_bulk(datetime.date(2026, 7, 18))
    assert len(hits) == 1, "an undated record cannot be window-checked; drop it"
    assert hits[0]["id"] == "doi:10.1/abc"
    assert hits[0]["watchlist"] == "greenwood"
    assert hits[0]["hair_trigger"] is False


def test_total_source_failure_exits_nonzero(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise RuntimeError("egress blocked")
    monkeypatch.setattr(scan, "http_get", boom)
    monkeypatch.setattr(scan, "OUTDIR", tmp_path)
    monkeypatch.setattr(scan.time, "sleep", lambda *_: None)
    monkeypatch.setattr(scan.sys, "argv", ["scan.py"])
    assert scan.main() == 1, "cron must see a nonzero code when every leg fails"


def test_partial_source_failure_still_writes_outputs(monkeypatch, tmp_path):
    # arXiv up, S2 down -> a normal run with one recorded error, exit 0.
    monkeypatch.setattr(scan, "OUTDIR", tmp_path)
    monkeypatch.setattr(scan, "SEEN_PATH", tmp_path / "seen_ids.json")
    monkeypatch.setattr(scan.time, "sleep", lambda *_: None)
    monkeypatch.setattr(scan.sys, "argv", ["scan.py"])

    def fake_get(url, *a, **k):
        if "semanticscholar" in url:
            raise RuntimeError("429")
        return ATOM_FIXTURE.format(recent=scan.datetime.datetime.utcnow()
                                   .date().isoformat())
    monkeypatch.setattr(scan, "http_get", fake_get)
    assert scan.main() == 0

    stamp = scan.datetime.datetime.utcnow().date().strftime("%Y%m%d")
    assert (tmp_path / ("hits_%s.csv" % stamp)).exists()
    hair = (tmp_path / ("hairtrigger_%s.md" % stamp)).read_text(encoding="utf-8")
    assert "边界表影响评估" in hair, "the Marta/Riva fixture must reach the 毛刺节"
    assert (tmp_path / "seen_ids.json").exists(), "dedup registry must persist"
