# P1 — the WRDS runbook for a ONE-DAY window

**Rev 2, 2026-08-27.** Rev 1 assumed a 3–5 day borrowed window. The owner is
renting **one day**, so this is rewritten as an execution sheet: an order, a
clock, hard cut lines, and the decisions that must be settled *before* the
account goes live rather than during it.

Everything in `p1/wrds/` is written, tested offline and inert. The account is
needed only for `discover` and `pull`.

---

## The single sentence that governs the day

> A WRDS column name written from memory **does not raise — it returns a
> different number.**

So nothing builds SQL from a name until that name has been read off the live
server. `tables.yaml` states what each field must *mean*; its `candidates:` are
unverified hints and confer nothing. `resolved:` is filled only by
`pull.py resolve` against the server's own inventory. Ships inert, and a test
enforces that it ships inert.

The corollary for a one-day window: **when the resolver refuses, do not guess to
save time.** Open the WRDS web query tool in another tab, copy the real name,
paste it. That costs two minutes. A wrong name costs the whole dataset, silently,
and you find out weeks later.

---

## Before the account goes live (do this today)

### 1. Confirm the machine is ready

```bash
python p1/wrds/universe.py                    # the scope, derived offline
python p1/wrds/pull.py status                 # everything BLOCKED is correct here
python -m pytest p1/tests/test_wrds_layer.py p1/tests/test_wrds_verify.py -q
pip install wrds pandas pyarrow               # `wrds` is only importable on a connected node
```

`pull.py status` should report every pull BLOCKED with an empty inventory. That
is the shipped state, not a problem.

### 2. Send the seller the four questions

They are at the bottom of `p1/wrds/TABLE-REQUEST.md`. Each one costs window time
if discovered live and takes the seller one sentence:

1. delisting table names (`dsedelist`/`msedelist` or the CIZ-format equivalent)
2. IBES adjusted (`statsum_epsus`) vs unadjusted (`statsumu_epsus`) — **for SUE
   the unadjusted file is preferred**
3. TAQ **WRDS Intraday Indicators** — present? keyed on symbol or permno?
   covers 2019→2026 including small caps?
4. `comp.fundq` / `comp.funda` are the **North America** files, not Global

### 3. Pre-record the one decision the resolver will refuse to make

`crsp.stocknames` carries **both** `ncusip` and `cusip`, so `resolve` will report
it ambiguous and stop. The answer is **`ncusip`** — the historical CUSIP valid
over `[namedt, nameendt]`, which is what a point-in-time N-PORT holding must
match. Reasoning is recorded as a `decision_hint` in `tables.yaml`. Paste it from
the web query tool when asked.

---

## The window — an order and a clock

Times are working estimates for planning the day, not measurements. The
dependencies, however, are enforced in code: every downstream pull **refuses**
with a `PULL ORDER` message rather than running unscoped.

| # | step | est | why here |
|---|---|---:|---|
| 0 | `export WRDS_USER=<username>` (case-sensitive) | 2 m | |
| 1 | `pull.py discover` | 10–20 m | the server lists its own tables/columns |
| 2 | `pull.py resolve` then `pull.py status` | 10 m | unique-candidate matches only |
| 3 | settle every `NEED_HUMAN` at the web query tool | 20–40 m | **the real variable** |
| 4 | `pull --pull stock_names` | 5 m | CUSIP→PERMNO + ticker. **Everything waits on this.** |
| 5 | **`python p1/wrds/verify.py`** | 1 m | ← **stop here if coverage FAILs** |
| 6 | `pull --pull ccm_link` | 5 m | gvkeys, before any Compustat |
| 7 | `pull --pull msf` | 10 m | small |
| 8 | `pull --pull compustat` | 15 m | scoped by gvkey |
| 9 | `pull --pull ibes` | 20 m | three parts, cusip-scoped |
| 10 | `pull --pull mf_holdings` | 30 m | fund_header → name match → holdings |
| 11 | **`pull --pull dsf`** | 60–120 m | the big one; ~1–3 GB scoped |
| 12 | `pull --pull taq_iid` | 30–60 m | skip if CRSP bid/ask came back populated |
| 13 | **`python p1/wrds/verify.py`** again | 2 m | the release gate |
| 14 | commit provenance — see below | 10 m | **before** releasing |

Run `--dry-run` first on each pull to read the SQL before it executes. Every pull
lands an immutable parquet under `p1/wrds/raw/` with a lineage JSON carrying the
exact query, and refuses to overwrite (`--force` to replace deliberately).

### Step 14 — what is committed, and where the data has to live

**The raw parquets are licensed CRSP/Compustat/IBES rows and must never reach the
repository.** `p1/wrds/raw/*` is gitignored and a policy test enforces it. What
*is* committed, and must be, before the account goes back:

```bash
python p1/wrds/verify.py --json > p1/wrds/verify_report.json
git add p1/wrds/tables.yaml            # the resolved names — the day's real product
git add p1/wrds/raw/*.lineage.json     # exact SQL + row count per landed file
git add p1/wrds/raw/mf_holdings__matched_fundnos.json
git add p1/wrds/verify_report.json
```

The `.lineage.json` sidecars are provenance, not data — each carries the exact
query, the row count and the code version behind one parquet. They are
deliberately negated out of the ignore rule, because a pull with no committed
locator fails meta-rule 1.

**This implies where the pull must run.** Since `raw/` cannot travel through git,
the machine that pulls has to be the machine that later computes the outcomes, or
share storage with it. Decide that before the day starts — the always-on box has
been down since 2026-07-10 (`ops/briefs/PORTFOLIO-REVIEW-AND-PLAN-2026-08-19.md`
deviation D1), so "pull it on the box" is not currently an answer. A local
machine with ~5 GB free and the repo checked out is fine; an ephemeral container
is not.

### Step 5 is not optional

`verify.py` exists because of one asymmetry: a bad pull is cheap to fix while the
account is live and needs a **second rental** afterwards. The check that matters
most is `cusip->permno coverage`. If it FAILs, you almost certainly resolved
`cusip` where you wanted `ncusip` — fix `tables.yaml`, `pull --force`, re-verify.
Doing this at minute 40 costs five minutes. Doing it tomorrow costs a day.

### If the clock runs out — the cut order

Drop from the bottom up. Everything above a cut line is worth more than
everything below it.

| cut | what you lose |
|---|---|
| **never cut** `stock_names`, `dsf`, `dsi` | without these there is no paper at all — no permno, no returns, no benchmark |
| `dsedelist` | spine two acquires survivorship bias. Cheap and fast; only cut in genuine emergency |
| `taq_iid` | spine four's effective spread. **Free to cut if CRSP bid/ask came back populated** — `verify.py` tells you which world you are in |
| `mf_holdings` (3 parts) | the CRSP cross-check on the free-path ConvExp. The free path already works; this validates it |
| `msedelist` | only the monthly Jegadeesh reversal variable (§7, 2-7) |
| `compustat.funda` | the §107 control match. Painful — but the intensity-tercile design (V-3, the *primary* spec) uses within-treated comparisons and does not need matched outside controls |

**Do not cut `ccm_link` while keeping `compustat`** — the fundamentals pull is
scoped by gvkey and will refuse without it.

---

## Three questions discovery cannot answer

Listing columns never tells you what a number *means*. These are flagged in
`tables.yaml` and `pull` holds on them until you pass `--accept-open-questions`.
**Landing raw data with these open is fine. Computing a number from it is not.**

1. **`shrout` units.** The existing scaffold multiplies by 1000 (assumes
   thousands). A 1000× error would not raise — it would move every exposure.
2. **Effective-spread convention** behind whichever TAQ-IID field is chosen
   (dollar vs proportional, quote-matching rule). Also CITE_REQUEST item in
   `p1/t3_spec_preflight.md`.
3. **SUE: analyst expectations vs time-series model.** The DECISION_NEEDED fork
   at `docs/Project_1.md` §125. This pull supports both branches — which is
   exactly why it cannot pick.

Plus two added in rev 2:

4. **CCM link filter.** The standard filter keeps `linktype in ('LU','LC')` and
   `linkprim in ('P','C')` and applies `[linkdt, linkenddt]`. The pull
   deliberately does **not** apply it (that would discard the rows needed to
   audit the choice). Dropping the filter at merge time does not raise — it
   duplicates firm-quarters through secondary and superseded links.
5. **The fund-name match.** Converting funds are selected from `crsp.fund_hdr` by
   normalised name, because `events_merged.csv` carries a real mutual-fund ticker
   on 8 of 131 rows. The match set is written to
   `raw/mf_holdings__matched_fundnos.json`. A zero match refuses; a **partial**
   match cannot be detected automatically. Read the file.

---

## After the window — none of this needs the account

Release it, then:

- merge `p1/t2_free/conv_exposure_free_crosswalk.csv` to the landed
  `stock_names` pull so the free-path ConvExp gains a permno key, and run
  `python p1/reconcile/convexp_reconcile.py` — comparing the free EDGAR
  construction against CRSP is a real credibility item, and worth reporting
  whichever way it lands;
- record `shrout` units, the spread convention, the SUE fork, the CCM filter and
  the fund-match outcome in `ops/decisions.md`, **pre-outcome**;
- T3 still needs its literature package independently
  (`p1/t3_spec_preflight.md`) — data access does not unblock a spec.

## What WRDS does *not* fix

`p1/NON_WRDS_BLOCKERS.md` has the full list. The two that matter most for the
sample, both needing `sec.gov` rather than WRDS:

- **the recheck pool** — 111 event records / 66 funds parked by the owner gate at
  `recheck`, of which 43 carry a verbatim effective date across 26 potential new
  waves, 15 already with a complete +120-day post-window. See
  `p1/EVENT-COUNT-AUDIT.md`. This is a larger lever on the event count than
  anything in this runbook.
- **the `asset_class` backlog** — blank on 25 of 131 events, so "36 equity_US" is
  a floor.
