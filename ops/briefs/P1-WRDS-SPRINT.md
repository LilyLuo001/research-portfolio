# P1 — the WRDS sprint runbook

**Premise** (`ops/briefs/WRDS-access-assessment.md`): WRDS is not a one-shot need,
it is the spine of P1-T2→T5 and refraction R2/R10. But it collapses to five
distinct pulls that can all be taken in one sitting and cached. Borrowing an
account for **one concentrated 3–5 day window** beats a 3–6 week on/off rental —
*provided every script is written before the account is live.* This is that
runbook; the scripts are in `p1/wrds/`.

## Before you book anything (all of this is already done, offline)

```bash
python p1/wrds/universe.py        # what will be pulled, derived from committed files
python p1/wrds/pull.py status     # what names are still unconfirmed
python -m pytest p1/tests/test_wrds_layer.py -q
```

`p1/wrds/pull_scope.json` is committed and is the sheet you hand to whoever books
the account. As of 2026-08-18 it says: **6,747 CUSIPs** to map (2,241 with a
computed ConvExp + 4,635 dropped for a missing denominator — those are treated
stocks too, they lost a denominator, not a holding), **78 waves** from 2021-03-26
to 2026-11-20, daily window **2020-03-04 .. today**, −250/+120 trading days
around each effective date. Three waves are future-dated and have no post-window
yet; they are flagged, not silently pulled.

## The one rule this package exists to enforce

A WRDS column name written from memory **does not raise — it returns a different
number.** So nothing here builds SQL from a name until that exact name has been
read off the live server. `p1/wrds/tables.yaml` states what each field must *mean*;
its `candidates:` are unverified hints scraped from this repo's own history and
confer nothing. `resolved:` is filled only by `pull.py resolve`, against the
inventory `pull.py discover` reads from the server.

Ships inert: every `resolved:` is null, and a test enforces that.

## The window itself

```bash
export WRDS_USER=<username>          # case-sensitive
python p1/wrds/pull.py discover      # server lists its own tables/columns
python p1/wrds/pull.py resolve       # unique-candidate matches only; rest -> NEED_HUMAN
python p1/wrds/pull.py status        # read the NEED_HUMAN list
```

Settle whatever `resolve` could not — **at the WRDS web query tool, not from
memory** — by pasting real names into `tables.yaml`'s `resolved:` fields. The
resolver deliberately refuses to pick when several candidates exist or none do;
a "best match" heuristic there would reintroduce exactly the guessing this
package prevents.

Then, **in this order** (order is load-bearing):

```bash
python p1/wrds/pull.py pull --pull stock_names   # CUSIP -> PERMNO. small. FIRST.
python p1/wrds/pull.py pull --pull mf_holdings
python p1/wrds/pull.py pull --pull msf
python p1/wrds/pull.py pull --pull dsf           # the big one, scoped by permno
python p1/wrds/pull.py pull --pull taq_iid
python p1/wrds/pull.py pull --pull ibes
```

`stock_names` comes first because the universe is **endogenous** — it is whatever
the converting funds held — so `msf`/`dsf` cannot be scoped until CUSIP→PERMNO
has actually landed. Unscoped, the daily pull is the entire CRSP universe over
six years: the 5–10 GB case instead of ~1–3 GB. The scripts refuse rather than
run unscoped.

Use `--dry-run` first on each to read the SQL before it executes. Every pull
lands an immutable parquet under `p1/wrds/raw/` with a lineage JSON carrying the
exact query, and refuses to overwrite (`--force` to replace deliberately).

## Three questions discovery cannot answer

Listing columns never tells you what a number *means*. These are flagged in
`tables.yaml` and `pull` will hold on them until you pass
`--accept-open-questions`:

1. **`shrout` units.** The existing scaffold multiplies by 1000. A 1000× error
   here would not raise — it would move every exposure. Confirm against the WRDS
   variable documentation.
2. **Effective-spread convention** (dollar vs proportional, quote-matching rule)
   behind whichever TAQ-IID field is chosen. This is also one of the ten
   CITE_REQUEST items in `p1/t3_spec_preflight.md`.
3. **SUE: analyst expectations vs time-series model.** The DECISION_NEEDED fork
   named in `docs/Project_1.md` §125. The IBES pull supports the analyst branch;
   the time-series branch needs Compustat quarterly earnings instead. Do not pick
   one silently.

Landing raw data with these open is fine. Computing a *number* from it is not.

## After the window

Release the account. Everything downstream (`conv_exposure` on permno,
`outcomes_panel`, T4 replication, T5) runs off `p1/wrds/raw/`. Then:

- merge `p1/t2_free/conv_exposure_free_crosswalk.csv` to the landed
  `stock_names` pull so the free-path ConvExp gains a permno key, and compare
  the two ConvExp constructions — that comparison is a free validation of the
  entire free path, and worth reporting either way it lands;
- record the outcome in `ops/decisions.md`;
- T3 still needs its literature package independently (`p1/t3_spec_preflight.md`)
  — data access does not unblock the spec.
