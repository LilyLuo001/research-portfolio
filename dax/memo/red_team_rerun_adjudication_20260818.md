# Fresh cross-vendor red-team adjudication — 2026-08-18

## Gate status

**BLOCK.** All three fresh DeepSeek V4-Pro reruns returned `REVISE/BLOCK`.
The older conditional-go narrative reviewed a superseded design and does not
clear this gate. The outcome seal remains closed.

| Consolidated finding | Decision | Enforced action | Current status |
|---|---|---|---|
| M1: dynamic dose may be absorbed by the full nuisance design | Accept | Require a pre-outcome identification receipt computed on the real W5 occupation-month dose panel after residualizing on occupation, month, industry-by-month, and frozen static-decile-by-month effects. Dynamic claims require effective rank at least 2 and leading singular share at most 0.95. | Pending W5 dose panel; Gate 1 blocked |
| M2: `pi_go` is sparse and the complement rule mixes entrants, linkage failures, and long non-employment | Accept | Demote the entrant companion to exploratory. Audit adjacent-month CPSIDP transitions in MISH 2–4 and 6–8; do not restore the registered companion without a PI-approved cell definition, pooling threshold, and sampling-error propagation rule. | Audit implemented; private run required |
| M3: the executable 0.19 power benchmark has no dated page/section locator | Accept | Remove 0.19 from the executable standard, set the benchmark to unresolved, and make the freezer require `locator_status=VERIFIED`. A PI preference is not evidence. | Fixed; Gate 1 blocked pending locator or signed reversion to sourced 0.13 |
| M4/M5: occupation-month simulated power is not proven to upper-bound the person-month estimator | Accept | Keep adequacy null until the real person-level pre-outcome power run uses the frozen CPS extract and real W5 doses. The cell simulation remains diagnostic only. | Pending W5 dose panel; Gate 1 blocked |

## Price/evidence finding resolved in parallel

The W2 price panel now has 65 verified rows and zero single-channel or conflict
rows. Three mechanical failures were corrected without weakening the rule:

- GPT-4 uses a dated official launch page plus the independent git channel.
- GPT-4.5 official pricing cards use the family label `GPT-4.5`; the parser now
  checks that alias even when the exact preview ID occurs elsewhere in page
  metadata.
- Git history now uses committer dates. Cherry-picked LiteLLM commits retained
  author dates before the GPT-5.4 and GPT-5.5 launches, which were not valid
  observation dates.

Price verification does not resolve event-date evidence. Rows still lacking a
second dated event locator remain ineligible even when their price rows pass.

## Non-negotiable implementation rules

1. `mapped`, `priced`, `source-verified`, `identified`, and `adequately powered`
   are separate statuses; none implies another.
2. No outcome regression may run before the identification and power receipts
   pass on sealed/pre-outcome inputs.
3. The entrant companion cannot appear in the Gate-1 power table while its
   status is exploratory.
4. No benchmark number may remain executable while its dated locator is
   pending.
5. A new independent red-team run is required after these changes; this
   adjudication does not self-certify the revised design.
