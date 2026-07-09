"""L1 client: response parsing, the sentinel fence, token-based costing, and the
full live batch flow (with the vendor POST mocked — no network)."""
import json
import models
import budget
import dispatch


# --- pure functions --------------------------------------------------------

def test_parse_answers_plain():
    assert models.parse_answers('{"a": "1", "b": "2"}') == {"a": "1", "b": "2"}


def test_parse_answers_tolerates_fence_and_prose():
    txt = "Sure:\n```json\n{\"S1\": \"4\"}\n```\nhope that helps"
    assert models.parse_answers(txt) == {"S1": "4"}


def test_parse_answers_garbage_returns_empty():
    assert models.parse_answers("no json here") == {}
    assert models.parse_answers("") == {}


def test_parse_answers_outer_map_beats_inner_rows():
    """A well-formed reply whose values are row-objects must return the outer
    id->answer map, not the first nested row."""
    txt = '{"i1": {"对象": "sACRED", "结论": "x", "备注": "y"}, "S1": "2025-08"}'
    got = models.parse_answers(txt)
    assert set(got) == {"i1", "S1"}


def test_parse_answers_truncated_reply_still_yields_something():
    # mid-JSON truncation (the live E2-T1-facts failure): outer map never
    # closes; the best inner object comes back so the post-mortem shows WHAT
    # was answered — the missing sentinels still void the batch.
    txt = '{"i1": [{"对象": "sACRED", "结论": "发行方直喂"}, {"对象": "mF-ONE", "结'
    got = models.parse_answers(txt)
    assert got.get("对象") == "sACRED"


def test_verify_sentinels():
    s = [{"id": "S1", "expect": "4"}, {"id": "S2", "expect": "Paris"}]
    assert models.verify_sentinels({"S1": "4", "S2": "Paris"}, s) == (True, [])
    ok, bad = models.verify_sentinels({"S1": "5", "S2": "Paris"}, s)
    assert not ok and bad == ["S1"]


def test_verify_sentinels_tolerant_but_not_loose():
    s = [{"id": "S1", "expect": "4"}, {"id": "S2", "expect": "Paris"}]
    # tolerant of case / punctuation / mild chattiness
    assert models.verify_sentinels({"S1": "4", "S2": "The capital is Paris."}, s)[0]
    assert models.verify_sentinels({"S1": 4, "S2": " paris "}, s)[0]
    # but a short numeric answer must be exact: '42' must not satisfy '4'
    assert models.verify_sentinels({"S1": "42", "S2": "Paris"}, s) == (False, ["S1"])
    # the old-bug case: a literal echo of the prompt is still caught
    assert not models.verify_sentinels({"S1": "2+2", "S2": "capital of France"}, s)[0]


def test_estimate_cost():
    # deepseek input price 0.5 ¥/1M -> 1M prompt tokens = 0.5
    assert abs(models.estimate_cost("deepseek", {"prompt_tokens": 1_000_000}) - 0.5) < 1e-9
    assert models.estimate_cost("gemini_free", {"prompt_tokens": 1_000_000}) == 0.0
    assert models.estimate_cost("deepseek", {}) == 0.0


def test_dispatch_dry_run_needs_no_key():
    ok, res = models.dispatch("kimi", "hello", dry_run=True)
    assert ok and "DRY-RUN" in res["text"]


# --- full live flow, vendor POST mocked ------------------------------------

def _mock_openai(text, usage):
    def fake(url, key, model, prompt):
        return True, {"text": text, "usage": usage}
    return fake


def test_live_batch_done_logs_cost_and_writes_output(monkeypatch, tmp_path):
    monkeypatch.setattr(models, "_post_openai",
                        _mock_openai('{"d1":"done","S1":"4","S2":"Paris"}',
                                     {"prompt_tokens": 2_000_000, "completion_tokens": 0}))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    monkeypatch.setattr(budget, "LOG", tmp_path / "spend.jsonl")
    out = tmp_path / "ans.json"

    status, detail, answers = dispatch.run_batch(
        "deepseek", [{"id": "d1", "prompt": "do"}], dispatch.SMOKE_SENTINELS,
        est_cost=0.0, live=True, out=str(out))

    assert status == "DONE"
    assert answers["d1"] == "done"
    assert abs(budget.today_spend() - 1.0) < 1e-9          # 0.5¥/1M * 2M = 1.0 logged
    assert json.loads(out.read_text())["d1"] == "done"


def test_live_batch_voids_on_bad_sentinel_and_logs_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(models, "_post_openai",
                        _mock_openai('{"d1":"x","S1":"WRONG","S2":"Paris"}', {}))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    monkeypatch.setattr(budget, "LOG", tmp_path / "spend.jsonl")

    status, _, answers = dispatch.run_batch(
        "deepseek", [{"id": "d1", "prompt": "do"}], dispatch.SMOKE_SENTINELS, live=True)

    assert status == "VOID-SENTINEL"
    assert answers is None
    assert budget.today_spend() == 0.0                     # voided batch is not billed


def test_truncated_reply_voids_with_diagnosis(monkeypatch, tmp_path):
    """finish_reason=length must show up in the VOID detail and the .void.json
    post-mortem — 'sentinels failed' alone sent us hunting wrong causes live."""
    monkeypatch.setattr(models, "dispatch",
                        lambda *a, **k: (True, {"text": '{"d1": "partial',
                                                "usage": {"completion_tokens": 1025},
                                                "finish_reason": "length"}))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    monkeypatch.setattr(budget, "LOG", tmp_path / "spend.jsonl")
    out = tmp_path / "ans.json"

    status, detail, _ = dispatch.run_batch(
        "deepseek", [{"id": "d1", "prompt": "do"}], dispatch.SMOKE_SENTINELS,
        live=True, out=str(out))

    assert status == "VOID-SENTINEL"
    assert "TRUNCATED" in detail
    void = json.loads((tmp_path / "ans.void.json").read_text())
    assert void["finish_reason"] == "length"
    assert not out.exists()


def test_live_batch_blocked_by_budget(monkeypatch, tmp_path):
    monkeypatch.setattr(budget, "LOG", tmp_path / "spend.jsonl")
    monkeypatch.setattr(budget, "DAILY_CAP", 1.0)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    status, why, _ = dispatch.run_batch(
        "deepseek", [{"id": "d1", "prompt": "do"}], dispatch.SMOKE_SENTINELS,
        est_cost=5.0, live=True)                             # 5 > daily cap 1
    assert status == "SKIP-BUDGET" and "daily cap" in why


# --- kimi $web_search builtin round-trip ------------------------------------

def _search_then_answer(responses):
    """Return a fake _post_json that pops canned responses in order."""
    seq = list(responses)

    def fake(url, key, payload):
        # every leg must declare the builtin tool, ask for enough output room
        # (vendor default ~1024 truncated a live batch), and echo tool messages
        assert payload["tools"] == models.WEB_SEARCH_TOOLS
        assert payload["max_tokens"] == models.MAX_OUTPUT_TOKENS
        return seq.pop(0)
    return fake


def test_openai_path_sets_max_tokens_and_reports_finish_reason(monkeypatch):
    seen = {}

    def fake(url, key, payload):
        seen.update(payload)
        return {"choices": [{"finish_reason": "length",
                             "message": {"content": '{"i1": "cut off'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 1025}}

    monkeypatch.setattr(models, "_post_json", fake)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    ok, res = models.dispatch("deepseek", "batch", dry_run=False)
    assert ok
    assert seen["max_tokens"] == models.MAX_OUTPUT_TOKENS
    assert res["finish_reason"] == "length"          # dispatch.py surfaces this


def test_kimi_web_search_round_trip(monkeypatch):
    tool_leg = {
        "choices": [{"finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": "",
            "tool_calls": [{"id": "c1", "type": "builtin_function",
                            "function": {"name": "$web_search",
                                         "arguments": '{"query": "NAV publish frequency"}'}}]}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10},
    }
    final_leg = {
        "choices": [{"finish_reason": "stop",
                     "message": {"role": "assistant", "content": '{"i1": "daily"}'}}],
        "usage": {"prompt_tokens": 300, "completion_tokens": 20},
    }
    calls = []
    real_fake = _search_then_answer([tool_leg, final_leg])

    def spy(url, key, payload):
        calls.append(payload)
        return real_fake(url, key, payload)

    monkeypatch.setattr(models, "_post_json", spy)
    monkeypatch.setenv("KIMI_API_KEY", "x")
    ok, res = models.dispatch("kimi", "verify things", dry_run=False, web_search=True)
    assert ok and res["text"] == '{"i1": "daily"}'
    # usage summed across legs + one search counted
    assert res["usage"] == {"prompt_tokens": 400, "completion_tokens": 30, "search_count": 1}
    # second leg must carry the echoed tool result (arguments as-is)
    tool_msgs = [m for m in calls[1]["messages"] if m.get("role") == "tool"]
    assert tool_msgs == [{"role": "tool", "tool_call_id": "c1", "name": "$web_search",
                          "content": '{"query": "NAV publish frequency"}'}]


def test_kimi_web_search_cost_includes_search_fee():
    usage = {"prompt_tokens": 1_000_000, "completion_tokens": 0, "search_count": 2}
    # kimi: 12¥/1M input -> 12.0, plus 2 searches
    assert abs(models.estimate_cost("kimi", usage) - (12.0 + 2 * models.KIMI_SEARCH_FEE)) < 1e-9


def test_web_search_rejected_for_non_kimi(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    ok, res = models.dispatch("deepseek", "x", dry_run=False, web_search=True)
    assert not ok and "only wired for kimi" in res["error"]


# --- gemini google_search grounding ------------------------------------------

def test_gemini_grounded_dispatch(monkeypatch):
    """web_search=True must declare the google_search tool, send the key in the
    x-goog-api-key header (never the URL), join multi-part replies, and surface
    the executed query count as usage['search_count']."""
    seen = {}

    def fake_post(url, key, payload, extra_headers=None):
        seen.update(url=url, key=key, payload=payload, headers=extra_headers)
        return {"candidates": [{
                    "content": {"parts": [{"text": '{"i1": '}, {"text": '"daily"}'}]},
                    "groundingMetadata": {"webSearchQueries": ["q1", "q2"]}}],
                "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 5}}

    monkeypatch.setattr(models, "_post_json", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "sekrit")
    ok, res = models.dispatch("gemini_free", "verify things", dry_run=False, web_search=True)
    assert ok and res["text"] == '{"i1": "daily"}'
    assert seen["payload"]["tools"] == [{"google_search": {}}]
    assert seen["headers"] == {"x-goog-api-key": "sekrit"}
    assert "sekrit" not in seen["url"]              # key must never ride the URL
    assert res["usage"] == {"prompt_tokens": 50, "completion_tokens": 5, "search_count": 2}


def test_gemini_ungrounded_has_no_tools(monkeypatch):
    def fake_post(url, key, payload, extra_headers=None):
        assert "tools" not in payload
        return {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}

    monkeypatch.setattr(models, "_post_json", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    ok, res = models.dispatch("gemini_free", "x", dry_run=False)
    assert ok and "search_count" not in res["usage"]


def test_gemini_max_tokens_maps_to_length(monkeypatch):
    """Gemini says MAX_TOKENS where OpenAI says length — dispatch.py's
    truncation diagnosis must fire for both vendors."""
    def fake_post(url, key, payload, extra_headers=None):
        return {"candidates": [{"content": {"parts": [{"text": '{"x": "cut'}]},
                                "finishReason": "MAX_TOKENS"}]}

    monkeypatch.setattr(models, "_post_json", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    ok, res = models.dispatch("gemini_free", "x", dry_run=False)
    assert ok and res["finish_reason"] == "length"


def test_gemini_grounded_searches_bill_zero():
    # the per-search fee is kimi's; gemini free-tier grounding must stay ¥0
    assert models.estimate_cost(
        "gemini_free", {"prompt_tokens": 1_000_000, "search_count": 5}) == 0.0


# --- retry/backoff fast-fail on exhausted billing ----------------------------

class _FakeResp:
    def __init__(self, status, body="", payload=None):
        self.status_code = status
        self.text = body
        self.headers = {}
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)


def _fake_requests(monkeypatch, responses, sleeps):
    import requests
    seq = list(responses)
    monkeypatch.setattr(requests, "post", lambda *a, **k: seq.pop(0))
    import time
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))


def test_rate_limit_429_is_retried(monkeypatch):
    sleeps = []
    _fake_requests(monkeypatch,
                   [_FakeResp(429, "You exceeded your current quota"),
                    _FakeResp(200, payload={"ok": True})], sleeps)
    assert models._post_json("http://x", "k", {}) == {"ok": True}
    assert sleeps == [20]                            # one backoff, then success


def test_depleted_credits_429_fails_fast(monkeypatch):
    """'prepayment credits are depleted' cannot succeed on retry — the run must
    fail immediately with the body surfaced, not sleep through 3 backoffs."""
    import pytest, requests
    sleeps = []
    _fake_requests(monkeypatch,
                   [_FakeResp(429, '{"error": {"message": "Your prepayment '
                                   'credits are depleted.", '
                                   '"status": "RESOURCE_EXHAUSTED"}}')], sleeps)
    with pytest.raises(requests.HTTPError, match="depleted"):
        models._post_json("http://x", "k", {})
    assert sleeps == []                              # zero retries, zero waiting


def test_web_search_round_limit(monkeypatch):
    tool_leg = {
        "choices": [{"finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": "",
            "tool_calls": [{"id": "c", "function": {"name": "$web_search",
                                                    "arguments": "{}"}}]}}],
        "usage": {},
    }
    monkeypatch.setattr(models, "_post_json",
                        _search_then_answer([tool_leg] * models.MAX_SEARCH_ROUNDS))
    monkeypatch.setenv("KIMI_API_KEY", "x")
    ok, res = models.dispatch("kimi", "x", dry_run=False, web_search=True)
    assert not ok and "exceeded" in res["error"]
