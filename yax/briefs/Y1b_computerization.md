# Y1b — Vendor the real computerization measures

*Prepend `Y0_CONTEXT_PACK.md`. Blocks the freeze. One task, one session.*

Read `../RESEARCH_PLAN_v4.md` §2, §3 and §6 first. §6 fixes the choices; you
implement them, you do not re-decide them.

## Why this blocks

Everything the project currently knows about AI-vs-computerization separability
comes from `measurement/computerization_support.py`, which uses Dingel–Neiman
**teleworkability as a stand-in**. Teleworkability is not computerization — an
occupation can be computer-intensive and not teleworkable, and the reverse. No
number from that script may be quoted. This task replaces the proxy.

A control added after outcomes are seen is specification search, so this must
land before the tag or it cannot be done cleanly at all.

## 1. Webb software exposure — expect a blocker

Webb (2020), `michaelwebb.co/webb_ai.pdf`, constructs **software, robot and AI**
exposure from a common task–patent framework. That much is verified from the
paper. **The data file is not.**

1. Locate the distributed file. Record URL, sha256, and its **native
   occupation taxonomy**.
2. It is commonly distributed on **`occ1990dd`**, and existing CPS
   implementations key it on IPUMS **`OCC90`** rather than treating it as
   another SOC-2010 measure — see `github.com/EIG-Research/AI-unemployment`.
   Confirm this against the actual file rather than assuming it.

**The blocker, already verified:** the wide extract carries `OCC2010` and **no
`OCC1990`** — 26 variables, one occupation code, checked against
`dax/memo/power_calcs/ipums_ai_telework_extract_v1.json`. So Webb cannot be
merged as things stand.

**RESOLVED by Y1a — do not re-litigate.** Use **Dorn's direct
`OCC2010 → occ1990dd` crosswalk** (`ddorn.net/data/occ2010_occ1990dd.zip`,
sha256 `454cf8d7…`). `OCC1990` is not needed; `occ1990dd` is Dorn's 341-category
scheme, not IPUMS `OCC1990`'s 389. Coverage on the outcome-blind pre-period
support is 445 codes observed, **0 unmapped**, 442 with a Webb score = 99.9515%
of employment weight. Webb file `exposure_by_occ1990dd_lswt2010.xls`, sha256
`c5652fd3…`, 341 rows; measure `pct_software`.

**One thing Y1a left open: name the three occupations Webb does not score**, and
report their combined employment weight. The receipt records the count, not the
identities. This project names occupations rather than reporting only shares.

*Historical, retained so the reasoning is checkable:*

1. **Does IPUMS CPS offer `OCC1990` for 2017–2026 basic monthly samples?** One
   call to the variables metadata endpoint settles it. It needs the API key,
   which is being rotated. If `OCC1990` is available, the bridge route costs
   coverage for nothing and the fork is a formality.
2. **Is `OCC1990` sufficient for Webb?** `occ1990dd` is understood to be Dorn's
   time-consistent modification of `OCC1990`, not `OCC1990` itself. If that is
   right, adding the variable is necessary but not sufficient and Dorn's
   crosswalk is still required. **Verify against Webb's replication files** —
   do not take that sentence, or mine, on faith.

The extract **is** built — the SCC run reports 9,262,480 rows validated — so
amending means resubmitting, days of queue, not editing an unsubmitted spec.
Outcome-blind today; impossible after the tag.

`NEED_HUMAN` on the route once (1) and (2) are answered, with the coverage cost
of the bridge if you can estimate it. Do not pick silently — one route changes
the extract.

Take Webb's **software** measure as the computerization primary. His AI measure
is *not* the computerization control and must not be used as one.

## 2. O\*NET *Working with Computers* — already frozen, just build it

| choice | value |
|---|---|
| release | **O\*NET 24.3, May 2020** — last before the O\*NET-SOC 2019 transition |
| descriptor | **`4.A.3.b.1`** |
| scale | **Importance primary**, Level as robustness |

`onetcenter.org/db_releases.html`. Record release and sha256. **Do not use
current O\*NET** — those ratings post-date LLM diffusion and are not a measure
of *prior* computerization. 24.3 is on the O\*NET-SOC 2010 taxonomy, so the
project's existing vintage repair applies.

## 3. RTI and Frey–Osborne

Routine-task intensity by the Autor–Levy–Murnane / Acemoglu–Autor recipe.
Frey–Osborne **secondary only** — it bundles AI and robotics into automation
risk rather than measuring prior computerization, so it partly contains the
treatment.

## 4. Re-run the diagnostics on the real measures

Re-run `measurement/computerization_support.py` against each. The script's
`proxy_warning` field must be removed **only** when the receipt genuinely
reflects a real computerization measure — `gates.py::gate_computerization`
blocks on that field, and clearing it while still on the proxy would be
falsifying a gate.

Report for each AI × computerization pair, per plan §3:

- employment-weighted correlation; partial variance of AI; VIF and SE inflation;
- effective number of occupations identifying β_AI;
- share of residual variation by major occupational family;
- named divergence occupations;
- common-support employment coverage.

**Report the result whatever it is.** If conditional support is weak, the
chapter's conclusion becomes that occupation-level public data cannot separately
attribute the pattern — smaller, and still a chapter.

## Definition of done

- Webb vendored with URL, sha256, native taxonomy; merge route decided by the
  owner and implemented; coverage reported.
- O\*NET 24.3 `4.A.3.b.1` Importance and Level, crosswalked, receipted.
- RTI and Frey–Osborne built.
- Diagnostics re-run; `proxy_warning` removed only if genuinely resolved.
- `python yax/gates.py` shows `computerization` no longer BLOCKED.
- `pytest -q` green.

## Do not

- Do not open a post-period file.
- Do not use Webb's **AI** measure or AIOE as the computerization control.
- Do not use current O\*NET ratings.
- Do not drop a measure because it absorbs the AI coefficient. That is the result.
