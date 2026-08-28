# Y1c — Power for the joint model

*Prepend `Y0_CONTEXT_PACK.md`. Requires Y1b. Blocks the freeze.*

## Why

**The 3.44% MDE does not apply.** It was simulated for an unconditional AI
contrast on 490 clusters and 66 pre-period months. Adding a collinear
computerization regressor changes the sampling distribution of β_AI. Plan v3
carried the unconditional figure into a conditional design and quoted an
estimated conditional MDE; both were wrong and v4 removes them.

**Until this task completes, this design has no MDE and none may be quoted** —
not in the plan, not in a table, not in conversation.

## What to simulate

The exact estimating equation from plan v4 §5:

    E[N_oat] = exp[ α_oa + δ_ot + λ_at
                    + β_AI (AI_o × Young_a × Post_t)
                    + β_C  (Comp_o × Young_a × Post_t) ]

- Use the **observed joint distribution** of AI and computerization from Y1b,
  preserving their correlation. Do not simulate from independent marginals.
- Inject an AI-specific effect while **holding β_C fixed** at a plausible
  non-zero value; report sensitivity to that value.
- 999 repetitions, exact seed recorded.
- Grid wide enough that power crosses 80% **inside** it. The unconditional run
  needed extending twice; expect the conditional MDE to be larger.

## Report

- conditional MDE80 for β_AI, with its bootstrap interval;
- realised type-I error at nominal 5% — the unconditional engine rejected at
  6.8068% and covered at 93.1932%, so expect over-rejection and correct for it;
- effective number of occupations identifying β_AI;
- influence concentration across occupations;
- the same for α as the direct-LLM contrast.

**Wild-cluster bootstrap is primary inference**, Rademacher weights, clustered
on occupation, ≥999 draws.

## The gradient check still applies

`yax/gates.py` FAILs if power sits at ceiling at the smallest tested effect —
that is an engine describing its own smoothness, not a strong design. It also
FAILs if power never reaches 80%, which is the opposite diagnosis: the joint
design is underpowered and plan §12.4 triggers.

## Definition of done

- Conditional power aggregate JSON + lineage + receipt, with a `bootstrap` key.
- `python yax/gates.py --power-aggregate <path>` shows `gradient` and
  `calibration` PASS.
- `POWER_NOTE.md` updated: the conditional MDE, its interval, the assumed β_C,
  the DGP's assumptions, and what a simulation on a fitted model cannot capture.
- `pytest -q` green.

## Do not

- Do not open a post-period file.
- Do not quote the unconditional 3.44% anywhere.
- Do not write "100% power".
