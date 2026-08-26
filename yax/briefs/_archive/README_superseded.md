# Chapter execution briefs

Read `../CHAPTER_SCOPE_v1.md` first. Then run C1 → C4 in order, one task per
session, prepending `C0_CONTEXT_PACK.md` to every prompt.

| brief | task | blocks on |
|---|---|---|
| `C0_CONTEXT_PACK.md` | header, not a task | — |
| `C1_crosswalk_repair.md` | reconcile vs EIG, then crosswalk; audit item 2 | EIG GitHub first; BLS crosswalk + OEWS 2019/recent only if needed |
| `C2_merge_and_freeze.md` | merge to CPS, MDE, design freeze | C1; **wide IPUMS extract** |
| `C3_estimation.md` | run the six frozen tables once | C2 |
| `C4_manuscript.md` | manuscript, appendix, replication | C3 |

## Owner actions, not agent actions

1. **Submit the wide IPUMS extract** —
   `dax/memo/power_calcs/ipums_ai_telework_extract_v1.json`, 2017-01 →,
   ages 16–75. C2 blocks on it and it has queue time. Do this first.
2. **Check EIG's GitHub before downloading anything from BLS.** If their
   crosswalked AIOE resolves the group-15 occupations, C1 collapses to a
   comparison and you have saved a week. See C1 Step 0.
3. **Run the power calculation this week.** It is the only genuinely unknown
   input, it is now cheap (C2), and the §3 framing depends on the answer.
   Do it before committing to a framing.
4. **Download the BLS SOC 2010→2018 crosswalk and OEWS 2019 + recent year** —
   only if step 2 does not resolve it.
5. **Rotate the exposed credentials.** No longer on the critical path — the
   chapter needs no vendor API keys — but still owed.
6. **Create the `v1.0-preregistered` tag** after C2's design freeze, before
   C3's outcomes may be committed.
