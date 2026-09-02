# The WRDS execution prompt — copy this whole file into the agent's session

_Seat C, 2026-09-02. For the agent that will run on the machine holding the WRDS
credential. Requirement of record: `p1/wrds/DATA-REQUIREMENTS-v2.1.md`._

**Before you dispatch it, read these three operator notes.**

1. **Where it runs.** The raw parquets are licensed CRSP/Compustat/IBES rows and
   are gitignored by policy — they can never travel through git. So the machine
   that pulls must be the machine that later computes the outcomes, or share
   storage with it. An ephemeral container is not an answer. ~10 GB free.
2. **Two sessions, not one.** Phase 0 is offline repo work and should be run and
   committed **before** the credential is live. Phases 1–6 are the connected
   window.
3. **Do not paste the plan documents into the prompt.** The agent reads them from
   the repo; that is what keeps the file the single source of truth.

---

## PHASE 0 PROMPT — offline, run and merge before the account goes live

```
[CONTEXT PACK v1.0 — 基金转换研究项目]
你是本项目多 agent 流水线中的一个执行单元。仓库中的
docs/基金转换实验_博士研究计划.md (v2.1) 与
docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md + docs/Refraction_Chapter_Plan_Amendment_v2_2.md
是唯一的项目真相源;你的任务定义若与它们冲突,以它们为准并报告冲突。

硬性规则(违反任何一条 = 任务失败):
1. 不得凭记忆给出任何日期、金额、持仓、表名、列名;一切事实须来自代码在真实
   数据上的执行输出,或附带原始定位符的抽取。
2. 输出文件严格遵守 ops/contracts/ 中已冻结的 schema,不增删改列名。
3. 信息不足时输出 NEED_HUMAN: <原因>,禁止猜测补全。
4. 每次输出末尾附自检清单(逐条 PASS/FAIL)。

TASK: P1-WRDS Phase 0 — patch the pull machinery so that one connected window is
enough. No network is required for any of this.

READ FIRST (in this order, do not skim):
  p1/wrds/DATA-REQUIREMENTS-v2.1.md      <- the requirement of record; §6 is your worklist
  p1/wrds/tables.yaml                    <- the machine-readable contract you are patching
  p1/wrds/pull.py                        <- discover / resolve / pull
  p1/wrds/universe.py                    <- the offline scope builder
  p1/wrds/verify.py                      <- the release gate
  ops/briefs/P1-WRDS-SPRINT.md           <- the runbook and its cut order

DO, in this order, committing after each item:
  P1  tables.yaml: add logical column `anndate_time` (candidates: [anntims]) to the
      `ibes` pull, and an assert `anntims_timezone_and_coverage` whose text says the
      time zone and the non-null rate must be verified on the server before any
      number is computed from it.
  P2  pull.py build_queries('ibes'): add the resolved anntims column to the actuals
      SELECT.
  P3  pull.py build_queries('dsf' and 'msf'): add shrout, cfacshr, cfacpr to both
      SELECTs. They are already declared in tables.yaml and never reach the SQL.
  P4  pull.py build_queries('mf_holdings'): extend the holdings upper bound at least
      two reporting periods past the last effective date. Gate 0 (plan §9.0) compares
      the last PRE-conversion report with the FIRST POST-conversion one; the current
      bound makes the post side unreachable.
  P5  tables.yaml + pull.py: add fundq columns niq, atq, ceqq, cshoq, prccq, saleq,
      sich, fyearq, fqtr.
  P6  tables.yaml + pull.py: add stocknames columns shrcd, exchcd, siccd, comnam, permco.
  P7  universe.py: daily_start -> 2014-01-01, monthly_start -> 2012-01-01,
      fundamentals_start -> 2010-01-01. Keep the derivation comments truthful: the
      binding constraint is refraction's 2017-01 announcement start plus its
      placebo-in-time on 2017-2020 fake conversion dates with +-8 quarters of
      announcements (refraction/frozen_config.yaml, assert A2), NOT a preference.
      Regenerate pull_scope.json with `--write` and commit the lineage sidecar.
  P8  tables.yaml: new pull `fund_flows` (candidates crsp.fund_summary,
      crsp.monthly_tna_ret_nav) for net flows / expense ratio / TNA — threat T5.
  P9  tables.yaml: new pull `index_membership` (candidates comp.idxcst_his and any
      Russell constituent product) — threat T9 is a FORCED sub-spec
      (docs/P1_修订补丁_v1_1.md) and ops/contracts/outcomes_panel.yaml already
      declares a `russell_change` column with no producer. If nothing resolves on
      the server later, that is a NEED_HUMAN, not a silent drop.
  P10 tables.yaml: make the ibes `summary` pull land BOTH statsum_epsus and
      statsumu_epsus rather than resolving to one. Adjusted-vs-unadjusted then
      becomes a groupby instead of a second rental.
  P11 tables.yaml: add msi (monthly index) and msedelist (monthly delisting).
  P12 tables.yaml + pull.py: add a `taq_intraday` pull whose scope is a (symbol, date)
      LIST and which REFUSES to run without that list. It must be impossible to
      express it as a bare date range.
  V1  verify.py: add two checks — anntims non-null rate (by year and by market-cap
      decile if computable), and holdings coverage on BOTH sides of every effective
      date.

CONSTRAINTS:
- Do not remove or weaken any existing refusal. The resolver's refusal to guess a
  name is the safety property of this whole layer; adding a fallback heuristic is a
  task failure, not a fix.
- Every new column goes into tables.yaml as a CANDIDATE with `resolved: null`.
  Filling `resolved:` from your own knowledge is a meta-rule-1 violation.
- Run `python -m pytest p1/tests/ -q` after each commit; extend the tests where a
  patch is not covered.
- `python p1/wrds/pull.py status` must still report every pull BLOCKED with an empty
  inventory afterwards. That is the correct shipped state.

DELIVERABLE: the commits, plus a short PHASE0-REPORT.md listing each of P1-P12/V1 as
DONE / NOT-DONE-BECAUSE, and the `pull.py pull --dry-run` SQL for every pull (it runs
without a connection) so the queries can be read before they execute.

自检清单: tests green? status still BLOCKED-with-empty-inventory? every new column
`resolved: null`? no refusal weakened? pull_scope.json regenerated with lineage?
```

---

## PHASES 1–6 PROMPT — the connected window

```
[CONTEXT PACK v1.0 — 基金转换研究项目]
(same header as Phase 0 — paste it verbatim)

TASK: P1-WRDS — execute the pull. You have a live WRDS account and a bounded window.

THE ONE SENTENCE THAT GOVERNS THE DAY:
  A WRDS column name written from memory does not raise — it returns a different
  number. Nothing here builds SQL from a name that has not been read off the live
  server. When the resolver refuses, DO NOT GUESS TO SAVE TIME: open the WRDS web
  query tool, copy the real name, paste it. Two minutes there beats a silently wrong
  dataset found six weeks later.

READ FIRST:
  p1/wrds/DATA-REQUIREMENTS-v2.1.md   <- what is needed and why (§4 tables, §7 the
                                         questions only the live server can answer)
  ops/briefs/P1-WRDS-SPRINT.md        <- the order, the clock, the cut lines
  p1/wrds/PHASE0-REPORT.md            <- what the offline patch pass did or did not do

------------------------------------------------------------------
PHASE 1 — INVENTORY (do this before anything else; it is cheap and it decides the
rest of the day)
------------------------------------------------------------------
  export WRDS_USER=<username>          # case-sensitive
  python p1/wrds/pull.py discover      # writes p1/wrds/discovered_schema.json

Then, in the same connected session, produce p1/wrds/SUBSCRIPTION-REPORT.md — the
only authority on what this account can actually read. It must answer, each with the
command that produced the answer:

  1. Every library this account can list. (`db.list_libraries()`)
  2. For each of these, does it exist and what are its columns:
     crsp stock (stocknames/dsenames, dsf, dsi, dsedelist, msf, msi, msedelist),
     crsp ccm link, comp fundq/funda/company, ibes actuals/summary/summary-unadjusted/
     idsum/detail, crsp mutual fund (holdings, fund header, portnomap, fund summary),
     TAQ daily indicators (IID), TAQ intraday quotes/trades, index membership
     (S&P and/or Russell), Fama-French factors, 13F, OptionMetrics, short interest,
     any macro/consensus product.
  3. **IBES anntims** — does the column exist on the actuals file? Report its
     non-null rate overall, by year, and (if the join is cheap) by market-cap decile.
     THIS IS THE HIGHEST-VALUE FACT OF THE DAY. Plan §7.1/§7.1.1 build every event's
     t_0 from it, gate K3 thresholds on it at >=70%, and §4.1 makes the intraday
     purchase decision downstream of it. Report the TIME ZONE the field is stored in,
     with the documentation locator — do not infer it from values.
  4. **TAQ intraday** — which product, keyed on what, does it cover EXTENDED HOURS
     (pre-market and post-market), and does its coverage include small caps? Plan
     §7.1 sets t_0 = the next 09:30 open for pre/post-market announcements, so
     extended-hours coverage is a design question, not a nicety. If this account
     carries usable intraday quotes, say so plainly — it may make the external
     Databento purchase in §4.1 unnecessary, which is a five-figure-RMB-scale
     decision the owner is currently holding open.
  5. Which effective-spread convention the IID field implements (dollar vs
     proportional, quote-matching rule), with the documentation locator.
  6. `shrout` units on msf and dsf, with the documentation locator.
  7. Delisting table format: dsedelist/msedelist, or the CIZ-format equivalent?
  8. Are comp.fundq/funda the NORTH AMERICA files (not Global)?
  9. Which linktype and linkprim values actually occur on the CCM link table?
  10. Does an ETF flag exist on the CRSP MF header (et_flag or equivalent)?
  11. Does any index-membership product resolve? Any macro-consensus product?

For 3, 4, 5, 6 and 11: REPORT, do not choose. Items 4 and 11 are owner decisions
with money attached.

------------------------------------------------------------------
PHASE 2 — RESOLVE
------------------------------------------------------------------
  python p1/wrds/pull.py resolve
  python p1/wrds/pull.py status

Settle every NEED_HUMAN at the WRDS web query tool and paste the real names into
tables.yaml's `resolved:` fields. One decision is pre-recorded and you should not
re-litigate it: stocknames carries BOTH ncusip and cusip, the resolver will refuse
as ambiguous, and the answer is **ncusip** — the historical CUSIP valid over
[namedt, nameendt], which is what a point-in-time N-PORT holding must match. Paste
it from the web query tool; do not type it from memory.

If a name cannot be settled, leave it unresolved and cut that pull per the cut order
in DATA-REQUIREMENTS §8. Do not substitute a similar-looking table.

------------------------------------------------------------------
PHASE 3 — PULL, in dependency order
------------------------------------------------------------------
Run `--dry-run` first on every pull and READ the SQL before it executes.

  1. stock_names        -> permno + ticker + shrcd/exchcd/siccd. EVERYTHING waits on it.
  2. python p1/wrds/verify.py     <- STOP HERE IF cusip->permno COVERAGE FAILS.
     A failure here almost certainly means you resolved `cusip` where you wanted
     `ncusip`. Fix tables.yaml, `pull --force`, re-verify. Five minutes now; a
     second rental later.
  3. ccm_link           -> gvkeys, before any Compustat. Do NOT apply the
                           linktype/linkprim filter at pull time.
  4. msf                -> monthly, FULL CRSP universe (see the scoping note below).
  5. compustat          -> fundq + funda, scoped by gvkey.
  6. ibes               -> identifiers + summary(adjusted) + summary(unadjusted)
                           + actuals INCLUDING anntims.
  7. mf_holdings        -> fund_header, then the NAME match, then holdings.
     ** After fund_header lands and before holdings runs, READ
        p1/wrds/raw/mf_holdings__matched_fundnos.json. A zero match refuses
        automatically. A PARTIAL match cannot be detected by machine and silently
        drops treated funds from ConvExp. The register has 172 events / 170 distinct
        fund names / a usable mutual-fund ticker on only 19 of them — matching is by
        normalised name and it is the weakest join in the pipeline. If the matched
        count looks low against 170, stop and report NEED_HUMAN with the unmatched
        names listed. **
  8. dsf                -> the big one. Run last among the large pulls.
  9. taq_iid            -> skip if CRSP bid/ask came back populated; verify.py tells
                           you which world you are in.
 10. fund_flows, msi, msedelist, index_membership, factors -> if the clock allows.

SCOPING NOTE — this differs from what the code did before, and the reason is
recorded in DATA-REQUIREMENTS §2 and §D7: the ConvExp file the old scope was derived
from is STALE (its lineage names an older events_merged.csv; the register has since
gone 131 -> 172 events, and ConvExp covers 49 of 96 waves). Scoping CRSP to our
6,747 CUSIPs therefore bakes a stale universe into the pull, and the ConvExp rebuild
is blocked on sec.gov egress rather than on WRDS. So:
  - msf: pull the FULL CRSP universe (monthly is small) — it is also the only way to
    get NYSE breakpoints and a matched-control pool of non-held stocks, which plan
    §5 layer 3 and refraction §5 layer 3 both require.
  - dsf: scope by a UNIVERSE FILTER read off CRSP (shrcd in (10,11)), not by our
    CUSIP list. **Run `select count(*)` with the intended WHERE clause first and
    report the number before executing the pull.** If the count implies a size the
    window cannot absorb, fall back to (our CUSIPs) UNION (the matched-control
    permnos selected from the landed msf) and say so in the manifest.
  - Every pull lands an immutable parquet under p1/wrds/raw/ plus a lineage JSON
    carrying the exact SQL, and refuses to overwrite without --force.

------------------------------------------------------------------
PHASE 4 — THE TWO EX-ANTE ARTEFACTS (still inside the window; they are cheap and
they are what the whole design is waiting on)
------------------------------------------------------------------
A. **The announcement-timing table (plan §7.1.1).** From the landed IBES actuals,
   classify every earnings event of every stock in the universe as RTH (09:30-16:00
   ET) / pre-market / post-market, and produce a PURE EX-ANTE table:
     events, stocks and waves in each class; split by treated vs control; split by
     DFA vs non-DFA; plus event characteristics (market-cap decile, analyst
     coverage, Exposure^pre distribution).
   Write it to p1/wrds/announcement_timing_table.{md,json} with a lineage sidecar.
   ** This table contains NO outcome variable and must be produced BEFORE any beta_h
      is estimated. Plan §7.1.1: the main-sample rule is decided from this table and
      written into ops/decisions.md, and after that it may not be changed because of
      a result. Do not compute any treatment effect in this phase. **

B. **The intraday request list.** From the same classification plus the ConvExp
   universe, emit the exact (symbol, date) pairs an intraday pull would need —
   treated and matched-control stocks, their earnings-announcement dates, and the
   window each class requires (pre/post-market events need the next session's open,
   and possibly extended hours). Write p1/wrds/intraday_request_list.csv plus a
   count summary. This replaces the §4.1 cost estimate, whose own audit table marks
   7 of its 11 inputs as unverified — including the 0.596 MB/symbol-day coefficient
   that the entire figure rests on, and the 131-event ConvExp it was computed from.
   If Phase 1 item 4 found usable WRDS intraday quotes, pull a PILOT — 30 treated +
   30 control stocks over 20 announcement dates — and report per-symbol-day size and
   coverage. Do not pull the full intraday set without the owner's go-ahead.

------------------------------------------------------------------
PHASE 5 — RELEASE GATE
------------------------------------------------------------------
  python p1/wrds/verify.py
  python p1/wrds/verify.py --json > p1/wrds/verify_report.json

Then commit provenance — and ONLY provenance. The raw parquets are licensed rows,
are gitignored, and a policy test enforces it:
  git add p1/wrds/tables.yaml                       # the resolved names: the day's real product
  git add p1/wrds/raw/*.lineage.json                # exact SQL + row count per file
  git add p1/wrds/raw/mf_holdings__matched_fundnos.json
  git add p1/wrds/verify_report.json
  git add p1/wrds/SUBSCRIPTION-REPORT.md p1/wrds/announcement_timing_table.*
  git add p1/wrds/intraday_request_list.csv
Commit BEFORE releasing the account.

------------------------------------------------------------------
PHASE 6 — RECORD THE DECISIONS, PRE-OUTCOME
------------------------------------------------------------------
Append to ops/decisions.md, each with the locator that settled it:
  shrout units; the cfacshr direction (multiply vs divide) as VERIFIED AGAINST DATA by
  p1/tests/test_gate0_continuity.py, not against documentation alone; the effective-
  spread convention; the SUE fork (analyst vs time-series — this one is the owner's,
  report both branches' availability and stop); the CCM link filter codes; the
  fund-name match outcome; ncusip vs cusip; the main-sample rule implied by the
  Phase 4A table; and whether the WRDS intraday product removes the need for the
  external purchase.

------------------------------------------------------------------
STOP RULES
------------------------------------------------------------------
- Any name that cannot be confirmed on the live server -> NEED_HUMAN and cut that
  pull per DATA-REQUIREMENTS §8. Never substitute a similar table or a similar column.
- cusip->permno coverage FAIL -> stop, fix, re-pull. Do not proceed to dsf.
- Fund-name match materially below the 170 distinct names -> stop and report before
  holdings runs.
- A pull whose estimated size the window cannot absorb -> report the count, propose
  the narrower scope, and wait rather than starting something that will be killed
  half-landed.
- Any temptation to compute a treatment effect during this window -> refuse. The
  window is for landing data and for the two ex-ante artefacts in Phase 4. Outcome
  estimation happens after, against a frozen sample rule.

------------------------------------------------------------------
NOT IN SCOPE (do not attempt, and do not report as blockers of this task)
------------------------------------------------------------------
The literature package; the ConvExp rebuild (needs sec.gov); the Saglam-Tuzun PDF;
the trust -> asset-manager crosswalk; refraction's macro-consensus licence; every
DECISION_NEEDED fork. See p1/NON_WRDS_BLOCKERS.md — WRDS does not clear any of them.

DELIVERABLE: SUBSCRIPTION-REPORT.md, the landed raw/ tree with lineage sidecars,
verify_report.json, announcement_timing_table.{md,json}, intraday_request_list.csv,
the ops/decisions.md entries, and a manifest listing inputs+hashes, environment,
limitations and an explicit UNKNOWN list. Output without the manifest is not done.

自检清单(逐条 PASS/FAIL):
  discover ran against a live connection and discovered_schema.json is committed?
  every `resolved:` name came from the server or the web query tool, none from memory?
  anntims: existence, non-null rate and time zone all reported with locators?
  intraday availability + extended-hours coverage reported?
  verify.py green, or every FAIL explained and cut deliberately?
  matched_fundnos.json read by a human-readable report, not just written?
  Phase 4A table produced BEFORE any outcome variable was touched?
  raw parquets absent from the commit?
  every open question recorded in ops/decisions.md rather than resolved silently?
```

---

## Why the phases are ordered this way

`discover` before everything because the subscription decides the day, and two of
its answers (intraday availability, macro consensus) are owner decisions with
money attached. `stock_names` then `verify` before the large pulls because
`ncusip`-vs-`cusip` is the one mistake that produces a full, plausible, wrong
dataset. `fund_header` and the name match before `holdings` because a partial
match is invisible to the machine and drops treated funds. Phase 4 inside the
window because the announcement-timing table is pure ex-ante, costs minutes, and
is the precondition the plan itself places ahead of both the main sample rule
(§7.1.1) and the intraday purchase (§4.1) — and because getting it after the
account is released means asking for the account again.
