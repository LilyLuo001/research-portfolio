#!/usr/bin/env python3
"""
models.py — the ONLY place that talks to non-Anthropic model APIs (L1).

Thin HTTP client, no agent framework (every framework is a new mid-task failure
source). Uses YOUR OWN API keys under each vendor's commercial terms — the
compliant path for automated/24-7 work. Claude is NEVER called here.

DeepSeek, Kimi (Moonshot), GLM (Zhipu) and Qwen (Alibaba) all speak the
OpenAI-compatible /chat/completions shape; Gemini has its own generateContent
shape. `dispatch()` returns (ok, {"text", "usage"}); on any error it returns
(False, {"error": ...}) so the batch is voided rather than crashing the box.

`requests` is imported lazily inside the POST helpers so this module (and its
pure-function tests) import fine on a machine without it.

Env keys: DEEPSEEK_API_KEY, KIMI_API_KEY, GLM_API_KEY, QWEN_API_KEY,
GEMINI_API_KEY (Gemini free tier = ¥0 cross-vendor channel B).

Kimi `$web_search`: implemented as the Moonshot builtin-function round-trip —
declare {"type": "builtin_function", "function": {"name": "$web_search"}}; when
the model answers finish_reason=="tool_calls", echo tool_call.function.arguments
back as the tool message content (the search itself runs server-side), and loop
until a normal finish. Pass web_search=True to dispatch() (spec key
`web_search: true` in ops/l1/<task>.yaml). Each search leg bills a per-call fee
on top of tokens (KIMI_SEARCH_FEE, ¥). Kimi host/model are env-overridable
(KIMI_BASE_URL, KIMI_MODEL) — the platform is rebranding moonshot.cn → kimi.com,
so verify both against https://platform.kimi.com/docs before going live.

Gemini grounding (channel-B web tasks): pass web_search=True and the
generateContent payload declares {"google_search": {}} — Google runs the
searches server-side and the response carries groundingMetadata (we surface
len(webSearchQueries) as usage["search_count"]; free tier bills ¥0, but the
free grounding quota is LIMITED PER DAY — verify current limits at
ai.google.dev/pricing before arming a nightly batch). If the quota runs out,
set `manual: true` in the spec and fall back to ops/l1/gemini_helper.py.
"""
import os

ENDPOINTS = {
    "deepseek":   ("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1/chat/completions"),
    "deepseek_r": ("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1/chat/completions"),
    "kimi":       ("KIMI_API_KEY",
                   os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1").rstrip("/")
                   + "/chat/completions"),
    "glm":        ("GLM_API_KEY",      "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
    "qwen":       ("QWEN_API_KEY",     "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
    "gemini_free":("GEMINI_API_KEY",   "https://generativelanguage.googleapis.com/v1beta/models"),
}

# model id per worker tier (edit to the vintages you actually provisioned)
MODELS = {
    "deepseek":   "deepseek-chat",
    "deepseek_r": "deepseek-reasoner",
    "kimi":       os.getenv("KIMI_MODEL", "moonshot-v1-32k"),
    "glm":        "glm-4-flash",
    "qwen":       "qwen-plus",
    "gemini_free":"gemini-2.5-flash",
}

# Moonshot builtin web search: per-invocation fee on top of tokens (¥).
# Public docs quote ~$0.005/search; verify current billing before going live.
KIMI_SEARCH_FEE = float(os.getenv("KIMI_SEARCH_FEE", "0.04"))
WEB_SEARCH_TOOLS = [{"type": "builtin_function", "function": {"name": "$web_search"}}]
MAX_SEARCH_ROUNDS = 8   # hard stop so a confused model can't loop searches forever

# APPROXIMATE prices, ¥ per 1M tokens as (input, output). These feed budget.py's
# caps only — VERIFY against each vendor's current pricing and tune freely; they
# do not need to be exact, just the right order of magnitude.
PRICES = {
    "deepseek":   (0.5, 2.0),
    "deepseek_r": (1.0, 8.0),
    "kimi":       (12.0, 12.0),
    "glm":        (0.1, 0.1),
    "qwen":       (0.8, 2.0),
    "gemini_free":(0.0, 0.0),   # free tier
}

SYSTEM = ("You are a batch worker. Respond with ONLY a single JSON object mapping "
          "each input item's id to its answer. No prose, no markdown fences.")

TIMEOUT = 120


def dispatch(worker, prompt, sentinels=None, dry_run=True, web_search=False):
    """Send one batch. Returns (ok, {"text", "usage"}) or (False, {"error"}).
    Dry-run (or missing key) returns a stub so the scheduler runs offline.
    web_search=True (kimi only) runs the $web_search builtin round-trip; the
    returned usage carries an extra "search_count" for cost accounting."""
    key_env, url = ENDPOINTS[worker]
    key = os.getenv(key_env)
    if dry_run or not key:
        tag = " +$web_search" if web_search else ""
        return True, {"text": f"[DRY-RUN {worker}{tag}] would POST {len(prompt)} chars to {url}",
                      "usage": {}}
    try:
        if worker == "gemini_free":
            return _post_gemini(url, key, prompt, web_search=web_search)
        if web_search:
            if worker != "kimi":
                return False, {"error": f"web_search is only wired for kimi and "
                                        f"gemini_free, not {worker}"}
            return _post_kimi_search(url, key, MODELS[worker], prompt)
        return _post_openai(url, key, MODELS[worker], prompt)
    except Exception as e:  # network / HTTP / parse — void the batch, don't crash
        return False, {"error": f"{type(e).__name__}: {e}"}


def _post_openai(url, key, model, prompt):
    import requests
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0,
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": prompt}]},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    d = r.json()
    return True, {"text": d["choices"][0]["message"]["content"], "usage": d.get("usage", {})}


def _post_json(url, key, payload):
    import requests
    r = requests.post(url,
                      headers={"Authorization": f"Bearer {key}",
                               "Content-Type": "application/json"},
                      json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _post_kimi_search(url, key, model, prompt):
    """Moonshot builtin $web_search round-trip (see module docstring).

    The model decides when to search; each tool_calls turn is answered by
    echoing the call's own `arguments` back as the tool result — the search
    executes on Moonshot's side. Token usage is summed across all legs and
    the number of search invocations is returned as usage["search_count"]."""
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt}]
    total = {"prompt_tokens": 0, "completion_tokens": 0, "search_count": 0}
    for _ in range(MAX_SEARCH_ROUNDS):
        d = _post_json(url, key, {"model": model, "temperature": 0,
                                  "messages": messages, "tools": WEB_SEARCH_TOOLS})
        u = d.get("usage", {}) or {}
        total["prompt_tokens"] += u.get("prompt_tokens", 0) or 0
        total["completion_tokens"] += u.get("completion_tokens", 0) or 0
        choice = d["choices"][0]
        msg = choice["message"]
        if choice.get("finish_reason") == "tool_calls":
            messages.append(msg)
            for tc in msg.get("tool_calls") or []:
                name = tc.get("function", {}).get("name", "")
                args = tc.get("function", {}).get("arguments", "{}")
                if name == "$web_search":
                    total["search_count"] += 1
                    content = args           # builtin: echo the arguments as-is
                else:
                    content = '{"error": "unsupported tool in this harness"}'
                messages.append({"role": "tool", "tool_call_id": tc.get("id"),
                                 "name": name, "content": content})
            continue
        return True, {"text": msg.get("content", ""), "usage": total}
    return False, {"error": f"web_search exceeded {MAX_SEARCH_ROUNDS} rounds without finishing"}


def _post_plain_json(endpoint, payload):
    import requests
    r = requests.post(endpoint, json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _post_gemini(url, key, prompt, web_search=False):
    """generateContent, optionally grounded with Google Search (see module
    docstring). Grounded replies may split across several parts and carry the
    executed queries in groundingMetadata.webSearchQueries."""
    endpoint = f"{url}/{MODELS['gemini_free']}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": SYSTEM + "\n\n" + prompt}]}]}
    if web_search:
        payload["tools"] = [{"google_search": {}}]
    d = _post_plain_json(endpoint, payload)
    cand = d["candidates"][0]
    text = "".join(p.get("text", "") for p in cand["content"]["parts"])
    um = d.get("usageMetadata", {})
    usage = {"prompt_tokens": um.get("promptTokenCount", 0),
             "completion_tokens": um.get("candidatesTokenCount", 0)}
    if web_search:
        gm = cand.get("groundingMetadata") or {}
        usage["search_count"] = len(gm.get("webSearchQueries") or [])
    return True, {"text": text, "usage": usage}


def parse_answers(text):
    """Pull the JSON answer-map out of a model response (tolerates stray prose or
    ```json fences). Returns {} if nothing parseable is found."""
    import re, json
    if not text:
        return {}
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def _norm(s):
    """Casefold and drop non-alphanumerics so 'Paris', 'paris.', ' PARIS ' all
    compare equal — tolerant of formatting without being so loose it lets a wrong
    answer through."""
    import re
    return re.sub(r"[^0-9a-z]+", "", str(s).lower())


def verify_sentinels(answers, sentinels):
    """Return (ok, bad_ids): a batch is trustworthy only if every known-answer
    sentinel came back correct. A sentinel passes when the normalized expected
    value equals the model's normalized answer, or (for multi-char answers) is
    contained in it — so a slightly chatty 'The capital is Paris' still passes,
    while a short numeric answer must match exactly (no '4' matching '42')."""
    bad = []
    for s in (sentinels or []):
        got = _norm(answers.get(s["id"], ""))
        exp = _norm(s["expect"])
        ok = got == exp or (len(exp) >= 3 and exp in got)
        if not ok:
            bad.append(s["id"])
    return (len(bad) == 0, bad)


def estimate_cost(worker, usage):
    """¥ cost of one call from its token usage. The per-search fee applies to
    kimi's $web_search legs only (usage['search_count']); Gemini free-tier
    grounded searches report a search_count too but bill ¥0."""
    if not usage:
        return 0.0
    p = PRICES.get(worker)
    cost = 0.0
    if p:
        pin = usage.get("prompt_tokens", 0) or 0
        pout = usage.get("completion_tokens", 0) or 0
        cost = (pin * p[0] + pout * p[1]) / 1_000_000.0
    if worker == "kimi":
        cost += (usage.get("search_count", 0) or 0) * KIMI_SEARCH_FEE
    return cost
