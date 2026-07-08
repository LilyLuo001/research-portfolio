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
"""
import os

ENDPOINTS = {
    "deepseek":   ("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1/chat/completions"),
    "deepseek_r": ("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1/chat/completions"),
    "kimi":       ("KIMI_API_KEY",     "https://api.moonshot.cn/v1/chat/completions"),
    "glm":        ("GLM_API_KEY",      "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
    "qwen":       ("QWEN_API_KEY",     "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
    "gemini_free":("GEMINI_API_KEY",   "https://generativelanguage.googleapis.com/v1beta/models"),
}

# model id per worker tier (edit to the vintages you actually provisioned)
MODELS = {
    "deepseek":   "deepseek-chat",
    "deepseek_r": "deepseek-reasoner",
    "kimi":       "moonshot-v1-32k",
    "glm":        "glm-4-flash",
    "qwen":       "qwen-plus",
    "gemini_free":"gemini-2.5-flash",
}

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


def dispatch(worker, prompt, sentinels=None, dry_run=True):
    """Send one batch. Returns (ok, {"text", "usage"}) or (False, {"error"}).
    Dry-run (or missing key) returns a stub so the scheduler runs offline."""
    key_env, url = ENDPOINTS[worker]
    key = os.getenv(key_env)
    if dry_run or not key:
        return True, {"text": f"[DRY-RUN {worker}] would POST {len(prompt)} chars to {url}",
                      "usage": {}}
    try:
        if worker == "gemini_free":
            return _post_gemini(url, key, prompt)
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


def _post_gemini(url, key, prompt):
    import requests
    endpoint = f"{url}/{MODELS['gemini_free']}:generateContent?key={key}"
    r = requests.post(endpoint,
                      json={"contents": [{"parts": [{"text": SYSTEM + "\n\n" + prompt}]}]},
                      timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json()
    text = d["candidates"][0]["content"]["parts"][0]["text"]
    um = d.get("usageMetadata", {})
    usage = {"prompt_tokens": um.get("promptTokenCount", 0),
             "completion_tokens": um.get("candidatesTokenCount", 0)}
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
    """¥ cost of one call from its token usage. Missing usage -> 0.0."""
    p = PRICES.get(worker)
    if not p or not usage:
        return 0.0
    pin = usage.get("prompt_tokens", 0) or 0
    pout = usage.get("completion_tokens", 0) or 0
    return (pin * p[0] + pout * p[1]) / 1_000_000.0
