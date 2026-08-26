# SOC-vintage and EIG crosswalk gate

**Status:** measurement gate complete; no CPS outcomes opened.

The 96.7% computer-and-mathematical employment loss in the original audit was
an exact-code merge failure, not structural omission by AIOE. The official BLS
bridge maps the headline missing occupations directly: for example, 2010 SOC
15-1132 and 15-1133 combine into 2018 SOC 15-1252 (Software Developers).

## Binding correction to C1

The frozen C1 brief says to weight many-to-one 2010 parents with OEWS 2021
employment. That is not defined. OEWS 2021 is already on the target 2018 SOC
taxonomy; after 15-1132 and 15-1133 become 15-1252, its one employment total
cannot recover the two source shares.

The defensible source-employment variant therefore uses May 2018 OEWS. BLS's
May 2018 technical notes state that the release classifies its detailed
occupations using the 2010 SOC system. Target-vintage OEWS remains appropriate
for measuring coverage after the mapping, but not for weighting source parents.

## Four constructions kept separate

1. `AIOE_admin`: EIG's official administrative bridge, taking an equal mean
   when multiple source occupations enter one target Census occupation.
2. `AIOE_sim`: EIG's O*NET ability-overlap bridge. It is a diagnostic, not the
   measure used for EIG's main Felten results.
3. `AIOE_wgt`: EIG's direct reconstruction from ability-level AIOE and O*NET
   25.1 target-occupation ability weights. This is EIG's main Felten measure.
4. `AIOE_oews2018_source_weighted`: the new administrative bridge, weighting
   2010 source occupations by May 2018 OEWS employment.

The Python reproduction matches EIG's published Figure 9: on EIG's Census-2018
support, the direct ability reconstruction correlates about 0.98 with the
equal-mean official bridge, while the O*NET bridge correlates about 0.50 with
the direct reconstruction and 0.51 with the official bridge.

## Results

On the 519 Census occupations common to all four constructions:

- equal administrative versus source-employment-weighted: Pearson 0.996;
- direct ability reconstruction versus equal administrative: Pearson 0.983;
- direct ability reconstruction versus source-employment-weighted: Pearson
  0.979.

On 767 SOC-2018 occupations common to the two administrative variants, their
OEWS-2021 employment-weighted Pearson correlation is 0.99975. The
employment-weighted mean absolute native-scale difference is 0.00256, although
the maximum difference is 0.515; coefficient sensitivity must therefore be
tested rather than inferred from the high correlation.

Coverage against national OEWS detailed occupations is:

| target year | equal-admin employment | source-weighted employment |
|---|---:|---:|
| 2021 | 92.90% | 92.39% |
| 2025 | 92.50% | 91.96% |

Within SOC major group 15, the exact-code baseline covers 4 of 21 occupations
and 3.33% of employment. The equal-admin repair covers 20 occupations and
97.72% of employment; the source-weighted repair covers 19 and 97.64%.

## Reproducibility and remaining boundary

`CROSSWALK_GATE_RESULTS.json` records every source locator, file date where
available, SHA-256, mapping count, coverage result, flagship occupation source
rows, and common-support correlation. Raw public inputs live outside Git under
`/projectnb/econdept/qluo/dax-private/public_raw/`.

This gate does not choose a preferred exposure measure and does not estimate an
employment coefficient. The next design-freeze task must keep the equal-admin,
direct-ability, and source-employment variants separately named. It must also
specify the Census-2010 to Census-2018 bridge for 2017--2019 CPS observations;
that person-level bridge is outside this measurement-only gate.
