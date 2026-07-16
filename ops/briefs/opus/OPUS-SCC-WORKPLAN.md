# OPUS-SCC-WORKPLAN — P1 / Refraction / DAX structural plan + Opus 4.8 prompt pack
_Written 2026-07-16 by the frontier-tier session (seat C lane). Owner asked for:
(a) big-picture status of P1, refraction, DAX; (b) division of labor where the
frontier model does spec/audit/gates only and Opus 4.8 sessions on the BU SCC
do the execution; (c) ready-to-paste prompts. Prompts live in this directory
as `OPUS-<task>.md` — each is standalone for a fresh Claude Code session
running in a clone of this repo on the SCC._

## 0. The new lane, and the one routing rule that matters

Opus 4.8 @ SCC is an **Anthropic-family** lane. It can take:
- any task whose queue worker is `code_pro` / `project_pro` (Anthropic already);
- any **channel-A** L1 task stranded by the kimi bench / dead box lane
  (precedent: E2-T1-facts, P1-T0-crash, E2-T9b escalations in ops/decisions.md).

It can **never** take a **channel-B** task whose A-channel is already Anthropic
(P1-T1-events-B, P1-T13-ant-B, REFR-R0-collide-B): cross-vendor independence
(meta-rule 2) would collapse. Those stay on gemini_free and need either the box
L1 lane repaired or `GEMINI_API_KEY` + `ops/runner/l1_driver.py` run on the SCC
(the driver is vendor-keyed, not Anthropic — running it on SCC is legal).

Priority order when SCC time is contended: `dax > e2 > p1` (queue.yaml meta),
with one exception — **P1-T1-events-A-finish is cheap and unblocks the most**
(arb → spotcheck → WRDS → refraction R2 inputs), so run it first anyway.

## 1. P1 (fund conversions) — status

**Done:** T0 collision sweep (CONTINUE, owner-signed); T2a power memo
(three-band ALL-PASS, `gate P1-GATE-t2a pass` applied); EDGAR harvest (1418
T1 filings + 414 T13 filings, manifest committed); all four L1 specs built
(`ops/l1/P1-T1-events{,-B}.yaml`, `P1-T13-ant{,-B}.yaml`); **channel A of
T1-events 35/90 batches extracted** this week on the Anthropic lane
(`p1/t1_channelA_wip/rb_001..035.jsonl` + POLICY.md + full handoff pack in
`p1/t1_channelA_wip/handoff/`). Lease on P1-T1-events is held by seat C.

**Not done / blocked:**
| item | state | blocked on |
|---|---|---|
| T1-events channel A batches 36–90 + assembly | **→ OPUS-P1-T1-events-A-finish.md** | nothing |
| T1-events channel B (gemini) | armed, laneless | box repair OR SCC gemini driver run (owner) |
| T13-ant channel A (414 filings, incl. semi-transparent/ANT schema) | **→ OPUS-P1-T13-ant-A.md** | nothing |
| T13-ant channel B | armed, laneless | same as T1-B |
| T1-arb (machine-diff + adjudication → events_merged.csv) | prompt prepared (**OPUS-P1-T1-arb.md**) | both channels landed |
| T1-spotcheck | human gate | arb output (H 抽10%, M/L 全查) |
| T2-wrds (holdings pipeline + ConvExp) | not started | spotcheck pass + WRDS credentials on SCC |
| T4 replication, T3 spec chain, T5 main | not started | upstream |
| AUDIT K-1: DFA per-fund AUM sum discrepancy ($30.7bn vs ~$28.65bn) | **owner browser check, 5 min** | owner |
| P1-T0-monitor monthly re-arm | parked (kimi bench) | owner decision due 2026-08-01 |

## 2. Refraction (macro-event standby chapter) — status

**Done:** R0 repo landing — frozen_config.yaml, prereg_guard (machine-enforced
prereg-before-outcomes + lookahead ban), assert_panel (14 asserts), 19 tests,
5 contracts, 2 L1 specs (parked on kimi bench).

**Not done / blocked:**
| item | state | blocked on |
|---|---|---|
| R0 collision sweep channel A | **→ OPUS-REFR-R0-collide-A.md** (re-route off kimi; B stays gemini → cross-family holds) | web search enabled |
| R0 channel B | gemini spec | box/gemini lane |
| R1a USMPD/calendars/consensus registry | **→ OPUS-REFR-R1a-verify.md** | web search enabled |
| R1b parsers (build_calendar/build_surprises → contracts `macro_calendar`, `surprises`) | **→ OPUS-REFR-R1b-parse.md** | R1a output + **owner-pasted USMPD file heads** (hard NEED_HUMAN in the prompt) |
| R2 panel/β/lever build (~1 seat-week) | do NOT dispatch yet | R1b; owner CRSP table/var list; holdings_weights口径 aligned with P1-T2 **in writing**; P1 frozen inputs (events_merged.csv, conv_exposure.parquet) which don't exist until P1-T1-arb→T2 |
| R3 Gate-0 → GATE-PREREG → R4 OSF → R5 design → R6+ | sequential behind R2 | — |
| Standing NEED_HUMAN | consensus license (Bloomberg ECO vs WRDS); ETF Global access (R9, non-blocking); Gate-0 thresholds confirmation; OSF account | owner |

## 3. DAX (AI exposure index) — status  [portfolio priority 1]

**Done:** W0-infra (3-layer prereg seal on analysis/outcomes/, NDA CI grep);
W0.5 feasibility **CONDITIONAL GO signed 2026-07-10** with three binding
conditions: (1) W4 API capture before the 2026-10-23 / 2026-12-11 OpenAI
shutdown waves — **this is the portfolio's only hard external deadline**;
(2) retired vintages only via cited open-weight stand-ins inside EIV bounds,
gpt-4.5-preview excluded; (3) GDPval task-by-ID referencing only, nothing
GDPval-derived in the W10a public release until license clarified.

**Not done / blocked:**
| item | state | blocked on |
|---|---|---|
| W1 pre-registered design memo (GATE 1; the one irreplaceable frontier consumer) | **→ OPUS-DAX-W1-memo.md** — multi-session, every number [PI-DECISION] flagged | PI iteration |
| W2 public data backbone (O*NET/OEWS/IPUMS-CPS/crosswalks/static scores/prices) | **→ OPUS-DAX-W2-data.md** — pre-period only until GATE1 | IPUMS API key (owner registers) |
| W3-mapA GDPval mapping protocol | next after W2; frontier task — write prompt when W2 lands | W2 |
| W3-bulk annotation + W3-audit | cheap tier + cross-vendor audit; NOT Opus work | W3-mapA |
| W4 capability/cost panel (SPEND, own budget line) | schedule against 2026-10-23 deadline; owner flags budget to funder NOW | W3-mapA, budget |
| GATE1 → tag v1.0-preregistered → W5 index | PI signs every memo number | W1 |
| analysis/outcomes/ | **stays sealed until the tag** (never open early) | GATE1 |

## 4. E2 (not in scope of this pack, one line)
E2-T4a-design (seat B) and E2-T2-dune (deepseek, armed) are READY; both wait
on a seat/lane, not on specs. The same SCC lane logic applies if wanted later.

## 5. Division of labor going forward

- **Opus 4.8 @ SCC (execution):** the seven prompt files in this directory.
  Run order if serial: P1-T1-events-A-finish → DAX-W1-memo (session 1) →
  DAX-W2-data → P1-T13-ant-A → REFR-R1a → REFR-R0-A → REFR-R1b (after owner
  supplies USMPD heads). DAX-W1 is multi-session; interleave with PI feedback.
- **Frontier tier (this lane) — gates and audits only:** P1-T1-arb
  adjudication when both channels land; 10% stratified audit of each Opus
  bulk output before its contract check; red-team pass on the W1 memo draft
  BEFORE PI signature; Gate-0 判读 memo draft at REFR-GATE-PREREG.
- **Owner (cannot be delegated):** gemini/deepseek keys or box repair (revives
  every channel-B + E2-T2-dune); WRDS + IPUMS credentials on SCC; DFA AUM
  fix (K-1); USMPD file heads for R1b; W4 budget line to funder; PI signatures
  at the gates; the standing refraction NEED_HUMANs.

## 6. Session protocol for every Opus run (repeated at the top of each prompt)
Fresh session in a repo clone on SCC → read CLAUDE.md + the named brief →
claim the lease (`python ops/runner/lease.py claim <task> --account <seat>`)
→ work on branch `task/<task>` touching only the owning project's directory →
commit early/often → output must pass its contract or self-check → lineage
JSON via `python ops/runner/lineage.py <output> <inputs...>` → merge to main +
`python ops/runner/runner.py --complete <task>` only when the task's OWN
definition of done is met (dual-channel tasks are NOT complete until arb) →
`make plan`, report what's newly READY, stop when blocked and say on whom.
