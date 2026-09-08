# I09 findings: sampling identifiers and design variables

Status: **VERIFIED**

SCC job `7490381` completed with scheduler `failed=0` and `exit_status=0`.
It authenticated both authorized extract hashes and passed the header audit.

The available fields support a repeated-household released-weight sensitivity:
`CPSID` supplies the linked household multiplier unit, `CPSIDP`/`CPSIDV`
permit person-link diagnostics, `MISH` records rotation position, and `WTFINL`
is the Basic Monthly person weight. The authorized extracts do not contain
public PSU/stratum variables or replicate weights.

Consequently, the household refit will preserve dependence observed within
linked households, including co-residents and repeated months, but it will not
be presented as CPS design-based inference. The code must not treat the eight
`MISH` categories as independent PSUs and must not borrow ASEC replicate
weights. Household sensitivity and occupation/family shock inference answer
different stochastic questions and will not be added without a derived
decomposition.

Evidence:

- `evidence/I09_DESIGN_VARIABLE_AUDIT.json`
- `I09_SOURCE_EVIDENCE.md`
