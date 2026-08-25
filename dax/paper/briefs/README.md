# Chapter execution briefs

Read `../CHAPTER_SCOPE_v1.md` first. Then run C1 → C4 in order, one task per
session, prepending `C0_CONTEXT_PACK.md` to every prompt.

| brief | task | blocks on |
|---|---|---|
| `C0_CONTEXT_PACK.md` | header, not a task | — |
| `C1_crosswalk_repair.md` | SOC 2010→2018 repair; audit item 2 | BLS crosswalk + OEWS 2019/recent |
| `C2_merge_and_freeze.md` | merge to CPS, MDE, design freeze | C1; **wide IPUMS extract** |
| `C3_estimation.md` | run the six frozen tables once | C2 |
| `C4_manuscript.md` | manuscript, appendix, replication | C3 |

## Owner actions, not agent actions

1. **Submit the wide IPUMS extract** —
   `dax/memo/power_calcs/ipums_ai_telework_extract_v1.json`, 2017-01 →,
   ages 16–75. C2 blocks on it and it has queue time. Do this first.
2. **Download the BLS SOC 2010→2018 crosswalk and OEWS 2019 + recent year.**
   C1 blocks on these.
3. **Rotate the exposed credentials.** No longer on the critical path — the
   chapter needs no vendor API keys — but still owed.
4. **Create the `v1.0-preregistered` tag** after C2's design freeze, before
   C3's outcomes may be committed.
