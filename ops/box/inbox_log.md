
## 2026-07-09T09:30:01Z — inbox edf5f8fc093a @ git ff99b11
```
== where am I ==
ff99b11 Merge branch 'main' of https://github.com/LilyLuo001/research-portfolio
aaec175 Add bu-scc MCP server: local Claude Code hands on the SCC (ControlMaster, no passwords)
Python 3.6.8
== which kimi model ids can this key use ==
moonshot-v1-128k-vision-preview
moonshot-v1-auto
moonshot-v1-32k
moonshot-v1-32k-vision-preview
kimi-k2.7-code-highspeed
moonshot-v1-128k
moonshot-v1-8k-vision-preview
moonshot-v1-8k
kimi-k2.6
kimi-k2.5
kimi-k2.7-code
== clear stale strikes (billing-era + contested-sentinel voids) ==
cleared 0 recorded attempt(s) for E2-T1-facts-B
cleared 0 recorded attempt(s) for E2-T6b-nav
== live L1 pass (gemini is free + fence-fixed; kimi will ERROR until KIMI_MODEL is pinned — no strikes) ==
L1 driver — 6 ready L1 task(s), mode=LIVE
  ✖ P1-T0-crash-B        [ERROR] kimi: HTTPError: 404 Client Error: Not Found for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"Not found the model kimi-latest or Permission denied","type":"resource_not_found_error"}}
  ✓ DAX-W0.5-legwork     output already at DAX-W0.5-legwork.json — not re-sending (validate + --complete it, or delete the file / --force to re-run)
  ✖ E2-T1-facts          [ERROR] kimi: HTTPError: 404 Client Error: Not Found for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"Not found the model kimi-latest or Permission denied","type":"resource_not_found_error"}}
  ✓ E2-T1-facts-B        [DONE] gemini_free: 4 items + 2 sentinels OK (LIVE ¥0.000)
  · E2-T6b-nav           manual channel — run: python ops/l1/gemini_helper.py E2-T6b-nav
  ✖ E2-T9b-scenarios     [ERROR] kimi: HTTPError: 404 Client Error: Not Found for url: https://api.moonshot.cn/v1/chat/completions :: {"error":{"message":"Not found the model kimi-latest or Permission denied","type":"resource_not_found_error"}}
  spent today: 0.501 / 70 daily cap (MTD 1.4 / 500)
  1 batch(es) written to ops/l1/out/ — validate + gate downstream before --complete.
[exit: 0]
```
