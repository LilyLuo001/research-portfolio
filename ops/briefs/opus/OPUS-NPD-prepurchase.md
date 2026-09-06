# PROMPT — NPD-prepurchase (no-purchase ETF/stock price-discovery feasibility)

_Paste below the line into a fresh Claude Code session **running where the WRDS
mirror is on local disk** — an SCC login/compute node, or a session on the Mac
that has the `bu-scc` MCP server and a live ControlMaster login. It will not run
anywhere else: the cloud seat that prepared this package proved it cannot reach
`/projectnb` or `*.bu.edu`, and recorded the evidence in
`news_price_discovery/prepurchase_wrds/ACCESS_BLOCKER.md`. Nothing here needs a
purchase, a vendor contact, or a credential._

---

You are executing **NPD-prepurchase**, a bounded no-new-purchase empirical
feasibility test in a clone of the portfolio repo. Fresh session, zero
conversational memory. Read `CLAUDE.md` first — the five meta-rules govern
everything below, and meta-rule 1 is the one that will bite: **no row count,
coverage figure, date range, or coefficient may come from a manual, from a
filename, or from memory.** It comes from code you ran on the archive, or it
does not go in the package.

## 0. Your two source documents are in the repo

Both are committed, so this task hands off through files rather than a chat
transcript (meta-rule 3):

- `news_price_discovery/prepurchase_wrds/INSTRUCTION-2026-09-06.md` — the
  owner's bounded instruction, **verbatim and authoritative**. Read it whole
  before writing code. Where this brief and that file differ, that file wins.
- `news_price_discovery/prepurchase_wrds/REFERENCE-WRDS-Data-Usage-Manual.md` —
  archive orientation. It is an inventory, **not a guarantee of any field or
  date**. Every fact it states is a hypothesis your code must confirm.

Frozen parameters are already in `news_price_discovery/prepurchase_wrds/config.yaml`.
They were set before any data was seen. Do not edit them after seeing a
coefficient — that is specification search, and it is banned outright.

## 1. Protocol

Claim the lease, work on the branch, touch only your directory:

```bash
python ops/runner/lease.py claim NPD-prepurchase --account C
git checkout -b task/NPD-prepurchase
```

Only `news_price_discovery/` is yours. `shared/` is read-only. Commit early and
often. Anything long-running is a script handed to the scheduler (`qsub` via
`scc_submit_job`, or the SCC batch system directly) — never babysat in-session,
and never more than one concurrent research job.

## 2. Start with stage 0. It is already written and tested.

```bash
python news_price_discovery/prepurchase_wrds/stage0_discover.py \
    --out news_price_discovery/prepurchase_wrds/out
```

It write-tests the output filesystem, reads `FINAL_SCC_MANIFEST.tsv` **once**,
resolves the families this task needs, and reads Parquet **footers only** — no
data rows, no concatenation. It emits `source_catalog.tsv` (contract:
`npd_source_catalog`) and `stage0_report.json`, each with lineage.

```bash
python ops/runner/contracts.py npd_source_catalog \
    news_price_discovery/prepurchase_wrds/out/source_catalog.tsv
python -m pytest news_price_discovery/prepurchase_wrds/tests -q   # 13 tests
```

Read `stage0_report.json` before writing another line of code. Its
`families[*].capability` block decides what is runnable:

| gate | if it comes back BLOCKED |
|---|---|
| `crsp_dsi` (a value-weighted market return) | the original-style Hou–Moskowitz baseline is **unavailable**; any substitute benchmark is labelled an *adaptation*, declared before you run it, and never swapped midway. Never regress SPY on itself. |
| `crsp_ibes_link` (`sdate`/`edate`/`score`) | do not fall back to ticker matching. Log the ambiguity and report the earnings census as blocked on the link. |
| `crsp_holdings` (`percent_tna`) | the §2 weight construction stops. Do not reconstruct weights by dividing pooled holdings by ETF-class TNA. |
| `ibes_actuals` (`anntims`) | the date-level census and the bracketed daily event study still run. Only the session classification stops. |

If the archive itself is unreachable, stage 0 exits 3 with `NEED_HUMAN` and
writes nothing. That is the correct behaviour — do not hand-write a catalog.

## 3. Then the round trips, before any bounded sample

The instruction (§7) asks for a few raw-record round trips and **one fully
worked event** before processing anything. Do exactly that, and commit the
notebook/script that shows it. Test: return units, mapping intervals, consensus
precedence, weights, split and distribution handling, session mapping, duplicate
events, and nested regression rows. Pick one primary daily source and compare
overlap with the alternate on a small sample — never stack legacy and CIZ, never
silently mix price and total returns. Extract the ETF securities separately from
any common-stock filter (`shrcd in (10,11)` excludes SPY).

## 4. Then stages 1–5, in the instruction's own order

Build each against `INSTRUCTION-2026-09-06.md` §1–§5 — event and coverage census;
portfolio approximation and signal size; Hou–Moskowitz D1 and the
earnings-response curves; the optional FRBSF macro supplement and Rigobon
variance diagnostic; the conditional precision table and acquisition manifest.
Declare each output's columns in a thin contract under `ops/contracts/` **in the
same commit that lands its builder** — that is the rule-3 handshake, and the
reason `npd_source_catalog.yaml` is deliberately thin.

Six traps worth naming, because each is easy to fall into and hard to undo:

1. **Do not renormalise a covered sleeve to 100% and call it the fund.** If the
   complete portfolio is not computable, report the sleeve and its coverage.
   Missing or unmapped assets are not cash and not zero-return assets.
2. **Do not turn a guessed timezone into a session classification.** A non-null
   `anntims` is not a verified timestamp. Seek the documentation check; if the
   semantics stay unknown, report both the same-day and next-day mappings as
   sensitivities and pick neither.
3. **Do not treat replicated ETF rows as independent shocks.** Hundreds of
   constituents on one FOMC date are one monetary shock. Resample whole shared
   news dates jointly across ETFs.
4. **Do not scale daily volatility into an intraday variance** by multiplying by
   the square root of elapsed trading time. The residual-SD grid in `config.yaml`
   is an assumption set for a planning table, and must be printed as one.
5. **Report the first run.** A null daily lag is not a failed project, and a
   wide insignificant interval is inconclusive rather than a zero.
6. **Leave 2024–2025 unexamined** for this question. If you inspect them, say so.

## 5. Definition of done

One compact package under `news_price_discovery/prepurchase_wrds/`: event and
coverage ledger; portfolio and signal diagnostics; delay and daily-response
results with figures; macro results or a specific statement that the module was
blocked; the conditional precision table; the acquisition manifest (union of
security-time intervals, so overlapping windows are not bought twice); a brief
purchase-readiness report; and the reproduction code, config and tests.

The report closes with exactly one of `READY_FOR_LIMITED_INTRADAY_VALIDATION`,
`HOLD_PURCHASE_FOR_NAMED_INPUT` (naming precisely what must be supplied), or
`NO_PURCHASE_FOR_CURRENT_SAMPLE_OR_PRODUCT` (stating the scope of that
conclusion). No daily p-value, response sign, R² cutoff, the old 3-bp threshold,
or assumed intraday MDE may act as an automatic gate.

Then: contracts pass, lineage emitted, merge to main,
`python ops/runner/runner.py --complete NPD-prepurchase`, `make plan`, stop.

**A failed optional module does not void the others** — report the independently
valid results and the specific blocker. Finish after this one bounded package;
do not append a literature or positioning assignment, and do not expand the
pipeline after seeing the first results. If something is genuinely unknown, emit
`NEED_HUMAN: <reason>` rather than guess-filling it.
