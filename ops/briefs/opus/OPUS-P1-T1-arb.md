# PROMPT — P1-T1-arb (dual-channel arbitration → events_merged.csv)
_BLOCKED until BOTH `ops/l1/out/P1-T1-events.json` (channel A, Anthropic) and
`ops/l1/out/P1-T1-events-B.json` (channel B, gemini) exist. Do not dispatch
early. The frontier-tier seat-C session has offered to run this itself —
prefer that; use this prompt only if running it on SCC Opus instead._

---

You are seat C (P1-prime) executing **P1-T1-arb** (AMEND P1-5): machine-diff
the two extraction channels and adjudicate divergences into the paper's event
list. Read `CLAUDE.md`; meta-rules 1 (locators only) and 4 (NEED_HUMAN over
guessing) dominate this task. **No specification searching: you adjudicate
evidence, you never pick the answer that makes the sample bigger.**

## Protocol
`python ops/runner/lease.py claim P1-T1-arb --account C` → branch
`task/P1-T1-arb` → touch only `p1/`.

## Steps
1. Write `p1/t1_arb/diff.py`: normalize both channel outputs to one row per
   (filing id × fund event) with the T1 schema; classify each id into
   AGREE / A-only / B-only / FIELD-CONFLICT (list conflicting fields).
   Deterministic, committed, rerunnable.
2. Adjudication rules (frozen before you look at the diff counts — commit
   this file first):
   - AGREE rows pass through.
   - Date conflicts: the field must be re-locatable in the excerpt of the
     cited filing (`ops/l1/P1-T1-events.yaml` items carry the excerpts);
     re-read the excerpt and rule for the channel whose value is verbatim-
     locatable. Both locatable but different (e.g. board date vs closing
     date confusion) → apply POLICY.md's definitions (announce = first
     board-approval/first-disclosure; effective = stated closing date).
     Neither locatable → NA + confidence L.
   - A-only/B-only events: check whether the other channel saw the same
     excerpt (same filing id present with no_event). If the excerpt supports
     the event on re-read → keep, note which channel missed it. If it rests
     on text outside the excerpt windows → mark `needs_fulltext` (these join
     the flagged "financial-highlights N-14" items).
   - Items either channel flagged "FLAG for B-channel/arb" (excerpt windows
     missed transaction language, CEF→ETF scope calls): resolve by fetching
     the full filing from the `source_url` ONLY if network allows; otherwise
     `needs_fulltext`, never guessed.
   - Any same-fund contradiction that survives re-reading → NEED_HUMAN row,
     carried in the output with status=NEED_HUMAN, never dropped silently.
3. Output `p1/events_merged.csv` conforming to `ops/contracts/events_merged.yaml`
   (run `python ops/runner/contracts.py events_merged p1/events_merged.csv`
   until PASS) + `p1/t1_arb/arb_report.md` (counts per category, every
   adjudicated row with its ruling and locator, the NEED_HUMAN list, and the
   needs_fulltext list for the owner's spotcheck).
4. Lineage JSON for both outputs; merge to main;
   `python ops/runner/runner.py --complete P1-T1-arb` ONLY if contract PASS
   and zero unresolved code errors. Then report: P1-T1-spotcheck (human 門 1:
   confidence H 抽10%, M/L 全查) is now READY for the owner. `make plan`, stop.
