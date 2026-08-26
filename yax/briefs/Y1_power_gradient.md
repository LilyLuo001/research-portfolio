# Y1 — Locate the MDE, and find out whether the power engine is honest

*Prepend `Y0_CONTEXT_PACK.md`. One task, one session.*

## The situation

The first power run returned ≥98.6% power at every effect on its grid,
including a 4.88% relative decline, and 100% against the 19% benchmark. That
did not locate the MDE — it only established the MDE is below the grid floor.

**A simulation reporting ceiling power across an order of magnitude of effect
sizes may be describing its own smoothness rather than the design's strength.**
Simulated power on a fitted DGP cannot capture misspecification, unmodelled
shocks, or serial correlation the fit did not see. This task decides whether
the chapter's foundation is real.

## What to run

Extend the grid downward until power falls through 80%. Start at
1%, 1.5%, 2%, 2.5%, 3%, 3.5%, 4%, 4.5% relative decline; go below 1% if
needed. 999 repetitions, same seed discipline, same 490-cluster / 66-month
pre-period panel.

Then aggregate and check:

    python yax/gates.py --power-aggregate <aggregate>.json

## The two outcomes, and they are not close

**Power falls through 80% inside the grid** → the gate reports `PASS` with an
interpolated MDE80. The design is powered, the chapter's premise holds, and you
proceed to Y2.

**Power is still ≥95% at the smallest tested effect** → the gate reports `FAIL`
with "engine bug". **Do not freeze. Do not treat this as good news.** Diagnose:

- Does the DGP resample residuals, or draw from a fitted mean with variance the
  fit chose? The second understates real variation.
- Is serial correlation within occupation preserved? Employment series are
  persistent; an i.i.d. draw across months inflates effective sample size
  enormously.
- Are cluster-level shocks drawn at all, or only cell-level noise?
- Does the simulated null reject at 5%? It currently rejects at 6.6%, which is
  already evidence the error distribution is too tight.

Report what you find as a finding. An engine that overstates power is a bug
worth a paragraph in the appendix, not an embarrassment to bury.

## Bootstrap — required regardless of the gradient result

The engine rejects at 6.6% against a nominal 5% and covers at 93–94%.
Recompute the MDE under a **wild-cluster bootstrap** (Rademacher weights,
clustered on occupation, ≥999 draws). Write the bootstrap MDE and its interval
into the aggregate JSON under a key containing `bootstrap` — `gates.py` looks
for it, and the calibration gate FAILs without it.

## Definition of done

- Fine-grid aggregate JSON + lineage + receipt.
- `python yax/gates.py --power-aggregate <path>` reports `gradient: PASS` and
  `calibration: PASS`, **or** a written diagnosis of why it does not.
- Bootstrap MDE with interval, recorded in the aggregate.
- A short `POWER_NOTE.md` in `yax/`: the MDE80, its bootstrap interval, the
  DGP's assumptions, and what the simulation cannot capture. Three paragraphs.
- `pytest -q` green.

## Do not

- Do not write "100% power" anywhere.
- Do not open any post-period file. This task is pre-period only.
- Do not proceed to Y3 on a `FAIL` or `BLOCKED` gradient gate.
