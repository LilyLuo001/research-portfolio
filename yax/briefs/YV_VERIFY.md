# YV — Independent verification

*Prepend `Y0_CONTEXT_PACK.md`. Run after each of Y1–Y5, in a FRESH session,
ideally on a different model family than the one that did the work.*

## Your role

You did not do this work and you are not here to help finish it. You are here
to find out whether a claimed milestone is actually met. **A milestone reported
as complete by the agent that completed it has been checked once, by an
interested party.**

This project has a documented failure mode: correct arithmetic carrying an
overstated verbal gloss. It happened three times — "no specification rescues
AIOE", "prospective" measure selection, and "AIOE omits Software Developers" —
and external review caught all three. Self-check caught none. You are the
replacement for that external review.

Your default posture is disbelief. Your output is a verdict, not a summary.

## Start here, always

    python yax/gates.py --power-aggregate <aggregate>.json --json

This is the authority. **`BLOCKED` is not `PASS`.** If the previous agent
reported a milestone complete and the gate reads `BLOCKED`, the milestone is
not complete and your verdict is `REJECTED`, whatever the agent's summary said.

## Per-milestone checks

### After Y1 (power)

1. Re-run the gate yourself. Do not read the previous agent's transcript for
   the numbers — open the aggregate JSON.
2. Recompute the MDE80 by hand from the `results` array. Does it match
   `POWER_NOTE.md`?
3. **The adversarial question: is the gradient real, or did the grid simply get
   extended until something crossed 80%?** Check the shape. A plausible power
   curve rises smoothly. A curve that is flat at 0.99 and then drops to 0.4 at
   one point is a bug or a seed artifact, not a gradient.
4. Does the bootstrap MDE differ materially from the normal-theory MDE? If they
   are identical to three decimals, the bootstrap probably did not run.
5. Grep the repository for `100% power`, `perfect power`, `fully powered`. Any
   hit is a `REJECTED`.

### After Y2 (novelty)

1. Every claim in §8 must carry a URL, author, date and version. A claim marked
   confirmed without a locator is not confirmed — it is the exact failure this
   project has already made three times.
2. Open at least two of the cited sources yourself and confirm they say what
   the table says they say.
3. Was the decisive question — *has anyone run a pre-registered, power-stated
   test of this claim on public data?* — actually searched, or answered by
   assertion? Check that the sources searched are listed.
4. If §12.2 is triggered and the plan was quietly re-framed instead of stopping,
   that is `REJECTED` and say so plainly.

### After Y3 (freeze) — the one that matters most

1. `prespec_before_tag` must read `PASS`. Verify independently:

       git log --reverse --format='%H %ci' -- yax/COVERAGE_RULE_PRESPEC_v1.md | head -1
       git log -1 --format='%H %ci' v1.0-design-freeze
       git merge-base --is-ancestor <prespec-commit> <tag-commit> && echo ORDER-OK

2. Check the tag was not deleted and recreated:
   `git reflog show v1.0-design-freeze` and look for the commit date preceding
   the tag date in a way that suggests a retag.
3. `DESIGN_FREEZE_v1.md` must pin a real sha256. Verify it against the actual
   panel if you can reach it.
4. Are the table shells genuinely **empty**? A shell with numbers already in it
   means outcomes were opened before the freeze.
5. Confirm the freeze commit exists on `origin`, not only locally.

### After Y4 (estimation)

1. Does every table carry three coverage-rule columns and bootstrap p-values?
2. Does the reported specification match `DESIGN_FREEZE_v1.md` **exactly**?
   Diff them line by line. Any difference not in a deviation log is
   specification search.
3. Is there evidence of more runs than tables — extra output files, commented
   alternative specifications, a second seed? The first run is the reported run.
4. If the result is a null, does the text state the MDE and call it an
   informative null? A null reported without its MDE throws away the chapter's
   contribution.

### After Y5 (manuscript)

1. Pick five numbers from the text at random. Trace each to a receipt. Any that
   cannot be traced is `REJECTED`.
2. Check every claim about prior work against Y2's table.
3. Does the replication package build from a clean clone with no private path?
   Actually try it.
4. Read the abstract against `RESEARCH_PLAN_v1.md` §2. Does it claim more than
   the three things the plan says it contributes?

## Your output

    VERDICT: ACCEPTED | REJECTED | ACCEPTED WITH FINDINGS

    Gate output:      <paste the --json output>
    Checked:          <what you actually opened and recomputed>
    Findings:         <numbered, each with the artifact that contradicts the claim>
    Not checked:      <what you could not verify, and why>

Rules for the verdict:

- `REJECTED` if any gate is `FAIL`, if any milestone claim is contradicted by
  an artifact, or if a number in prose cannot be traced.
- `ACCEPTED WITH FINDINGS` if the milestone holds but something needs fixing.
- `ACCEPTED` only if you checked and everything held.
- **Never `ACCEPTED` for something you did not check.** List it under "Not
  checked" instead. An honest "I could not verify this" is worth more than a
  confident pass, and this project has the scar tissue to prove it.

## Do not

- Do not fix anything. Report; the next Y-task fixes.
- Do not open a post-period file before the tag exists, even to verify.
- Do not accept a claim because it is plausible or because the previous agent
  sounded certain. That is the failure mode you exist to catch.
