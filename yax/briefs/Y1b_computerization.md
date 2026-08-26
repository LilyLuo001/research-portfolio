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
merged as things stand. Two routes, and §6.1 says the choice is made before the
freeze:

- **Amend the IPUMS extract** to add `OCC1990` and re-derive. Cleanest, and
  outcome-blind today. Requires the owner to submit; it has queue time.
- **Bridge `OCC2010` → `occ1990dd`** with a documented, cited crosswalk.
  Report coverage and name the occupations lost.

`NEED_HUMAN` on which route, with the coverage cost of the bridge if you can
estimate it. Do not pick silently — one of them changes the extract.

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
