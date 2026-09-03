"""REFR-R13a scanner tests. Synthetic payloads only — `scan.http_get` is
monkeypatched in every test that reaches the network layer, and `scan.urlopen`
is poisoned so a regression that bypasses http_get fails loudly instead of
quietly calling arXiv from CI.

Per the iron rules these tests assert about the machinery (window, dedup,
毛刺 flagging, failure semantics), never about the world.
"""
import datetime
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from refraction import scan  # noqa: E402

TODAY = datetime.datetime.utcnow().date()
FRESH = (TODAY - datetime.timedelta(days=3)).isoformat()
STALE = (TODAY - datetime.timedelta(days=400)).isoformat()
CUTOFF = TODAY - datetime.timedelta(days=scan.WINDOW_DAYS)


def atom(entries):
    body = ['<feed xmlns="http://www.w3.org/2005/Atom">']
    for e in entries:
        body.append("<entry>")
        body.append("<id>%s</id>" % e.get("id", "http://arxiv.org/abs/2608.00001v1"))
        body.append("<title>%s</title>" % e.get("title", "A Title"))
        body.append("<published>%sT00:00:00Z</published>" % e.get("published", FRESH))
        body.append("<summary>%s</summary>" % e.get("summary", "An abstract."))
        for a in e.get("authors", ["Jane Doe"]):
            body.append("<author><name>%s</name></author>" % a)
        body.append("</entry>")
    body.append("</feed>")
    return "".join(body)


def s2(papers):
    return json.dumps({"data": papers})


def paper(**kw):
    p = {"paperId": "p1", "title": "S2 Title", "authors": [{"name": "Jane Doe"}],
         "abstract": "abs", "url": "https://s2/p1", "publicationDate": FRESH,
         "externalIds": {}}
    p.update(kw)
    return p


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any real urlopen/sleep during tests is a bug."""
    def poisoned(*a, **k):  # pragma: no cover - only runs on regression
        raise AssertionError("scan.py attempted a real network call in tests")
    monkeypatch.setattr(scan, "urlopen", poisoned)
    monkeypatch.setattr(scan.time, "sleep", lambda *_: None)


def run_main(monkeypatch, tmp_path, responder, argv=()):
    monkeypatch.setattr(scan, "http_get", responder)
    code = scan.main(["--out-dir", str(tmp_path)] + list(argv))
    stamp = TODAY.strftime("%Y%m%d")
    return code, stamp


def read_jsonl(tmp_path, stamp):
    p = tmp_path / ("hits_%s.jsonl" % stamp)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# --------------------------------------------------------------------------
# parsing + window
# --------------------------------------------------------------------------

def test_arxiv_parse_fields():
    hits = scan.parse_arxiv_atom(
        atom([{"id": "http://arxiv.org/abs/2608.01234v2", "title": "Basket  Refraction",
               "authors": ["Ann Lee", "Bo Chen"], "summary": "line1\nline2"}]),
        CUTOFF, "kw")
    assert len(hits) == 1
    h = hits[0]
    assert h["id"] == "arxiv:2608.01234v2"
    assert h["title"] == "Basket Refraction"          # whitespace collapsed
    assert h["authors"] == "Ann Lee; Bo Chen"
    assert h["abstract"] == "line1 line2"
    assert h["source"] == "arXiv" and h["keyword"] == "kw"


def test_window_drops_out_of_window_entries():
    hits = scan.parse_arxiv_atom(
        atom([{"published": STALE, "title": "Old"},
              {"published": FRESH, "title": "New", "id": "http://arxiv.org/abs/2608.9v1"}]),
        CUTOFF, "kw")
    assert [h["title"] for h in hits] == ["New"]


def test_s2_id_preference_doi_then_arxiv_then_paperid():
    hits = scan.parse_s2(s2([
        paper(title="withdoi", externalIds={"DOI": "10.1/x", "ArXiv": "2608.1"}),
        paper(title="witharxiv", externalIds={"ArXiv": "2608.2"}),
        paper(title="bare", paperId="abc"),
    ]), CUTOFF)
    assert [h["id"] for h in hits] == ["doi:10.1/x", "arxiv:2608.2", "s2:abc"]


def test_s2_undated_and_stale_rows_dropped():
    hits = scan.parse_s2(s2([
        paper(title="undated", publicationDate=None),
        paper(title="stale", publicationDate=STALE),
        paper(title="fresh"),
    ]), CUTOFF)
    assert [h["title"] for h in hits] == ["fresh"]


# --------------------------------------------------------------------------
# 毛刺 (hair-trigger) rules — manual §R13b
# --------------------------------------------------------------------------

@pytest.mark.parametrize("authors,title,reason", [
    (["Marta Someone"], "Unrelated title", "author:marta"),
    (["A. Riva"], "Unrelated title", "author:riva"),
    (["Jane Doe"], "A switch in ETF replication technique", "title:replication technique"),
    (["Jane Doe"], "Index switch and comovement", "title:switch"),
    (["Jane Doe"], "复制方式变更与共动", "title:复制方式"),
    (["Jane Doe"], "ETF 切换 的截面效应", "title:切换"),
])
def test_burr_rules_fire(authors, title, reason):
    h = scan.classify({"authors": "; ".join(authors), "title": title})
    assert h["burr"] is True
    assert reason in h["burr_reason"]
    assert h["alert_threshold"] == scan.ALERT_BURR == 0.40


def test_ordinary_hit_gets_default_threshold():
    h = scan.classify({"authors": "Jane Doe", "title": "Passive ownership and betas"})
    assert h["burr"] is False and h["burr_reason"] == ""
    assert h["alert_threshold"] == scan.ALERT_DEFAULT == 0.60


def test_author_matching_is_token_exact_not_substring():
    """'Rivas'/'Martarelli' are different people — flagging them would train the
    owner to ignore the 毛刺节, which is the one section that must stay hot."""
    h = scan.classify({"authors": "Carlos Rivas; Ugo Martarelli", "title": "Nothing"})
    assert h["burr"] is False


def test_burr_survives_into_outputs(monkeypatch, tmp_path):
    def responder(url, **kw):
        if "arxiv" in url:
            return atom([{"title": "Do ETFs increase comovement? A switch",
                          "authors": ["Marta X", "Riva Y"],
                          "id": "http://arxiv.org/abs/2608.5555v1"}])
        return s2([])
    code, stamp = run_main(monkeypatch, tmp_path, responder)
    assert code == 0
    rows = read_jsonl(tmp_path, stamp)
    assert len(rows) == 1 and rows[0]["burr"] is True
    assert rows[0]["alert_threshold"] == 0.40
    burr_md = (tmp_path / ("burr_%s.md" % stamp)).read_text(encoding="utf-8")
    assert "毛刺节" in burr_md
    assert "http://arxiv.org/abs/2608.5555v1" in burr_md      # full-text link required
    assert "author:marta" in burr_md and "title:switch" in burr_md


def test_burr_file_written_even_when_empty(monkeypatch, tmp_path):
    code, stamp = run_main(monkeypatch, tmp_path,
                           lambda url, **kw: atom([]) if "arxiv" in url else s2([]))
    assert code == 0
    burr_md = (tmp_path / ("burr_%s.md" % stamp)).read_text(encoding="utf-8")
    assert "本轮无毛刺命中" in burr_md


# --------------------------------------------------------------------------
# dedup
# --------------------------------------------------------------------------

def test_same_paper_from_two_keywords_is_one_row_with_merged_keywords(monkeypatch, tmp_path):
    def responder(url, **kw):
        if "arxiv" in url:
            return atom([{"id": "http://arxiv.org/abs/2608.7777v1", "title": "Shared"}])
        return s2([])
    code, stamp = run_main(monkeypatch, tmp_path, responder)
    rows = read_jsonl(tmp_path, stamp)
    assert len(rows) == 1
    # every keyword leg returned it; the row records more than one of them
    assert "," in rows[0]["keyword"]


def test_cross_source_dedup_by_title(monkeypatch, tmp_path):
    def responder(url, **kw):
        if "arxiv" in url:
            return atom([{"id": "http://arxiv.org/abs/2608.8888v1", "title": "Same Paper"}])
        return s2([paper(title="Same  Paper", paperId="zz")])
    code, stamp = run_main(monkeypatch, tmp_path, responder)
    assert len(read_jsonl(tmp_path, stamp)) == 1


def test_seen_registry_suppresses_on_second_run_and_full_overrides(monkeypatch, tmp_path):
    responder = lambda url, **kw: (
        atom([{"id": "http://arxiv.org/abs/2608.9999v1", "title": "Repeat"}])
        if "arxiv" in url else s2([]))
    code, stamp = run_main(monkeypatch, tmp_path, responder)
    assert len(read_jsonl(tmp_path, stamp)) == 1
    assert (tmp_path / scan.SEEN_NAME).exists()

    code, stamp = run_main(monkeypatch, tmp_path, responder)
    assert code == 0 and read_jsonl(tmp_path, stamp) == []

    code, stamp = run_main(monkeypatch, tmp_path, responder, argv=["--full"])
    assert len(read_jsonl(tmp_path, stamp)) == 1


def test_full_run_does_not_write_seen_registry(monkeypatch, tmp_path):
    run_main(monkeypatch, tmp_path,
             lambda url, **kw: atom([{"title": "X"}]) if "arxiv" in url else s2([]),
             argv=["--full"])
    assert not (tmp_path / scan.SEEN_NAME).exists()


# --------------------------------------------------------------------------
# failure semantics
# --------------------------------------------------------------------------

def test_total_source_failure_exits_nonzero(monkeypatch, tmp_path):
    def dead(url, **kw):
        raise IOError("down")
    monkeypatch.setattr(scan, "http_get", dead)
    assert scan.main(["--out-dir", str(tmp_path)]) == 1
    assert not list(tmp_path.glob("hits_*.jsonl"))       # no green-looking output


def test_partial_failure_still_reports_and_records_the_error(monkeypatch, tmp_path):
    def half_dead(url, **kw):
        if "semanticscholar" in url:
            raise IOError("s2 down")
        return atom([{"title": "Survivor", "id": "http://arxiv.org/abs/2608.4444v1"}])
    code, stamp = run_main(monkeypatch, tmp_path, half_dead)
    assert code == 0
    assert len(read_jsonl(tmp_path, stamp)) == 1
    assert "s2 down" in (tmp_path / ("burr_%s.md" % stamp)).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# output surface
# --------------------------------------------------------------------------

def test_csv_header_and_ssrn_urls(monkeypatch, tmp_path):
    code, stamp = run_main(monkeypatch, tmp_path,
                           lambda url, **kw: atom([]) if "arxiv" in url else s2([]))
    header = (tmp_path / ("hits_%s.csv" % stamp)).read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",") == ["标题", "作者", "日期", "摘要", "链接", "来源",
                                 "毛刺", "ALERT阈值", "关键词"]
    ssrn = (tmp_path / ("ssrn_manual_%s.txt" % stamp)).read_text(encoding="utf-8")
    urls = [l for l in ssrn.splitlines() if l.startswith("http")]
    assert len(urls) == len(scan.KEYWORDS)


def test_keyword_list_is_bilingual_and_carries_the_manual_phrases():
    assert "ETF basket comovement announcement" in scan.KEYWORDS_EN
    assert "ETF replication switch comovement" in scan.KEYWORDS_EN
    assert len(scan.KEYWORDS_EN) == 6 and len(scan.KEYWORDS_ZH) == 6
    assert scan.KEYWORDS == scan.KEYWORDS_EN + scan.KEYWORDS_ZH


def test_ssrn_leg_generates_urls_only_never_parses(monkeypatch):
    """SSRN has no public API; the spec forbids inventing one."""
    urls = scan.ssrn_manual_urls()
    assert all(u.startswith("https://www.ssrn.com/") for u in urls)
    assert len(urls) == len(scan.KEYWORDS)
