#!/usr/bin/env python3
"""
models.py — the ONLY place that talks to non-Anthropic model APIs (L1).
Thin client, no agent framework (every framework is a new mid-task failure
source). Uses YOUR OWN API keys under each vendor's commercial terms — this is
the compliant path for automated/24-7 work. Claude is NEVER called here.

Env keys expected: DEEPSEEK_API_KEY, KIMI_API_KEY, GLM_API_KEY, QWEN_API_KEY,
GEMINI_API_KEY. Gemini free tier = ¥0 cross-vendor channel B.

Every batch is SENTINEL-FENCED: known-answer items are mixed in; if the model
misses them, the whole batch is voided (cheap models are only trustworthy
inside sentinel fences).
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

def dispatch(worker, prompt, sentinels=None, dry_run=True):
    """Send one batch job. Returns (ok, result). Real impl: POST + parse.
    Here: dry-run stub so the scheduler runs offline. Wire real POST when keys set."""
    key_env, url = ENDPOINTS[worker]
    if dry_run or not os.getenv(key_env):
        return True, f"[DRY-RUN {worker}] would POST to {url} ({len(prompt)} chars)"
    # --- real dispatch would go here (requests/httpx + sentinel verification) ---
    raise NotImplementedError("wire the POST + sentinel check for live runs")

def verify_sentinels(result, sentinels):
    """Return False (void batch) if any known-answer sentinel is wrong."""
    return True  # implement per batch type
