# Amendment 2: canonical rebuilt treatment contract

Status: **post-outcome exploratory; audit correction written before the rebuilt-treatment rerun.**

An internal consistency audit found that the expanded characteristic module rebuilt the corrected CPS outcome calendar but retained the historical production beta-quintile assignments and Webb normalization. That historical treatment was constructed with full-static-panel weights, including postperiod stock. The active paper instead describes the fully rebuilt corrected-preperiod treatment as its canonical treatment contract.

This amendment makes one mechanical correction. Every model in the registered characteristic grid will read beta-quintile membership, Webb normalization, support, and construction weights from the authenticated `REBUILT_TREATMENT_MEMBERSHIP.csv` artifact. That artifact was constructed from corrected January 2017--November 2022 stock only, contains 468 occupations, and has support hash `11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b`. The module must authenticate both the membership and normalization artifacts before fitting any model.

Nothing else changes. The corrected 113-month outcome calendar, occupation support, one-at-a-time controls, support-specific baseline/augmented pairs, literal all-characteristic common-support cumulative sequence, SOC2 specifications, standardization of characteristics with 2017--2019 stock, 9,999 occupation-level Rademacher draws, fixed seeds, and common multipliers within every paired comparison are retained. The original and Amendment 1 artifacts remain in Git as an audit trail.

The rerun remains post-outcome exploratory. The correction was triggered by a treatment-contract inconsistency, not by the sign, size, or significance of any characteristic result. Its output cannot be presented as preregistered, causal, or economically equivalent when a paired interval includes zero.
