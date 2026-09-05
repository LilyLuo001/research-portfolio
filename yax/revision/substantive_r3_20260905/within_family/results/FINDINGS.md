# Within-family findings

**Status:** POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

The corrected-calendar Q5--Q1 coefficient is `-0.134554`.  Adding SOC2-by-post terms yields `-0.031474`, and absorbing SOC2-by-month paths yields `-0.031737`.  These are sensitivity comparisons under changed conditioning restrictions, not causal allocations between AI and composition.

The direct-tail benchmark changes the population to Q1/Q5 occupations in the four families `27, 29, 31, 41`.  It retains 5.09% of full-support preperiod stock; its SOC2-by-month coefficient is `0.136116`.  It should not be compared mechanically with the full-support coefficient as if only a control changed.

The continuous companion uses one employment-weighted within-family beta standard deviation (`0.108385` raw beta units) and imposes a common slope across families.  Its SOC2-by-month slope is `-0.002465`.

Leave-one-family-out ranges are `-0.068191` to `0.003520` for the conditional Q5 coefficient and `-0.007781` to `0.001417` for the continuous slope.  No omitted family is promoted as a preferred specification.

Trajectory families were chosen solely by direct-tail nuisance-adjusted information: 31 (Healthcare Support); 27 (Arts, Design, Entertainment, Sports, and Media); 29 (Healthcare Practitioners and Technical); 41 (Sales and Related).  The output reports young and older stocks separately for both tails.  No sampling interval is fabricated from aggregate final weights.

Information is computed exactly as `I=sum h*r^2` after weighted fixed-effect absorption and projection on every other slope regressor.  Effective occupation counts and top-five shares describe fitted information concentration; they do not replace the nominal cluster count or validate a reference distribution.

Model failures recorded: `0`.
