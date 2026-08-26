# Y3 — Push, freeze, tag

*Prepend `Y0_CONTEXT_PACK.md`. Requires Y1 and Y2 both PASS. One task.*

This is the step that creates the chapter's contribution. Everything before it
is preparation; everything after it is estimation. It is also the step that
cannot be redone.

## Preconditions — verify with the gate runner, not by memory

    python yax/gates.py --power-aggregate <aggregate>.json

`gradient`, `calibration`, `coverage_rule` and `novelty` must all read `PASS`.
If any reads `BLOCKED`, it was not checked, which is not the same as passing.
**Stop.**

## 1. Push everything to `origin` first

The SCC work currently exists only on two cluster working copies
(`dax_design_power_20260825`, `dax-cps-sparse-20260825`) with commits
cherry-picked between them and no remote. Code, receipts, lineage sidecars and
audit CSVs are **not** licensed data and belong on `origin`. Only the CPS
panels themselves stay private.

Before pushing, confirm no microdata is staged:

    git status --short          # named paths only, never `git add -A`
    git diff --cached --stat

A freeze tag on a commit that exists on one cluster filesystem is not a freeze.

## 2. Write `yax/DESIGN_FREEZE_v1.md`

It must contain:

- The estimating equation **exactly as it will be run**, with the clustering and
  the bootstrap procedure named.
- The three coverage rules by reference to `COVERAGE_RULE_PRESPEC_v1.md`, with
  Rule B named primary.
- The MDE80 and its bootstrap interval from Y1.
- **The sha256 of the analysis panel.** `gates.py` requires a 64-hex string:
  a freeze that does not pin the data it froze is not a freeze.
- Empty table shells for Tables 1–6, with column headers and row labels filled
  in and every cell blank.
- The date, and the commit hash this freeze is made against.

## 3. Commit, then tag

    git add yax/DESIGN_FREEZE_v1.md
    git commit -m "YAX: design freeze"
    git tag -a v1.0-preregistered -m "YAX pre-registration: specification, coverage rule and MDE fixed before any post-period outcome"
    git push origin --tags

## 4. Verify the ordering held

    python yax/gates.py --power-aggregate <aggregate>.json

`prespec_before_tag` must now read `PASS` — it checks in git history that
`COVERAGE_RULE_PRESPEC_v1.md` is an ancestor of the tag. `freeze_doc` and
`seal` must also pass. **All seven gates green is the definition of done.**

If `prespec_before_tag` FAILs, the pre-specification is void by its own terms.
Do not delete and re-tag to make the check pass — that is falsifying the record.
Report it, and the paper reports the coverage rule as a post-hoc choice.

## Definition of done

- Everything pushed to `origin`, no microdata staged.
- `DESIGN_FREEZE_v1.md` committed with a panel sha256 and empty shells.
- `v1.0-preregistered` tagged and pushed.
- All seven gates `PASS`.

## Do not

- Do not open a post-period file. Not even now. Y4 does that.
- Do not re-tag to fix a failed ordering check.
