# refraction — quality review and execution caveats

_Seat C, 2026-08-19. Scope: `refraction/` only. Every finding below was
reproduced in the container today; the reproduction is printed with each one.
No code was changed — this review ends with a proposed fix set for the owner to
approve, because three of the fixes change R2's gate semantics and this is a
preregistration-sensitive pipeline._

---

## Verdict

**The engineering quality is high — among the best in the portfolio.** The two
iron rules are genuine program invariants rather than documentation, the guards
fail closed, there are no magic numbers, and the tests include tampered-world
fixtures that are *required* to fail. 42 tests pass in ~1s with the network
poisoned.

**But the assert battery has a hole that matters.** Two of the thirteen hard
assertions cannot fail through the production entry point, and the P1 → refraction
data boundary is broken against P1's own frozen contract. Both are cheap to fix
**now** and expensive to fix after R2 is implemented against them.

Nothing here threatens the design. Everything here threatens the *evidence that
the design was followed* — which, for a chapter whose whole selling point is a
machine-enforced preregistration discipline, is the thing worth protecting.

| Severity | Finding | Status |
|---|---|---|
| 🔴 Blocker | R-1 A10 crashes on a contract-conformant P1 file | Reproduced |
| 🔴 Blocker | R-2 P1's `permno` join key is 100% empty; 3 of 4 declared inputs absent | Reproduced |
| 🟠 Serious | R-3 A11 and A14 are vacuous in the CLI path | Reproduced |
| 🟠 Serious | R-4 documented `betas` schema omits a column A9 requires | Reproduced |
| 🟡 Moderate | R-5 test fixtures encode the code's assumptions, not the contracts | Root cause of R-1/R-4 |
| 🟡 Minor | R-6 A6 static scan misses most of `refraction/` | Confirmed |
| 🟡 Minor | R-7 A9 divides by `1 − w_i` with no single-name-basket guard | Confirmed |
| ⚪ Status | R-8 the R13 scanner has never run | Confirmed |

---

## R-1 🔴 A10 crashes on a P1 file that conforms to P1's frozen contract

`assert_panel.py` declares its expected input as:

```
convexp : permno, wave, conv_exp          (P1 frozen file, read-only)
```

and `a10_convexp_frozen` merges `on=["permno", "wave"]`.

P1's frozen contract `ops/contracts/conv_exposure.yaml` declares:

```yaml
primary_key: [permno, wave_id]
```

There is no `wave` column and never will be — CLAUDE.md rule 3 freezes column
names in `ops/contracts/` and forbids renaming. So refraction is coded against a
schema that does not exist.

**Reproduction** — a `convexp` frame built exactly to P1's frozen contract:

```
A10 RAISED KeyError: 'wave'
```

It does not fail the assert. It raises, which means `run_all` aborts and no
report is produced at all.

Note this is *not* a naming quibble about refraction's own panel: refraction's
`panel_ann.yaml` legitimately uses `wave` for its own output, and that is
internally consistent. The defect is purely on the **read** side of the P1
boundary.

**Fix (forced, not a judgement call):** rename on read, never on write. In
`a10_convexp_frozen`, accept `wave_id` and normalise to `wave` internally, or
add an explicit `_read_p1_convexp()` adapter that does the mapping in one place
and is the only function allowed to touch P1 files. The frozen P1 contract wins.

---

## R-2 🔴 The P1 join key is empty, and most declared inputs do not exist

`refraction/CLAUDE.md` names four READ-ONLY P1 inputs. Checked today:

| Declared input | Present? |
|---|---|
| `p1/events_merged.csv` | ✅ exists |
| `p1/conv_exposure.parquet` | ❌ **missing** — only `conv_exposure_free.parquet` exists |
| `p1/holdings_weights.parquet` | ❌ **missing** |
| `p1/ibes_sue.parquet` | ❌ **missing** |

Worse, the file that *does* exist cannot be joined on:

```
permno non-null: 6377 / 6377
permno dtype:    str
permno sample:   ['', '', '']
```

Every `permno` is the **empty string**, not null. This is the documented
consequence of the free EDGAR path (`ops/briefs/WRDS-access-assessment.md`:
"`permno` — left blank; the crosswalk recovers it if CRSP access returns"), but
it has a nasty property: `notna()` returns 6377/6377, so any liveness check
written as `df.permno.notna().any()` passes on a column that is entirely blank.

**Consequence:** R2 cannot be dispatched against real P1 data today, regardless
of the WRDS table list the README already flags. This is a harder block than the
README's "blocked on R1b + CRSP table list" suggests — the *frozen input P1 is
supposed to hand over does not yet exist in joinable form*.

**Fix:** two parts, both cheap.
1. Correct `refraction/CLAUDE.md` to name the file that actually exists, and mark
   the other three as NOT YET PRODUCED with the P1 task that will produce them.
2. Add a precondition check that refuses to run R2 when `permno` is blank —
   testing emptiness, not nullity. A blank join key must be a loud refusal, not a
   silent empty merge.

---

## R-3 🟠 Two hard assertions cannot fail through the CLI

`run_all` defaults:

```python
if expected_pairs is None:
    expected_pairs = panel[["permno", "announcement_id"]].drop_duplicates()
```

— i.e. **A11 compares the panel against itself.** And A14 returns
`_res(True, "skipped: no upstream frames supplied (dev mode)")` when
`upstream_for_a14` is None.

`main()` — the production CLI, and the only documented way to run the battery —
passes neither:

```
CLI main() passes expected_pairs?  False
CLI main() passes upstream_for_a14? False
A11 in HARD: True | A14 in HARD: True
```

Both are counted in `HARD`, so `overall_pass` can be `True` while the two checks
that exist to catch silent row loss and upstream drift have never executed.

**Reproduction** — a panel that has genuinely lost a row:

```
with the real expected set passed in:   False  <- correctly FAILS
with run_all()'s default:               True   <- vacuously PASSES
```

This matters more than a normal test gap because the manual makes A14 an explicit
*acceptance criterion* for R2 (§167: 随机抽 20 行回溯上游（断言 A14）), and the
R14 Meta-QA checklist item ⑥ checks the manifest for A4's PASS record. A manifest
generated by the CLI today would truthfully report `A11: pass, A14: pass` while
neither was run. The code comments are honest about this ("REQUIRED on real data
— R14 checks this is not skipped"), but honesty in a docstring is precisely the
"prose that was never executed against the code" failure the DAX red team
already caught elsewhere in this portfolio.

**Fix (changes gate semantics — needs owner sign-off):** make the battery
fail closed. Add `strict: bool = True` to `run_all`; when strict and either input
is absent, the assert records `pass: False` with detail `NOT EXECUTED — required
input not supplied`. Tests that intentionally exercise dev mode pass
`strict=False`. `main()` gains the two required inputs and refuses without them.

---

## R-4 🟠 The documented `betas` schema omits a column A9 requires

Module docstring:

```
betas   : permno, wave, beta_i, se_beta, n_pre_announcements, max_est_date
```

But `a9_loo_reconstruction` reads `take["beta_b_loo"]`, and `beta_b_loo` appears
only in the *panel* schema. Building `betas` to the documented schema and calling
A9 gives:

```
KeyError: 'beta_b_loo'
```

The suite does not catch it because `conftest.py`'s `betas` fixture silently adds
the column (line 49). The same fixture also adds `effective_date` to `convexp`,
which the docstring's convexp schema likewise omits — though `main()` at least
fails loudly on that one.

**Fix:** correct the docstring to include `beta_b_loo` in `betas` (and
`effective_date` in `convexp`), or move A9's LOO check to read `beta_b_loo` from
the panel. Either is fine; leaving the documented contract wrong is not, because
R2's implementer will build to the docstring.

---

## R-5 🟡 The fixtures encode the code's assumptions, not the contracts

This is the root cause of R-1 and R-4 rather than a separate defect, but it is
the one worth fixing structurally.

`conftest.py` builds every frame the way `assert_panel.py` expects rather than
the way the frozen contracts declare. So 42 green tests coexist with a battery
that crashes on the real P1 file. The tests validate self-consistency, not
conformance.

**Fix:** add one contract-conformance test per boundary — build the fixture
frames from `ops/contracts/*.yaml` column lists (or at minimum hard-code P1's
`wave_id` for the convexp fixture) and assert the battery survives. One test
would have caught R-1 at write time.

---

## R-6 🟡 A6's static scan misses most of `refraction/`

```
A6 default scan dir: /home/user/research-portfolio/refraction/pipeline
```

`run_all` defaults `src_dir` to `HERE.parent`, which is `refraction/pipeline/`.
`refraction/scan.py`, `refraction/guards/` and any future R6/R7 module sit
outside it. The manual says the scan covers 代码中 — the code, not one package.

**Fix:** default `src_dir` to `HERE.parents[1]` (`refraction/`).

---

## R-7 🟡 A9 has no guard for a single-name basket

`recon = (beta_b_full − w_i·beta_i) / (1 − w_i)` divides by zero when `w_i = 1`,
which is exactly the single-holding-wave case. Produces `inf`/`nan` rather than a
diagnosed failure.

**Fix:** skip and *report* rows with `w_i` within float tolerance of 1, rather
than dividing. Silently producing `nan` in a correctness check is the worst
outcome available.

---

## R-8 ⚪ The R13 scanner has never run

`refraction/scans/` contains `manifest.md` and nothing else — no `hits_*.csv`,
no `seen_ids.json`. The scanner is complete and tested, but the resident monitor
it implements has never executed once. This is expected (cron wiring is a seat-D
edit and the box has been dead since 2026-07-10), and it is correctly *not*
marked complete in `state.json` per the resident-node convention. Recorded here
so it is not mistaken for a working monitor.

One environment note from the manifest worth checking before wiring: `scan.py` is
deliberately kept Python 3.6-compatible because "the always-on box venv is 3.6",
while `ops/box/README.md` provisions a fresh `python3 -m venv`. Confirm the box's
actual interpreter before relying on either assumption.

---

## What is genuinely good, and should not be traded away

Stated explicitly because a review that lists only defects misrepresents this
codebase:

- **The iron rules are real invariants.** `assert_prereg_ok()` refuses on a null
  timestamp, a missing URL, an unfrozen `w_shrink`, *and* a system clock at or
  before the OSF timestamp. It rejects an unzoned timestamp rather than guessing
  a timezone — the right call, and rarer than it should be.
- **R6+ is guard-blocked by design and correctly still blocked.** No outcome
  estimation can run. That is the single most important property of this chapter
  and it holds.
- **A5 is honest.** It is specified as informational, implemented as always-pass,
  and deliberately excluded from `HARD` — matching the manual's "写入 manifest"
  wording rather than silently promoting itself to a gate.
- **A10's `tol=0.0`** is exact-match against the frozen file. Strict, and right.
- **A3 matches the spec exactly** — additive split identity at 1e-8 with
  missing-open rows legal but counted, per manual §196.
- **The tampered-world tests are real.** Duplicate keys, lookahead, magic
  `w_shrink`, broken LOO, silent drops and upstream mutation each have a test
  that must fail.

---

## Proposed fix set

Ordered; all inside `refraction/` (seat C) except where noted.

| # | Fix | Touches | Needs sign-off? |
|---|---|---|---|
| 1 | P1 read adapter: accept `wave_id`, normalise internally (R-1) | `assert_panel.py` | No — forced by CLAUDE.md rule 3 |
| 2 | Contract-conformance test at the P1 boundary (R-5) | `tests/` | No — pure addition |
| 3 | Correct the documented `betas`/`convexp` schemas (R-4) | docstring | No |
| 4 | Widen A6 scan to `refraction/` (R-6) | `assert_panel.py` | No — strictly stricter |
| 5 | A9 single-name-basket guard (R-7) | `assert_panel.py` | No — correctness |
| 6 | Correct `refraction/CLAUDE.md`'s input list; add blank-`permno` refusal (R-2) | `CLAUDE.md`, new precondition | No |
| 7 | **`strict=True` fail-closed for A11/A14 (R-3)** | `assert_panel.py`, `main()`, tests | **Yes — changes gate semantics** |

Items 1–6 are safety-increasing or documentation-truth fixes and can be applied
without a decision. Item 7 makes the battery refuse to certify a panel it has not
fully checked; that is plainly the manual's intent, but it changes what
`overall_pass` means and should be recorded in `ops/decisions.md` rather than
slipped in.

**None of this blocks anything today** — R2 is not implemented and R6+ is
guard-blocked. That is exactly why it is the right moment: every one of these
defects gets more expensive once an R2 implementation is written against the
current behaviour.
