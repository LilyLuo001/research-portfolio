# YAX execution briefs

Read `../RESEARCH_PLAN_v2.md` first. Then run Y1 → Y5 in order, one task per
session, prepending `Y0_CONTEXT_PACK.md` to every prompt. Run `YV_VERIFY.md`
after each one, in a fresh session and preferably a different model family.

| brief | task | gate it must clear |
|---|---|---|
| `Y0_CONTEXT_PACK.md` | header, not a task | — |
| `Y1_power_gradient.md` | fine grid, gradient check, bootstrap MDE | `gradient`, `calibration` |
| `Y1b_computerization.md` | separate AI exposure from computerization | `computerization` |
| `Y2_novelty_gate.md` | verify the four §8 claims | `novelty` |
| `Y3_freeze.md` | push to origin, freeze doc, tag | `prespec_before_tag`, `freeze_doc`, `seal` |
| `Y4_estimation.md` | run the six frozen tables once | all seven PASS first |
| `Y5_manuscript.md` | manuscript, appendix, replication | — |
| `YV_VERIFY.md` | independent verification | run after each |

## The gate runner is the authority

    python yax/gates.py --power-aggregate <aggregate>.json

Seven gates, each `PASS` / `FAIL` / `BLOCKED`. Exit status is non-zero unless
every gate passes, so **`BLOCKED` cannot be mistaken for fine.** No brief's
claim of completion overrides it.

Current state, checked in this repository:

| gate | status |
|---|---|
| `coverage_rule` | PASS |
| `seal` | PASS |
| `gradient` | **PASS** — MDE80 = 3.44%, curve internally consistent |
| `calibration` | **FAIL** — 6.8% null size, no bootstrap field |
| `novelty` | BLOCKED — partial; locators + registry search outstanding |
| `computerization` | BLOCKED — support check still on the teleworkability proxy |
| `prespec_before_tag` | BLOCKED — no tag |
| `freeze_doc` | BLOCKED — not written |

## Owner actions, not agent actions

1. **Push the SCC work to `origin`.** It exists on two cluster working copies
   with no remote. Code and receipts are not licensed data; only the panels are.
2. **Rotate the IPUMS API key.**
3. **Create the tag** at Y3, after the gates are green.
