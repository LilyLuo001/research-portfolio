# CPS bridge to the published BCC grouping

Status: post-outcome exploratory; not part of confirmatory YAX v1.1.

## Reproduced component

The public BCC specification uses the Eloundou GPT-4 beta score, forms employment-weighted exposure quintiles, and compares the top two quintiles with the bottom three. The source used to verify that rule is the Stanford Digital Economy Lab paper page and linked August 2026 paper:

- <https://digitaleconomy.stanford.edu/publication/canaries-in-the-coal-mine-six-facts-about-the-recent-employment-effects-of-artificial-intelligence/>
- <https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf>

The program in this directory implements that grouping inside the fixed YAX CPS employment-stock model. It does **not** reproduce BCC's proprietary ADP outcome, firm panel, job-title mapping, hiring and separation margins, or firm-time controls. All intervals below use 9,999 common occupation-level wild-score multipliers.

## Results

On the fixed 468-occupation YAX support, 155 occupations and 39.72 percent of frozen employment weight enter the top-two group. The post-January-2023 young-relative coefficient is:

| CPS specification | coefficient | SE | 95% wild-score interval | normal-theory MDE80 |
|---|---:|---:|---:|---:|
| BCC grouping, Webb software conditioned | -0.07277 | 0.02598 | [-0.12398, -0.02156] | 0.07278 |
| BCC grouping, no Webb software control | -0.07285 | 0.02610 | [-0.12364, -0.02206] | 0.07311 |

The observed top-group coefficient is therefore smaller in magnitude than YAX's Q5-versus-Q1 coefficient of -0.1311. This is expected because the published BCC comparison pools Q4 with Q5 and Q1--Q3 together; it is a different contrast, not a robustness estimate of the same parameter.

For a descriptive November 2022--June 2026 comparison, young CPS stock rises 5.78 percent in the bottom-three group and falls 5.03 percent in the top-two group. The top group's kept-pace shortfall is 10.22 percent. Older stock grows by about 0.6 percent in both groups. These aggregates do not inherit BCC's firm-panel or hiring interpretation.

## Architecture comparison under the same BCC grouping rule

Reapplying the top-two-versus-bottom-three rule to each architecture changes both the occupation classification and the coefficient. Native-support estimates are:

| architecture | occupations | coefficient | 95% interval |
|---|---:|---:|---:|
| AIOE administrative | 495 | -0.0532 | [-0.1104, 0.0039] |
| AIOE ability/direct | 484 | -0.0679 | [-0.1268, -0.0090] |
| AIOE OEWS-weighted | 485 | -0.0610 | [-0.1184, -0.0035] |
| Eloundou alpha | 468 | -0.0741 | [-0.1250, -0.0232] |
| Eloundou beta | 468 | -0.0728 | [-0.1240, -0.0216] |
| Eloundou broad/gamma | 468 | -0.0817 | [-0.1342, -0.0292] |
| Webb AI patent--task | 448 | -0.0168 | [-0.0710, 0.0374] |
| OECD capability gap | 448 | -0.0096 | [-0.0600, 0.0407] |

Native-support coefficients mix construction and support. On literal 426-occupation common support, beta is -0.0810. Common-draw paired intervals do not detect beta differences from the three AIOE implementations, alpha, gamma, or Webb AI. The beta-minus-OECD difference is -0.0733 with paired interval [-0.1390, -0.0076] and paired 80-percent MDE 0.0956. This grouping-specific result should not be conflated with the Q5--Q1 paired architecture exercise, where every paired interval includes zero. It shows that the ability to distinguish architectures itself depends on the economic contrast.

## Interpretation for the revision

This check strengthens the bridge to the motivating paper while narrowing the claim. Public CPS reproduces a negative young-relative association under BCC's published exposure grouping, at -0.0728 rather than the YAX Q5--Q1 estimate of -0.1346. It cannot adjudicate the proprietary data construction or hiring mechanism. The near identity of conditioned and unconditioned estimates in this particular binary grouping does not establish that computerization is generally irrelevant. Nor do the common-support comparisons establish a universal ordering: only the beta--OECD difference is detected under this particular grouping, and the paired design is too imprecise to resolve most architecture differences.

Machine-readable outputs and input hashes are in `results/BCC_GROUPING_RECEIPT.json`; exact occupation membership is in `results/BCC_GROUPING_MEMBERSHIP.csv`; architecture results and paired differences are in `results/BCC_GROUPING_ARCHITECTURE_RESULTS.csv` and `results/BCC_GROUPING_PAIRED_DIFFERENCES.csv`.
