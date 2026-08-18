# P1-T2 audit item 5 — the international sleeve: what each option costs

The coverage audit closed four of its five items mechanically. The fifth is a
**judgement call that belongs to the owner**: does the paper define its sample as
US-listed and document the international-equity conversions as out of scope, or
does it scope a separate non-US analysis? This memo does not make that call. It
attaches numbers to it, so the call is made against evidence instead of
intuition — and, per the portfolio's no-specification-search rule, so it can be
**recorded before** the main estimation rather than after seeing outcomes.

Every number below is recomputed from committed artifacts by
`international_sleeve_scoping.py` (offline, no network); the table is
`international_sleeve_scoping.csv`. Fund→asset_class comes from
`events_merged.csv`, wave membership from `waves_members.csv`, cells from
`conv_exposure_free.parquet`.

## The wave landscape

78 waves in all: **58 touch no international fund, 12 are purely international,
8 are mixed**. Of these, 49 waves have at least one computed ConvExp cell.
**The DFA anchor wave (2021-06-11, W002) is `no_intl`** — it is unaffected under
every option, which is the single most important fact here.

## What each scope keeps

| scope | waves | cells | distinct stocks | ≥0.25% | ≥0.5% | ≥1% |
|---|---|---|---|---|---|---|
| **ALL (as built)** | 49 | 6,377 | 2,241 | 761 | **389** | **24** |
| Option A — drop *pure*-international waves | 40 | 6,059 | 2,055 | 750 | **381** | **21** |
| Option A-strict — drop *any* wave touching international | 33 | 5,259 | 1,977 | 742 | **373** | **16** |
| (component) only mixed-international waves | 7 | 800 | 676 | 9 | 8 | 5 |
| (component) only pure-international waves | 9 | 318 | 286 | 11 | 8 | 3 |

Read at the ≥0.5% treated line — the line Gate 2 was read on — **the
international sleeve is nearly free to drop: 389 → 381 stocks (−2%)**, against a
P1-T2a power floor of ≥33 on the smaller side. Both options clear it by an order
of magnitude.

The ≥1% line behaves differently: 24 → 21 under Option A, but **24 → 16 under
A-strict**. A third of the most-intensely-treated names sit in waves that merely
*contain* an international fund. If any spine or robustness cut keys on ≥1%
dose, A-strict is the expensive choice and should be taken deliberately, not by
default.

## The subtlety that decides how much work each option is

ConvExp cells are aggregated per `(cusip, wave)` **across all funds converting in
that wave**. So a cell in a mixed wave cannot be attributed to the US fund or the
international one after the fact — the attribution exists in the raw N-PORT
holdings, but not in the built parquet.

Consequences:

- **"Exclude international *waves*"** is a filter on the committed data. Zero
  rebuild; it is the two Option-A rows above, computable today.
- **"Exclude international *funds*"** is NOT. It requires re-running
  `build_nport_convexp.py` with a per-fund asset-class filter, on the box, with
  network. It is the only version that cleanly keeps the US half of the 8 mixed
  waves (W029, W032, W048, W054, W056, W063, W064, W073 — 800 cells, 676 stocks).

If the owner wants the fund-level version, that is a box work item, not a
filter, and it should be bundled with the pending re-run that activates audit
items 2 and 4.

## Options as they would read in the paper

**Option A — US-listed sample definition (recommended).** The sample is
US-listed common equity; conversions of international-equity funds are reported
in the sample-definition footnote as out of scope, with the mechanical reason:
their holdings are foreign-listed and carry no US shares-outstanding
denominator, so they contribute no measurable treatment intensity. Cost: 8
stocks at the ≥0.5% line. This is a **sample definition, not a data problem** —
Mirae W020 alone accounts for 49% of all dropped cells precisely because it holds
Korean/Asian equities, and CRSP would not have placed most of them in a US event
study either.

**Option A-strict — exclude any wave touching an international fund.** Cleaner
to state ("no wave in the sample includes an international-equity conversion"),
materially more expensive at the ≥1% line (24 → 16). Choose only if the mixed
waves are judged to contaminate the treatment definition.

**Option B — separate non-US analysis.** Scientifically the most complete, and
the audit noted the 31 excluded non-equity funds could seed a companion
analysis. But it needs a non-US shares-outstanding source (the free SEC-XBRL
route covers US-domestic registrants only), which is exactly the gap the free
path cannot close. **Treat B as a future paper, not a scope decision for this
one** — and do not let it block the main run.

## What to record, and where

Whichever option is taken, record it in `ops/decisions.md` **before** the T5 main
estimation, so the sample definition is fixed independently of any outcome.
Nothing in this memo touches outcomes; every number is a pre-period coverage
count.

**Open question for the owner, one line:** Option A, A-strict, or A + a
fund-level rebuild that rescues the mixed waves?
