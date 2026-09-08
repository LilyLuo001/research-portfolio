# I09 source evidence: CPS identifiers and released design variables

Verified: 2026-09-08, before Gate 3 inference interpretation.

## Authorized extracts

The SCC header audit read the two authorized compressed extracts and verified
their complete file hashes before interpreting the fields. Both contain
`YEAR`, `MONTH`, `SERIAL`, `PERNUM`, `CPSID`, `CPSIDP`, `CPSIDV`, `MISH`,
`WTFINL`, and `HWTFINL`. Neither contains a public PSU/stratum field or a
`REPWT*` field. The audit publishes headers and hashes only; it publishes no
identifier value, microdata row, cell stock, or private path.

## Official IPUMS-CPS definitions

The following primary documentation was opened directly:

- [CPSID](https://cps.ipums.org/cps-action/variables/CPSID): IPUMS's
  longitudinal household identifier across samples, following the CPS 4-8-4
  rotation and appearing at most eight times for a household.
- [CPSIDP](https://cps.ipums.org/cps-action/variables/CPSIDP): IPUMS's
  longitudinal person identifier based on the household and roster line.
- [CPSIDV](https://cps.ipums.org/cps-action/variables/CPSIDV): the
  demographic-validated longitudinal person identifier.
- [SERIAL](https://cps.ipums.org/cps-action/variables/SERIAL): unique for a
  household only within a survey year and month; it is not the longitudinal
  household unit.
- [MISH](https://cps.ipums.org/cps-action/variables/MISH): month-in-sample in
  the 4-8-4 rotation. Its eight categories are rotation positions, not eight
  independent primary sampling units.
- [WTFINL](https://cps.ipums.org/cps-action/variables/WTFINL): the final Basic
  Monthly person weight used in the stock construction.
- [IPUMS-CPS replicate-weight documentation](https://cps.ipums.org/cps/repwt.shtml):
  the released replicate weights documented by IPUMS apply to the 2005-onward
  Annual Social and Economic Supplement. They are not imported into this Basic
  Monthly exercise.

## Binding inference interpretation

The feasible household sensitivity therefore uses positive `CPSID` as a
linked multiplier unit and assigns the same multiplier to every observed month,
co-resident record, and fractional routing descendant of that household. It is
not labeled CPS design-based inference. `SERIAL` is not substituted for
`CPSID`; `MISH` is not treated as a PSU; and ASEC replicate weights are not
borrowed. This released-weight sensitivity remains separate from the
occupation- and family-shock procedures rather than being mechanically added
to either variance.
