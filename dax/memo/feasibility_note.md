# DAX W0.5 — Vintage & GDPval-License Feasibility Note

_AMEND DAX-4 deliverable. Input to **DAX-GATE-feasibility** (PI signature
required; blocks W3 Mapping-A protocol and all W4 spend until signed).
Drafted 2026-07-10 from `dax/memo/w05_legwork_2026-07-10.md` (full row-level
tables + provenance live there; this note carries only the decision-relevant
facts). No content from the quarantined kimi output was used._

## Verdict proposed for PI signature

**CONDITIONAL GO**, on three conditions:

1. **W4 capability/cost panel API capture is deadline-bound.** Every
   still-accessible pre-2025 vintage has an announced shutdown:
   **2026-10-23** for the GPT-3.5/GPT-4/GPT-4-Turbo/GPT-4o/o1 snapshot
   families and **2026-12-11** for gpt-4.1/gpt-5/o3-mini and older gpt-5.4/
   5.5 snapshots. After 2026-10-23 the live-API measurement window for the
   core historical vintages is gone — W4 must be scheduled (and its budget
   flagged to the funder, per queue note) so capture completes before then.
2. **Retired vintages enter the panel only via open-weight stand-ins**
   (§3), each carrying its benchmark-parity citation and caveat; stand-in
   error feeds the amendment-1 EIV bounds. `gpt-4.5-preview` has **no
   qualified stand-in** — it is excluded from the panel rather than
   guess-filled.
3. **GDPval redistribution is an open legal item** (§4): the hosted gold
   subset declares **no license**. Internal research use proceeds
   (tasks referenced by ID); **no GDPval-derived task text may ship in the
   W10a public release** until terms are clarified with OpenAI or a
   license appears on the host page.

## 1. Vintage accessibility (adjudicated)

Accessibility is governed by OpenAI's deprecations page
(`https://platform.openai.com/docs/deprecations`, retrieved 2026-07-10);
owner adjudication 2026-07-10 resolved the pricing-page "yes" artifacts
(CONFLICT-A) in the deprecations page's favor.

**Retired / discontinued (stand-ins required):**

| vintage | shutdown |
|---|---|
| `gpt-3.5-turbo-0301`, `-0613`, `-16k-0613` | 2024-09-13 |
| `gpt-4-vision-preview` | 2024-12-06 |
| `gpt-4-32k` family | 2025-06-06 |
| `gpt-4.5-preview` | 2025-07-14 |
| `o1-preview` | 2025-07-28 (owner adjudication: discontinued) |
| `o1-mini` | 2025-10-27 (owner adjudication: discontinued) |
| `gpt-4-0314`, `gpt-4-0125-preview` | 2026-03-26 |
| `gpt-4-turbo-preview` | discontinued (owner adjudication) |

**Accessible today, shutdown announced (capture before these dates):**

| vintage | scheduled shutdown |
|---|---|
| `gpt-3.5-turbo`/`-0125`, `gpt-4`/`-0613`, `gpt-4-turbo`/`-2024-04-09`, `gpt-4o` snapshots, `gpt-4o-mini-2024-07-18`, `o1`/`-2024-12-17`, `gpt-4-1106-preview`¹ | **2026-10-23** |
| `gpt-4.1-2025-04-14`, `gpt-5-2025-08-07`, `o3-mini`, older `gpt-5.4`/`5.5` snapshots | **2026-12-11** |

¹ `gpt-4-1106-preview`: the deprecations page shows both 2026-03-26 (older
section) and 2026-10-23 (newer 2026-04-22 section); owner-resolved to
2026-10-23 (newer row supersedes).

**No announced shutdown:** `gpt-5.6-luna` / `-terra` / `-sol`,
`gpt-3.5-turbo-instruct`.

## 2. Current prices (per 1M tokens, in/out; retrieved 2026-07-09)

`gpt-3.5-turbo` $0.50/$1.50 · `gpt-3.5-turbo-instruct` $1.50/$2.00 ·
`gpt-4` $30/$60 · `gpt-4.1` $2/$8 · `gpt-4o` $2.50/$10 · `gpt-4o-mini`
$0.15/$0.60 · `o1` $15/$60 · `o1-pro` $150/$600 · `o3-mini` $1.10/UNKNOWN ·
gpt-5.4/5.5/5.6 families: **CONFLICT-B open** — the pricing page carries two
tables at exactly 2x of each other (e.g. `gpt-5.4` $2.50/$15 OR
$1.25/$7.50); both values are recorded in the legwork memo and neither is
filed as "the" price until the table captions are captured. Budget planning
should use the HIGHER value of each pair until resolved.

## 3. Open-weight stand-ins for retired vintages

| retired vintage | stand-in | parity evidence (source) | caveat |
|---|---|---|---|
| GPT-3.5 snapshots | Qwen2.5-72B-Instruct | MMLU 86.1, GSM8K 91.5, MBPP 84.7 (arxiv 2412.15115) | 推断: no same-harness GPT-3.5 row |
| GPT-4 / 4-Turbo snapshots | Llama-3.1-405B-Instruct | MMLU 85.2 vs GPT-4 86.4; GSM8K 89.0 vs 92.0; HumanEval 61.0 vs 67.0 (arxiv 2407.21783) | 推断: benchmark-near ≠ API-behavior-equivalent; no vision/tool parity |
| o1-preview / o1-mini | DeepSeek-R1 | AIME 79.8 vs o1-1217 79.2; MATH-500 97.3 vs 96.4; LCB 65.9 vs 63.4 (arxiv 2501.12948; corroborated on the Anthropic lane 2026-07-10) | reasoning/math/code only |
| o1-mini (small) | DeepSeek-R1-Distill-Qwen-32B | AIME 72.6 / MATH 94.3 / GPQA 62.1 vs o1-mini 63.6 / 90.0 / 60.0 (arxiv 2501.12948) | 推断: reasoning workloads only |
| gpt-4.5-preview | **NONE** | no direct parity claim found | exclude from panel |

## 4. GDPval license (verified negative, 2026-07-10)

- Host: `https://huggingface.co/datasets/openai/gdpval` (gold subset,
  220 rows; paper: "we open-source a subset, consisting of 220 tasks",
  arxiv 2510.04374).
- **No license declared**: no license field in the card metadata (only
  `configs`/`data_files`), no LICENSE file in the repo (Files view:
  `.gitattributes` + `README.md` only).
- The phrase "solely for research and evaluation purposes" appears in the
  card's Third-Party References disclosure — it is **not** a license grant.
- Implication: redistribution and commercial-use rights are UNKNOWN by
  primary source. Mapping work (W3) references tasks by ID and does not
  reproduce task text; the W10a release excludes GDPval-derived content
  (consistent with the existing CI release blocker).

## 5. Provenance & residual conflicts

- Row-level tables, URLs, retrieval dates: `dax/memo/w05_legwork_2026-07-10.md`.
- Channels: codex gpt-5.5 run (OpenAI family; owner-relayed) + owner
  browser pass 2026-07-09/10 + Anthropic-lane in-session spot checks
  (2 rows corroborated). Owner adjudications 2026-07-10: CONFLICT-A
  (deprecations governs), `gpt-4-1106-preview` = 2026-10-23.
- Open at signature time: **CONFLICT-B** (2x price tables, §2). It does not
  block the gate — it affects W4 budget sizing only, and the conservative
  (higher) values are specified for planning.

---
_PI signature at DAX-GATE-feasibility: record `gate DAX-GATE-feasibility
pass` (or fail) in ops/decisions.md._
