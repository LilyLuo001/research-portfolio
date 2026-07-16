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
    # PIN KIMI_MODEL in ops/box/.env — run `python ops/runner/models.py --list
    # kimi` (with the key in env) to see which ids YOUR key can use, and pick
    # the newest K-series one. History: moonshot-v1-32k (2024-era) worked but
    # under-searched and fabricated dates; 'kimi-latest' 404'd on this account
    # ("Not found the model kimi-latest or Permission denied", 2026-07-09).
    "kimi":       os.getenv("KIMI_MODEL", "kimi-latest"),
    "glm":        "glm-4-flash",
    "qwen":       "qwen-plus",
    "gemini_free":"gemini-2.5-flash",
}

# Moonshot builtin web search: per-invocation fee on top of tokens (¥).
# Public docs quote ~$0.005/search; verify current billing before going live.
KIMI_SEARCH_FEE = float(os.getenv("KIMI_SEARCH_FEE", "0.04"))
WEB_SEARCH_TOOLS = [{"type": "builtin_function", "function": {"name": "$web_search"}}]
# Hard stop so a confused model can't loop searches forever. Sized for real
# batches: a spec like P1-T0-crash-B estimates "~a dozen searches" for its items
# ALONE, and the sentinels need their own lookups — at 8 the model runs dry
# before it can verify the fence. Cost stays capped by budget.py either way.
MAX_SEARCH_ROUNDS = int(os.getenv("MAX_SEARCH_ROUNDS", "24"))

# APPROXIMATE prices, ¥ per 1M tokens as (input, output). These feed budget.py's
# caps only — VERIFY against each vendor's current pricing and tune freely; they
# do not need to be exact, just the right order of magnitude.
PRICES = {
    "deepseek":   (0.5, 2.0),
    "deepseek_r": (1.0, 8.0),
    "kimi":       (12.0, 12.0),
    "glm":        (0.1, 0.1),
    "qwen":       (0.8, 2.0),
    "gemini_free":(2.2, 18.0),  # PAID key since 2026-07-17: 2.5-flash ash.30/\.50 per 1M x ~7.2 CNY
}

SYSTEM = ("You are a batch worker. Respond with ONLY a single JSON object mapping "
          "each input item's id to its answer. No prose, no markdown fences. "
          "Answer EVERY item, including the short check questions.")

TIMEOUT = 420  # kimi K2 web-search legs can exceed 120s (live 2026-07-09)

# Vendors cap completions LOW when max_tokens is unset (Moonshot ~1024 — seen
# live 2026-07: a 4-item batch truncated mid-JSON at completion_tokens=1025,
# never reached its sentinels, and voided). Ask for room explicitly.
MAX_OUTPUT_TOKENS = int(os.getenv("L1_MAX_TOKENS", "8192"))


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


# Transient statuses worth retrying overnight: rate limits (free-tier Gemini
# limits per-minute, so waits are tens of seconds) and vendor 5xx blips.
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
RETRY_BASE_DELAY = 20   # seconds; doubles per attempt (20, 40, 80)

# 429 bodies that mean "account/billing exhausted", not "slow down": retrying
# cannot succeed, so fail fast and surface the body (seen live 2026-07: Gemini
# "Your prepayment credits are depleted" — needed AI Studio billing, not a wait).
NO_RETRY_MARKERS = ("credits are depleted", "prepayment")


def _raise_with_body(r):
    """raise_for_status, but append the response body to the message. A bare
    '400 Bad Request' from an overnight run is undiagnosable the next morning;
    the vendor's error body (bad param, content filter, quota name) is the
    only thing that says WHY."""
    import requests
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        body = " ".join((r.text or "").split())[:400]
        raise requests.HTTPError(f"{e} :: {body}", response=r) from None


def _post_json(url, key, payload, extra_headers=None):
    """One JSON POST with retry/backoff on transient statuses. Honors a numeric
    Retry-After when the vendor sends one."""
    import time, requests
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if extra_headers:
        headers.update(extra_headers)
    delay = RETRY_BASE_DELAY
    for attempt in range(MAX_RETRIES + 1):
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        exhausted = (r.status_code == 429
                     and any(m in (r.text or "") for m in NO_RETRY_MARKERS))
        if r.status_code not in RETRY_STATUSES or exhausted or attempt == MAX_RETRIES:
            _raise_with_body(r)
            return r.json()
        try:
            wait = float(r.headers.get("Retry-After", ""))
        except ValueError:
            wait = delay
        time.sleep(min(wait, 120))
        delay *= 2


def _temperature(model):
    """Moonshot K2-series models reject any temperature except 1 (observed
    live 2026-07-09: 400 'invalid temperature: only 1 is allowed for this
    model'). Everything else gets 0 for determinism."""
    return 1 if model.startswith("kimi-k2") else 0


def _post_openai(url, key, model, prompt):
    d = _post_json(url, key,
                   {"model": model, "temperature": _temperature(model),
                    "max_tokens": MAX_OUTPUT_TOKENS,
                    "messages": [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": prompt}]})
    choice = d["choices"][0]
    return True, {"text": choice["message"]["content"], "usage": d.get("usage", {}),
                  "finish_reason": choice.get("finish_reason")}


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
        d = _post_json(url, key, {"model": model, "temperature": _temperature(model),
                                  "max_tokens": MAX_OUTPUT_TOKENS,
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
        return True, {"text": msg.get("content", ""), "usage": total,
                      "finish_reason": choice.get("finish_reason")}
    return False, {"error": f"web_search exceeded {MAX_SEARCH_ROUNDS} rounds without finishing"}


def _post_gemini(url, key, prompt, web_search=False):
    """generateContent, optionally grounded with Google Search (see module
    docstring). Grounded replies may split across several parts and carry the
    executed queries in groundingMetadata.webSearchQueries. The key travels in
    the x-goog-api-key header, NOT the URL query string — a ?key= URL is
    reproduced verbatim in every HTTPError message and ends up in terminal
    scrollback, night reports, and pasted logs."""
    endpoint = f"{url}/{MODELS['gemini_free']}:generateContent"
    payload = {"contents": [{"parts": [{"text": SYSTEM + "\n\n" + prompt}]}]}
    if web_search:
        payload["tools"] = [{"google_search": {}}]
    d = _post_json(endpoint, None, payload, extra_headers={"x-goog-api-key": key})
    cand = d["candidates"][0]
    text = "".join(p.get("text", "") for p in cand["content"]["parts"])
    um = d.get("usageMetadata", {})
    usage = {"prompt_tokens": um.get("promptTokenCount", 0),
             "completion_tokens": um.get("candidatesTokenCount", 0)}
    if web_search:
        gm = cand.get("groundingMetadata") or {}
        usage["search_count"] = len(gm.get("webSearchQueries") or [])
    fr = cand.get("finishReason")
    # normalize to the OpenAI-style value dispatch.py checks for truncation
    finish = "length" if fr == "MAX_TOKENS" else (fr.lower() if fr else None)
    return True, {"text": text, "usage": usage, "finish_reason": finish}


def parse_answers(text):
    """Pull the JSON answer-map out of a model response (tolerates stray prose or
    ```json fences). Strictly parses each '{'-rooted candidate; a successful
    parse consumes its whole span, so nested row-objects never shadow the outer
    answer-map (seen live: a reply truncated mid-JSON made 'first parseable {'
    return an inner per-asset row instead of the id->answer map). Among the
    outermost candidates, the one with the most keys wins. Returns {} if
    nothing parseable is found."""
    import json
    if not text:
        return {}
    dec = json.JSONDecoder()
    best = {}
    idx = text.find("{")
    while idx != -1:
        try:
            obj, end = dec.raw_decode(text, idx)
            if isinstance(obj, dict) and len(obj) > len(best):
                best = obj
            idx = text.find("{", end)
        except ValueError:
            idx = text.find("{", idx + 1)
    return best


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


def list_models(worker):
    """Ask the vendor which model ids THIS key can use. Vendors rebrand and
    gate models per account (live 2026-07: 'kimi-latest' 404'd with
    'Permission denied') — the /models endpoint is the ground truth, not docs
    or guesses. Returns a list of id strings; raises on HTTP errors."""
    import requests
    key_env, url = ENDPOINTS[worker]
    key = os.getenv(key_env)
    if not key:
        raise RuntimeError(f"no {key_env} in env — source ops/box/.env first")
    if worker == "gemini_free":
        r = requests.get(url, headers={"x-goog-api-key": key}, timeout=30)
        _raise_with_body(r)
        return [m.get("name", "") for m in r.json().get("models", [])]
    base = url.rsplit("/chat/completions", 1)[0]
    r = requests.get(f"{base}/models",
                     headers={"Authorization": f"Bearer {key}"}, timeout=30)
    _raise_with_body(r)
    return [m.get("id", "") for m in r.json().get("data", [])]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="L1 model-client utilities")
    ap.add_argument("--list", metavar="WORKER", choices=sorted(ENDPOINTS),
                    help="list the model ids this worker's API key can use "
                         "(needs the key in env; pin your pick via KIMI_MODEL etc.)")
    a = ap.parse_args()
    if a.list:
        for mid in list_models(a.list):
            marker = "  <- current default" if mid == MODELS.get(a.list) else ""
            print(f"{mid}{marker}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
