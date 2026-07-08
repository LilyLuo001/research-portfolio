# Research portfolio — 24×7 multi-seat runtime (P1 · E2 · DAX)

Bootstrap kit implementing `docs/Agent_Architecture_24x7.md` with one addition:
a **multi-seat Claude Pro partition** so 3–5 separate Pro accounts run in
parallel without colliding or duplicating work.

## the mental model (three layers, only one is "24/7")
- **L0 backbone** (`ops/runner/`) — deterministic Python + cron on your own
  always-on box. Free. Truly 24/7. Holds NO Claude credential.
- **L1 cheap workers** (`ops/runner/models.py`) — DeepSeek/Kimi/GLM/Qwen +
  Gemini-free, your own API keys, own commercial terms. The overnight shift.
- **L2 Claude seats** — your 3–5 Pro accounts, human-driven in the official
  apps during working hours. Parallel *frontier bandwidth*, not 24/7.

Read `ops/COMPLIANCE.md` first — it's the boundary that keeps L2 legitimate.

## non-collision in one paragraph
Seats are partitioned by project subtree (`ops/accounts.yaml`). The three
projects share no mutable state except `shared/` (owned solely by seat D) and
`ops/`. To run a task a seat must (1) see it READY in `queue.yaml`, (2) win a
git-committed **lease** on it (`lease.py` — a push rejection means someone beat
you), (3) work on branch `task/<id>` in its own worktree, (4) merge only after
the output passes `contracts.py`. Seats never talk to each other; they talk to
the repo. That is the entire coordination protocol.

## first run (offline, no keys needed)
```
make plan            # shows the ready set + collision-free seat assignment
make brief T=<task>  # write a prime-block brief for a ready task
make complete T=<task>      # AFTER its contract passes; commit state.json with the merge
make fail T=<task>          # record a failed attempt (2 strikes -> escalation in plan/digest)
make gate T=DAX-GATE-feasibility V=pass
make decisions       # apply gate verdicts written in ops/decisions.md
make replicate       # weekly portfolio-wide replay: selfcheck + all tests + smoke
```

Completion/gate state lives in the git-tracked `ops/runner/state.json` — the
repo is the only shared state, so every seat's clone sees what is already done.
Human gate replies go in `ops/decisions.md`; the box applies them every 30 min.

## bootstrap sequence (arch §6)
1. `make init` — create the monorepo (manuals already copied to docs/).
2. Seat D, block 1: build `ops/runner` for real + contract validator (task SH-runner).
3. Seat D, block 2: `shared/econlib` skeleton + toy tests (SH-econlib).
4. Wire L1 API keys into `models.py`; run one sentinel-fenced dummy batch (SH-l1-smoke).
5. `make plan` drives the day; `make digest` compiles your 30-minute evening read.
6. Create 3 claude.ai Projects (one per paper) with plan + 文献包 in Project knowledge.
