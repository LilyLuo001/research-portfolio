# DAX Gate 1 dated-event evidence audit

**Audit date:** 2026-08-19
**Scope:** the nine `pending_second_date_locator` rows in the registry at base
`c84a6e5f2b9b13caa93bb79b8d946dd66197d5e6`
**Decision rule:** a pass requires a second dated primary/official locator that
independently establishes both the event date and the treatment-relevant fact.
Identity-only model pages, deprecation dates, current undated pricing pages,
search snippets, and secondary reporting do not pass.

Price verification is adjudicated separately. A `pass` below closes only the
event-date locator gate; it does not make a candidate retained, prove historical
absolute prices, pass W4 measurement, or pass the W5 dose threshold.

## Approval evidence table

| Row ID | Event | Current evidence at base | Proposed second locator | Locator date | Exact fact established | Status | Remaining action |
|---|---|---|---|---|---|---|---|
| `GPT4_TURBO_PREVIEW` | GPT-4 Turbo preview / `gpt-4-1106-preview` | [API changelog](https://developers.openai.com/api/docs/changelog) + deprecations page (retirement only) | [OpenAI DevDay announcement](https://openai.com/index/new-models-and-developer-products-announced-at-devday/) | 2023-11-06 | On the dated page OpenAI launches GPT-4 Turbo preview, identifies `gpt-4-1106-preview` as the API model, and states the lower-price treatment. | pass | Mark date verified. Keep shutdown conflict provenance and W4 availability test; rely on W2, not this page alone, for absolute price history. |
| `O1_PREVIEW_LAUNCH` | o1-preview API launch | [API changelog](https://developers.openai.com/api/docs/changelog) + deprecations page (retirement only) | [Learning to reason with LLMs](https://openai.com/index/learning-to-reason-with-llms/) | 2024-09-12 | The dated OpenAI release states that o1-preview was released for immediate use in ChatGPT and by trusted API users. | pass | Mark date verified. Preserve the signed stand-in and propagated-error requirement for W4. |
| `GPT45_PREVIEW_LAUNCH` | GPT-4.5 research preview | [API changelog](https://developers.openai.com/api/docs/changelog) + deprecations page (retirement only) | [Introducing GPT-4.5](https://openai.com/index/introducing-gpt-4-5/) | 2025-02-27 | The dated OpenAI post releases the GPT-4.5 research preview and states that it is being previewed in the Chat Completions, Assistants, and Batch APIs. | pass | Mark the date verified but preserve `excluded_binding`, `n_a`, and `NOT_APPLICABLE`; evidence cannot undo the no-stand-in exclusion. |
| `O3_PRICE_CUT` | o3 API price cut | [API changelog](https://developers.openai.com/api/docs/changelog) + current undated pricing page | [Official OpenAI Developer Community announcement](https://community.openai.com/t/o3-is-80-cheaper-and-introducing-o3-pro/1284925) | 2025-06-10 | The dated official announcement says the o3 price was cut 80%, gives $2 input / $8 output per 1M tokens, and says it was then in effect. | pass | Mark date verified. W2 remains the independent absolute before/after price channel; W5 must still test dose. |
| `GPT54_MINI_NANO_LAUNCH` | GPT-5.4 mini and nano API launch | [API changelog](https://developers.openai.com/api/docs/changelog) + undated mini model page | [Introducing GPT-5.4 mini and nano](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) | 2026-03-17 | The dated OpenAI post says both models were released that day; mini was available in the API, Codex, and ChatGPT, and nano was API-only. | pass | Mark date verified. Keep W2 price verification separate and apply W5 mechanical inclusion rule. |
| `GPT55_LAUNCH` | GPT-5.5 API launch | [API changelog](https://developers.openai.com/api/docs/changelog) dated 2026-04-24 + model page/snapshot dated 2026-04-23 | [Introducing GPT-5.5](https://openai.com/index/introducing-gpt-5-5/) | 2026-04-24 API update; original post 2026-04-23 | The official post was published for the product launch on April 23 and explicitly updated that GPT-5.5 and GPT-5.5 Pro became available in the API on April 24. | pass | Mark API date verified **without resolving away the conflict**: retain `api_effective_date=2026-04-24`, `date_conflict=2026-04-23`, and the dated snapshot. |
| `GPT56_FAMILY_LAUNCH` | GPT-5.6 Sol, Terra, and Luna launch | [API changelog](https://developers.openai.com/api/docs/changelog) + undated Sol model page | [GPT-5.6 launch post](https://openai.com/index/gpt-5-6/) | 2026-07-09 | The dated OpenAI post launches the three-model family for general availability and states that developers can access all three in the API. | pass | Mark date verified. This clears only the source gate; keep `candidate` until W5 establishes a qualifying dose. |
| `GPT56_PRICE_CUT` | GPT-5.6 Terra/Luna price cut | [API changelog](https://developers.openai.com/api/docs/changelog) + current undated pricing page | [Dated update to GPT-5.6 launch post](https://openai.com/index/gpt-5-6/) | 2026-07-30 | The OpenAI post explicitly records the July 30 update: Luna price reduced 80% and Terra 20%. | pass | Mark date verified. Keep W2 absolute-price verification separate and retain only if W5 passes the frozen dose rule. |
| `GPT56_FAST_LONG_CONTEXT` | Long-context support in API Fast mode | [API changelog](https://developers.openai.com/api/docs/changelog) + current [Fast-mode guide](https://developers.openai.com/api/docs/guides/fast-mode) | No qualifying second locator found; the current guide was rejected because it dates only the July 30 rename, not the August 5 long-context change. | — | The guide currently shows long-context Fast-mode support and rates, but independently establishes neither the August 5 event date nor that exact change on that date. | pending | Leave `pending_second_date_locator` and `BLOCKED_SOURCE_THEN_W5_FILL`. Obtain a stable dated official announcement/commit/archive that explicitly ties long-context Fast-mode support to 2026-08-05, or classify the row source-failed at Gate 1. |

## Approval disposition

- Date-locator gate passed: eight rows (`GPT4_TURBO_PREVIEW`,
  `O1_PREVIEW_LAUNCH`, `GPT45_PREVIEW_LAUNCH`, `O3_PRICE_CUT`,
  `GPT54_MINI_NANO_LAUNCH`, `GPT55_LAUNCH`, `GPT56_FAMILY_LAUNCH`, and
  `GPT56_PRICE_CUT`).
- Still evidence-excluded: `GPT56_FAST_LONG_CONTEXT`.
- Still binding-excluded despite a dated locator: `GPT45_PREVIEW_LAUNCH`.
- No row was promoted to `eligible`. The newly verified candidates still face
  the frozen W4/W5 measurement and dose rules before retention.

No outcome data, raw/private data, search snippets, or secondary press reports
were used. No web content was copied into the repository; only stable official
locators and the adjudication are recorded.
