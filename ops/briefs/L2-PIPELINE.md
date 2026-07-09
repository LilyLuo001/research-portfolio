# L2-PIPELINE — synchronization plan (written 2026-07-09)

_Read this before picking any brief. It sequences the next ~2 weeks of L2
prime blocks so the L1/L0 night shift stops starving. Regenerate the numbers
with `make plan`; this file explains the ORDER and the WHY, which the planner
does not._

## 1. Diagnosis — why "the cloud barely runs anything"

The automation is fine; the DAG is starved at the top. As of today:

- **45 of 59 tasks are blocked upstream; 0 in flight; 3 complete.**
- Of the 7 "ready" L1 batches, only ~2 are actually runnable tonight:
  4 are parked `manual: true` awaiting a human/vendor decision
  (E2-T1-facts struck out 4× on kimi, E2-T9b + E2-T6b parked pending the
  same call), 1 voided (DAX-W0.5-legwork), E2-T11-scan is a recurring cron
  script already live, SH-l1-smoke is a self-test.
- **Every future L1 workload is locked behind L2 blocks + human gates that
  have never run**: P1-T1-events(+B), P1-T13-ant(+B) sit behind
  P1-GATE-t2a ← P1-T2a-power; E2-T2-dune sits behind E2-T1-facts (struck
  out); DAX-W3-bulk/W3-audit sit behind DAX-GATE-feasibility ←
  DAX-W0.5-feasibility. None of those four ready L2 tasks had a brief in
  ops/briefs/ until today — the seats had nothing prepared to execute.

So the fix is not more automation. It is **4–5 specific human prime blocks,
run in the right order, plus two ~5-minute gate decisions**. Everything else
cascades from that.

**Sync metric:** the count of truly-runnable L1 batches each night.
Today ≈ 2. After Waves 0–2 below ≈ 7–8. Check it in the digest every evening;
if it drops toward 0 again, an L2 block or gate is overdue.

## 2. Wave 0 — decisions, no seat time (~15 min) — ✅ EXECUTED 2026-07-09

Owner approved; decision log in `ops/decisions.md`. What changed vs the
original draft: the chunked-kimi retry idea is DEAD — it was already tried on
the night of 2026-07-09 (DAX-W0.5-legwork) and voided in a third distinct
failure mode (plan-then-stop: an `<antThinking>` block and nothing else).
**kimi $web_search is benched for retrieval batches until the vendor fixes it.**

1. **E2-T1-facts** → escalated to seat D per the two-strike ladder
   (`ops/briefs/E2-T1-facts-escalation.md`); stays `manual: true` for the
   driver. → Wave 1, block 3.
2. **E2-T1-facts-B** → validated (structure, 6/6 asset coverage, URL-or-
   UNKNOWN discipline, sentinels correct) and marked complete. Union-block
   flags recorded in decisions.md (aggregate navlink row, dict-shaped
   coinbase-vault item, "inferred" FalconX oracle row).
3. **DAX-W0.5-legwork** → parked at attempt 1 (kimi bench; avoids strike 2 +
   nightly re-bill). Seat E does the legwork inline in the W0.5 feasibility
   session — the spec's three item prompts are that session's checklist.
4. **E2-T9b-scenarios** → un-parked, re-routed kimi→gemini_free (no channel
   pair → no cross-vendor issue; ¥0; S2 fence risk noted in the spec).
   Runs tonight **once this branch is merged to main** (the box pulls main).
   **E2-T6b-nav** → stays manual by design: run
   `python ops/l1/gemini_helper.py E2-T6b-nav` with issuer docs uploaded —
   owner 30-min item, schedule alongside a Wave-1 block.

## 3. Wave 1 — prime blocks (run in parallel, one per seat, days 1–2)

Status update 2026-07-09 evening: blocks 3 and 5 were executed the same day
by a delegated Anthropic L2 session (merged to main alongside PR #16) — what
remains of them is **owner sign-off, not seat time**.

| order | seat | task | worker | brief | status / why first |
|---|---|---|---|---|---|
| 1 | **C** | `P1-T2a-power` | code_pro | ops/briefs/P1-T2a-power.md | **OPEN — next up (owner working manually).** Feeds P1-GATE-t2a, which alone unlocks **4 pure-L1 batches** (P1-T1-events A/B, P1-T13-ant A/B). ⚠ its input `p1/events_from_note.csv` does not exist yet: building it from public FEDS-Note numbers (with raw-source locators, meta-rule 1) is step 1 of the block. |
| 2 | **E** | `DAX-W0.5-feasibility` | project_pro | ops/briefs/DAX-W0.5-feasibility.md | **OPEN.** Feeds DAX-GATE-feasibility → W1-memo, W2-data, W3-mapA, W4-panel (the whole DAX line, priority 1). Kimi legwork benched → do the vintage/license legwork inline (checklist in the brief). |
| 3 | ~~D~~ | `E2-T1-facts` escalation | code_pro | e2/t1_union_check.md | **✅ channel A + union check DONE** (sentinels 3/3; on-chain explorer verification appended). **Remaining: owner arbitrates the 3 conflicts in e2/t1_union_check.md, then `complete E2-T1-facts`** — that flips E2-T2-dune (deepseek, L1) to READY and reopens the whole E2 line. |
| 4 | **A** | `DAX-W0-infra` | code_pro | ops/briefs/DAX-W0-infra.md | **OPEN.** Prereg-guard + NDA CI grep; must exist before any DAX data/outcome work starts in Wave 3. Short block. |
| 5 | ~~C~~ | `P1-T0-crash` | project_pro | p1/t0_collision_sweep_channelA.md | **✅ channel A DONE** — verdict: no collision on P1's outcome variable, recommendation CONTINUE. **Remaining: owner signs the kill/pivot call, then `complete P1-T0-crash`** — unblocks the recurring P1-T0-monitor batch. |

Seat **B** has nothing ready — that is correct, don't burn the seat. B wakes
in Wave 3 when E2-T2-dune output lands (→ E2-T3-index) and after the T1-facts
union (→ E2-T4a-design).

### Owner queue right now (in order of downstream value)
1. Arbitrate the 3 conflicts in `e2/t1_union_check.md` → write
   `complete E2-T1-facts` in decisions.md (unlocks E2-T2-dune; its
   `ops/l1/E2-T2-dune.yaml` spec still needs writing — seat B or D).
2. Seat C block: `P1-T2a-power` (Wave-1 specifics are in the brief).
3. Sign P1-T0-crash's CONTINUE verdict → `complete P1-T0-crash`.
4. Seat E block: `DAX-W0.5-feasibility` (inline legwork checklist in brief).
5. E2-T6b-nav manual run: `python ops/l1/gemini_helper.py E2-T6b-nav` with
   issuer docs uploaded (raw output — needs your sign-off before T6a).
6. Seat A block: `DAX-W0-infra` (short).

Every block ends the standard way: contract/selfcheck pass → merge task/<id>
→ `make complete T=<id>` → **run `make plan` and re-arm any newly-READY L1
batch before logging off** — that last step is the synchronization habit this
file exists to install.

## 4. Wave 2 — human gates (evening, ~5 min each, days 2–4)

These become READY as Wave 1 merges. Reply in `ops/decisions.md`
(`gate <TASK> pass|fail`); the box applies within 30 min.

- `P1-GATE-t2a` — read `p1/power_memo.md`. Pessimistic band → kill-switch
  (cancels the WRDS budget line); otherwise pass unlocks P1-T1/T13 L1 batches
  **that same night**.
- `DAX-GATE-feasibility` — PI signs `dax/memo/feasibility_note.md`. Pass
  unlocks DAX-W1-memo, W2-data, W3-mapA, W4-panel.

## 5. Wave 3 — post-gate steady state (week 2)

Once both gates pass, the portfolio reaches the intended shape — L2 daytime
blocks producing, L1 running every night:

- **Night shift (L1, automatic once READY):** P1-T1-events + P1-T1-events-B,
  P1-T13-ant + P1-T13-ant-B, E2-T2-dune, E2-T9b-scenarios, E2-T6b-nav
  retries, P1-T0-monitor (monthly re-arm), E2-T11-scan (cron).
- **Seat A:** `DAX-W2-data` (code_pro, pre-period only until GATE1), then
  `DAX-W1-memo` in the claude.ai Project — multi-session, PI iteration; this
  is the one irreplaceable frontier consumer, don't rush it.
- **Seat B:** `E2-T3-index` when T2-dune lands; `E2-T4a-design` after the
  T1-facts union. Then the T5 design + GATE-t5 chain.
- **Seat C:** `P1-T1-arb` once both T1-events channels land (then the
  spotcheck gate → T2-wrds).
- **Seat D:** back to float/escalation duty; owns any new two-strike parks.
- **Seat E:** absorbs whichever project enters spec/writing (likely
  DAX-W1-memo support or the E2-T5 design channel A).

## 6. Cadence rules (keep it synchronized)

1. **Gates cleared within 24h.** A parked gate freezes an entire project
   line; the two gates in Wave 2 are 5-minute reads.
2. **Every L2 block ends with `make plan`** and re-arms newly-READY L1 specs
   (write/update `ops/l1/<task>.yaml`) so the same night's driver picks them
   up. An L2 merge that doesn't feed L1 wastes a night.
3. **Two strikes → seat D, same week.** Don't let a parked L1 batch age
   (E2-T1-facts sat parked while the whole E2 line waited behind it).
4. **Watch the digest's READY-L1 count.** < 3 runnable batches means the
   night shift is starving → the next morning's first block goes to whatever
   L2 task unlocks the most L1 nodes (this file's Wave-1 logic, re-applied).
