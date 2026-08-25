# Correction — the 96.7% is a merge failure, not a coverage gap

**Date:** 2026-08-25. **Raised by:** external review. **Verified:** yes, in repo.

## The error

`CHAPTER_SCOPE_v1.md` and `briefs/C1_crosswalk_repair.md` claimed that Software
Developers, Computer Systems Analysts, Computer User Support Specialists and
Project Management Specialists "have no AIOE value at all", and that AIOE
"structurally omits the occupations where the finding is claimed to occur".

**That is false.** Verified against the vendored file:

| occupation | AIOE code | AIOE value | Dingel–Neiman |
|---|---|---:|---:|
| Software Developers, Applications | 15-1132 | +1.2009 | 1.0 |
| Software Developers, Systems Software | 15-1133 | +1.2833 | 1.0 |
| Computer Systems Analysts | 15-1121 | +1.1982 | 1.0 |
| Computer User Support Specialists | 15-1151 | +0.2993 | 1.0 |

AIOE carries **18 occupations** in SOC major group 15, covering the SOC 2010
taxonomy in full. SOC 2018 renumbered the group — Software Developers became
15-1252, Computer Systems Analysts 15-1211, Computer User Support Specialists
15-1232 — so an **exact-code merge** onto OEWS 2021 finds none of them. Project
Management Specialists (13-1082) is genuinely new in SOC 2018, carved out of
13-1199; a crosswalk carries the parent value down rather than finding nothing.

The 96.7% figure is correct. It measures what an exact-code merge does. The
gloss placed on it was wrong.

## What was and was not affected

**The code was right.** `audit_common_support.py` diagnosed the cause
correctly; the receipt's `soc_vintage_reading` field states that AIOE and
Dingel–Neiman are SOC 2010 while OEWS 2021 is SOC 2018, and instructs the
reader to check the counts rather than take the sentence on faith. Every
number in `AUDIT_RESULTS.md` stands. Only the prose gloss was wrong, in three
places, now fixed, plus one generated heading in the script.

## Why it mattered

The false claim was load-bearing. It justified promoting the crosswalk repair
from appendix to main text on the grounds that an unrepaired measure omits the
treatment group. With the claim removed, that justification collapses — the
repair as stated is debugging, not a contribution.

The chapter survives at a different altitude, and a narrower one: **does the
crosswalk vintage decision change the estimated young-worker gradient?** Every
paper in this literature makes that decision; none reports it. That is a
legitimate methods contribution and it is what `CHAPTER_SCOPE_v1.md` §1 now
asks.

## The pattern, recorded

This is the third instance in one session of the same failure: correct
arithmetic, overstated verbal gloss. The earlier two were "no specification
rescues AIOE" (false — R² 0.58 implies VIF 2.38, which is workable) and
describing the measure-role decision as "prospective" (it was fixed after
treatment overlap was examined). All three were caught by review, not by
self-check.

Standing rule for this chapter, in addition to the §6 anti-specification-search
rules: **a sentence describing a computed number must be checkable against the
same artifact that produced the number.** "Occupations unmatched by an
exact-code merge" is checkable. "Occupations the measure omits" is a different
claim requiring a different check, and it was never run.
