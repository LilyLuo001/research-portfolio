# Y2 — Verify the position in the literature

*Prepend `Y0_CONTEXT_PACK.md`. Requires Y1 gradient PASS. One task.*

## Why this is a gate and not an afterthought

`RESEARCH_PLAN_v1.md` §8 lists four claims about prior work. **None has been
verified from this repository.** They were relayed second-hand, and this project
has already shipped one confidently-worded false claim that survived two agents
before review caught it.

If the pre-registered powered test already exists in public, the contribution is
gone (kill condition §12.2) and the remaining work is a replication note. It is
much cheaper to learn that now than after the freeze.

## The four claims

| claim | what to establish |
|---|---|
| Eckhardt & Goldschlag (EIG), *AI and Jobs: The Final Word (Until the Next One)* (2025) chose AIOE for crosswalk accuracy, compared two crosswalk approaches, published data on GitHub | Does the paper exist? Did they compare crosswalk approaches for **measure construction** only, or did they test whether the choice moves a **coefficient**? Get the repo, the commit, the file. |
| EIG report findings "similar across all available measures" | Confirm the wording and the measures covered. |
| Budget Lab (Yale) SDID analysis finds nulls | Confirm it exists, its data, its specification, and whether it states an MDE. |
| Brynjolfsson, Chandar & Chen (Aug 2026 version) added interest-rate controls (Zens et al.) and telework robustness | Confirm the version, the date, and whether telework enters. |

## The question that actually decides the chapter

**Has anyone run a pre-registered, power-stated test of the young-worker AI
employment claim on public data?** Not "has anyone asked the question" — many
have. Specifically: specification fixed before outcomes were visible, with a
stated minimum detectable effect.

Search deliberately for a negative: pre-analysis plan registries (AEA RCT
Registry, OSF), working papers stating an MDE, replication-and-preregistration
notes. Absence of evidence found in one hour is not evidence of absence, so say
which sources you checked.

## Definition of done

- Each of the four claims resolved: **confirmed / refuted / not found**, with a
  URL, author, date, and version for each.
- The decisive question answered, with the sources searched listed explicitly.
- `RESEARCH_PLAN_v1.md` §8 rewritten from a table of claims-to-verify into a
  table of findings, and the heading's `VERIFY BEFORE THE FREEZE` marker
  replaced. `gates.py` novelty gate stays BLOCKED until it is.
- If §12.2 is triggered, **stop and emit `NEED_HUMAN`.** Do not quietly
  re-frame the chapter to dodge the finding.

## Do not

- Do not accept a claim because it is plausible or because another agent said
  it. This gate exists precisely because that failed before.
- Do not open any post-period file.
