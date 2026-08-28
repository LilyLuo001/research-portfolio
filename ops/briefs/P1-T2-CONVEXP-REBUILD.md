# P1-T2 — rebuild ConvExp against the 172-event register

**Task id:** `P1-T2-convexp-rebuild`  ·  **Written:** seat C, 2026-08-27
**Runs on:** a machine with outbound HTTPS to `sec.gov` and `api.openfigi.com`.
**Supersedes:** `ops/briefs/P1-T2-recovery-BOX.md` — that brief tells you
`waves.csv` must come back byte-identical. **That is now wrong** and following it
will make you think you broke something. See "Trap 1".

---

## 0. Who you are and the rules you inherit

You are one execution unit in a multi-seat pipeline. The repo is the only shared
state; you never message another agent. Read `CLAUDE.md` at the repo root first —
its five meta-rules govern everything below. The two that will actually bite you
on this task:

- **Meta-rule 1 — the LLM is not a source of facts.** Every number you produce
  must come from code you wrote executed on real data, or from an extraction
  carrying a raw-source locator. A shares-outstanding figure "from memory" is a
  hallucination; discard it. This pipeline is built so that every cell traces to
  an EDGAR accession.
- **Meta-rule 4 — don't know → stop.** A fund with no matchable NPORT-P, or a
  stock with no resolvable shares outstanding, goes to a `NEED_HUMAN_*.csv` and is
  **dropped, never imputed**. Do not "fix" coverage by interpolating,
  back-filling, or substituting a nearby date. A 48% drop rate that is honest is
  worth more than a 95% one that is invented.

Work only inside `p1/`. `shared/` is read-only. Commit early and often.

---

## 1. What you are doing and why

`p1/conv_exposure_free.parquet` is the **treatment variable** of the whole paper:

```
ConvExp_i,e = Σ_f∈e (shares of stock i held by converting fund f, pre-conversion)
              ────────────────────────────────────────────────────────────────
                          shares outstanding of stock i
```

per stock `i` and conversion wave `e`. Everything downstream — the treated/control
split, the dose terciles, the power calculation, the DFA-concentration finding —
is computed off this file.

**It is stale.** On 2026-08-27 the event register was rebuilt from 131 dated
conversions to **172**, across **96 waves** instead of 78, after the owner-gate
recheck pool was adjudicated (`p1/EVENT-COUNT-AUDIT.md`). The committed parquet
predates that: it holds 6,377 cells built from the 131-event register, so **41
conversions — 10 of them equity_US — have no ConvExp cells at all.**

Why this matters more than it sounds. The paper's single biggest weakness is that
**92.8% of treated stocks come from one wave** (W002, the 2021-06-11 Dimensional
conversion), and the exclude-DFA robustness arm stands at **36 stocks against a
simulated power floor of 33**. Ten new equity_US conversions is the first real
chance to widen that arm since the problem was found. It may or may not help —
report what you find either way, and **do not tune anything toward a preferred
answer** (meta-rule: never specification-search; report the first run).

---

## 2. Before you touch anything

```bash
cd <repo>
git fetch origin && git checkout claude/p1-continuation-zgdcem && git pull
python -m pytest -q                      # expect all green (456 as of 2026-08-27)
python ops/runner/selfcheck.py
```

**This brief lives only on `claude/p1-continuation-zgdcem`, not on `main`** — so
the checkout above has to happen before you can read it. If you are reading this,
you already did. The branch is a small number of commits behind `main`; the only
files that differ under `ops/runner/` are `queue.yaml` and `state.json`, so the
gate scripts you run at step 8 are the same ones. Merge `main` in if you like, but
it is not a prerequisite.

Then confirm you actually have the egress this task needs — do not assume it,
and do not take a previous session's word for it either way:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -m 20 \
  -A "P1 Research <your-email>" https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany
```

`200` means proceed. Anything else (`000`, `403`, a proxy CONNECT failure) means
**stop and report** — this task cannot be done without SEC access, and there is no
offline substitute. The N-PORT cache under `p1/t2_free/cache/` is empty and
gitignored, so it will not save you.

Set the two environment variables:

```bash
export SEC_UA="Boston University research <your-real-email>"   # SEC 403s without a real UA
export OPENFIGI_KEY=...                                        # optional but strongly wanted
```

`SEC_UA` is **not optional** — SEC rejects anonymous automated traffic, and it is
genuinely load-bearing: no SEC access, no pipeline.

**`OPENFIGI_KEY` is a mapping FALLBACK, not load-bearing** (settled 2026-08-27 by
reading the code, not by assumption). Step 2 calls OpenFIGI *only* for holdings
where the N-PORT row itself carried no ticker (`valid_cusip(...) and not
h["ticker"]`). With no key the step is **skipped cleanly** and those holdings go
to `NEED_HUMAN_stocks.csv` — dropped, never imputed. So the pipeline **completes
and is correct without it**; what you lose is coverage, not validity. The code's
own note adds that these are mostly foreign/odd holdings that lack SEC XBRL
shares-outstanding anyway, i.e. many would drop at the denominator step
regardless.

**Still get the key** — it is free and widens coverage — but if you cannot, run
anyway rather than blocking.

**Report this number** (it answers a question we could not settle offline):
how many holdings lacked an N-PORT ticker, how many OpenFIGI resolved, and how
many of the unresolved would have dropped at the shares-outstanding step anyway.
Grep the run log for `Step2:` and `NO_SHARES_OUT`. That converts "fallback vs
load-bearing" from an architectural claim into a measured one.

---

## 3. Run it

Each step is cheap to repeat — the builder writes every raw HTTP body once under
`p1/t2_free/cache/` and re-reads from disk on reruns. Delete a cache file to force
one refetch.

```bash
# 1 — waves. No network. Reads events_merged.csv, writes waves.csv + waves_members.csv.
python p1/t2_wrds/build_waves.py

# 2 — the rebuild itself. SLOW: EDGAR is rate-limited and this walks ~172 funds'
#     filing histories. Expect hours on a cold cache. Run it under nohup/tmux.
python p1/t2_free/build_nport_convexp.py

# 3 — contract
python ops/runner/contracts.py conv_exposure_free p1/conv_exposure_free.parquet

# 4 — denominator recovery: SEC-renamed -> yfinance -> Stooq for cells dropped
#     for a missing shares-outstanding
python p1/output/convexp_coverage_audit/recover_denominators.py --online \
       --shares-held p1/t2_free/dropped_cells_shares_held.csv

# 5 — regenerate the coverage audit against the new build
python p1/output/convexp_coverage_audit/build_coverage_audit.py

# 6 — the scenario tables that carry the DFA finding
python p1/t1_reconcile/sample_scenarios.py

# 7 — pull scope (feeds the WRDS purchase)
python p1/wrds/universe.py --write

# 8 — gates
python -m pytest -q
python ops/runner/selfcheck.py
```

---

## 4. Five traps, each of which has already cost someone time

> **Fixed before you got here (2026-08-27).** `main()` in
> `build_nport_convexp.py` used to raise `UnboundLocalError` on the first
> aggregated cell — a leftover inline copy of the per-cell loop appended to
> `rows` / `nh_stocks`, while `rows, nh_stocks = _cell_rows(...)` further down
> made both names function-local for the whole function. It would have died in
> Step 2 **after** every EDGAR fetch had been paid for. The dead loop is deleted
> and `p1/tests/test_no_use_before_assignment.py` now lints the whole of `p1/`
> for that class of defect. Mentioned because if you are working from an older
> checkout, this is what you will hit.

### Trap 0 — Gate 0 needs data this brief did not previously fetch

Gate 0 (`p1/gate0_continuity/compute_continuity.py`) compares the **last
pre-conversion** N-PORT against the **first POST-conversion** N-PORT. The ConvExp
builder only ever fetches the pre side (`filed < eff_date`), so **the post side
does not exist anywhere in this repo** and cannot be derived from it.

While you have SEC egress, **also fetch the first NPORT-P filed AFTER each
conversion's effective date** for the surviving ETF, and land it alongside. Then
run Gate 0 and report the measured distribution — it decides whether the
"same portfolio, different wrapper" framing survives, and it gates the headline
regressions.

Gate 0 also needs **CRSP `CFACSHR`** to put share counts on a corporate-action
basis (a 2:1 split doubles raw share counts with zero trading and would read as
the manager buying). It is now in the `msf` pull. Until
`test_direction_against_a_real_crsp_split` runs green on landed data, the
multiply-vs-divide direction is **owner-asserted, not verified** — that test is
what makes it safe, and it currently skips.

### Trap 1 — `waves.csv` is SUPPOSED to change now

The older brief says step 1 must leave `waves.csv` byte-identical. That was true
when the register was frozen at 131 events. It is now 172, so `waves.csv` goes
from 78 to 96 waves. **Expect a diff.**

What must *not* change is any existing `(effective_date → wave_id)` binding.
Assignment was made append-only on 2026-08-27 precisely because a plain rank over
sorted dates would have renumbered 36 existing wave IDs — and since
`conv_exposure_free.parquet` carries `wave_id` per cell, every one of those cells
would have been re-pointed at the wrong wave **with nothing raised.** Verify:

```bash
python -m pytest p1/tests/test_recheck_resolution.py -q   # includes the renumber guard
```

The Dimensional anchor must still be **W002 / 2021-06-11**. If it is not, stop —
every scenario table and the 92.8% figure key on it.

### Trap 2 — declare `val_usd`, in the same commit as the parquet

`ops/contracts/conv_exposure_free.yaml` has a **pending** declaration for the
N-PORT value column. The pipeline emits **`val_usd`** (with the underscore), the
committed parquet carries neither spelling, and `contracts.py` treats every
declared column as mandatory — so the declaration and the rebuilt parquet must
land together. Declaring early fails the artifact Gate 2 was signed on.

**Add `val_usd: {min: 0}` to the contract in the SAME commit that lands the new
parquet.**

**Two more columns are now pending on exactly the same terms** (v2.1d):
`holdings_asof_min` and `holdings_asof_max`. They carry the N-PORT
`genInfo/repPdDate` — the date the share counts are AS OF — because the CRSP
CFACSHR corporate-action factor must be joined on that date, not on the filing
date. A March 31 share count adjusted by a May 30 factor does not remove an April
split; it inserts one, and both numbers still look plausible afterwards. Declare
all three in the same commit as the parquet:

```yaml
  val_usd: {min: 0}
  holdings_asof_min: {}
  holdings_asof_max: {}
```

A fund whose N-PORT has no `repPdDate` is now refused into
`NEED_HUMAN_funds.csv` with `reason=no_repPdDate` rather than dated by `filed`.
If that count is not ~0, say so in the run report — it is a coverage loss, not a
nuisance, and it must not be "fixed" by falling back to the filing date.

(The file used to carry a second, contradictory note saying to declare `valusd`
without the underscore, which would have failed the validator. That spelling came
from a dead inline loop — see the note at the top of §4 — and both are now gone.
`valusd` survives only as an internal aggregation key and as a column of the
dropped-cells sidecar CSV; neither is this parquet, and neither should be renamed.)

### Trap 3 — `NEED_HUMAN_stocks.csv` has a frozen four-column schema

Do not widen it. The extra quantities ride along internally and are written to the
separate sidecar `p1/t2_free/dropped_cells_shares_held.csv`, which is what step 4
consumes. `_write_need_human` drops the extras with `extrasaction="ignore"` on
purpose. Meta-rule 3: never rename or add to a frozen column set.

### Trap 4 — two known gaps are best-effort and must be *reviewed*, not trusted

Both are logged loudly and neither has ever been validated against live EDGAR:

- **G1 — fund→series matching in multi-series trusts.** The builder fuzzy-matches
  the fund name against the N-PORT `<seriesName>`. Dimensional, JPMorgan, Goldman
  and Fidelity all file many series under one CIK, so a wrong match silently
  attributes the wrong portfolio to a conversion. **Grep the log for
  `SERIES_MATCH` and read every line for the newly added funds.** This is the
  single highest-risk step in the pipeline.
- **H2 — `mcap_decile`** is computed from the N-PORT-implied price
  (`valUSD / shares × shares_outstanding`), with no external price feed. Thin
  waves log `MCAP_THIN` and get a null decile. That is acceptable; inventing a
  price is not.

### Trap 5 — one treated cell now depends on the `asset_class` backlog

Until 2026-08-27 zero treated cells sat in a wave containing an unclassified fund,
which is what made the DFA finding independent of that backlog. Releasing
**Thrivent Mid Cap Value Fund** (no `asset_class`) into wave W065 (2025-11-14),
which already carried one treated cell (BELFB, ConvExp 1.30%), makes it **exactly
1**. A test pins that number. If your rebuild changes it, **re-audit — do not edit
the test to match.**

---

## 5. What "done" means

All of these, not a subset:

1. `python ops/runner/contracts.py conv_exposure_free p1/conv_exposure_free.parquet` → **PASS**
2. `val_usd` declared in the contract, in the same commit as the parquet
3. A lineage JSON emitted next to the parquet naming `events_merged.csv`,
   `waves_members.csv` and the builder as inputs
4. `python -m pytest -q` → all pass. **If a test fails because a real number
   moved, update the test's pinned number AND say so in the commit message with
   the new value and why it moved. If a test fails because something broke, fix
   the thing, not the test.**
5. `python ops/runner/selfcheck.py` clean
6. `p1/t2_free/diagnostics.md` regenerated and read by you
7. A short memo at `p1/t2_free/REBUILD-2026-08.md` answering, with numbers:
   - cells before → after; distinct waves with any cell; distinct CUSIPs
   - **treated stocks at ConvExp ≥ 0.5% and ≥ 1%, total and excluding W002**
   - how many of the 41 newly released conversions produced ≥1 treated cell, and
     which ones produced none, and why (no N-PORT? non-US holdings? no denominator?)
   - **whether the exclude-DFA arm now clears the power floor of 33** — state the
     number plainly whichever way it lands
   - the new W002 share of treated stocks (was 92.8%)
   - `SERIES_MATCH` review: how many newly added funds matched a series, how many
     you hand-checked, and any you are unsure about
   - drop-rate before → after, and the recovery pass's yield
8. Committed and pushed to `claude/p1-continuation-zgdcem` (or a branch off it —
   never to `main` directly, never to another seat's branch)

---

## 6. When you get stuck

Emit `NEED_HUMAN: <reason>` in the memo and keep going on everything that does not
depend on it. Specifically **do not**:

- impute a denominator, a price, or a holding
- widen a frozen schema to make something fit
- delete or re-key rows to make a contract pass
- edit a pinned test number to match a result you have not explained
- rerun with different parameters because you did not like the first answer

The finding that 92.8% of the sample is one wave was discoverable only because the
treatment variable was built, committed and inspectable before any outcome
existed. Keep it that way: this task must finish before anyone looks at an outcome
variable, and nothing here is allowed to be tuned against one.

---

## 7. Context you may want

| file | what it gives you |
|---|---|
| `p1/EVENT-COUNT-AUDIT.md` | why the register moved 131 → 172, and what is still unresolved |
| `p1/ROADMAP-2026-08-19.md` | where P1 stands overall; the DFA-concentration headline |
| `p1/t2_free/build_nport_convexp.py` | the builder's own docstring is the best spec of the data flow |
| `ops/contracts/conv_exposure_free.yaml` | the frozen output schema |
| `p1/output/convexp_coverage_audit/coverage_audit_memo.md` | the drop-rate argument this rebuild is meant to test |
| `docs/基金转换实验_博士研究计划.md` §5 | the ConvExp definition in the plan's own words, incl. why intensity uses the **last pre-conversion** holding and is never revised afterward |
