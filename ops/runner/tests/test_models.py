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
        # every leg must declare the builtin tool and echo prior tool messages
        assert payload["tools"] == models.WEB_SEARCH_TOOLS
        return seq.pop(0)
    return fake


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
