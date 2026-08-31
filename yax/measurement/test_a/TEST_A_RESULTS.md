# Frozen Test A construct diagnostics

This closes the outcome-free Test A matrix incorporated by `DESIGN_FREEZE_v2.md` through `RESEARCH_PLAN_v5.md`. No protected post-period outcome is read.

Common complete support for the joint residual audit: **348 occupations**.

## Employment-weighted Pearson correlations

| AI measure | cognitive_ability_importance | manual_physical_ability_importance | rti_autor_dorn | required_education_category_index | log_mean_annual_wage | dingel_neiman_telework | stem_major_group_share | onet_computers_importance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aioe_admin_equal | 0.653 | -0.936 | 0.161 | 0.688 | 0.611 | 0.741 | 0.249 | 0.849 |
| aioe_ability_direct | 0.689 | -0.913 | 0.152 | 0.708 | 0.640 | 0.746 | 0.242 | 0.847 |
| aioe_oews2018_source_weighted | 0.660 | -0.939 | 0.148 | 0.700 | 0.617 | 0.754 | 0.249 | 0.854 |
| dv_rating_alpha | -0.032 | -0.266 | 0.217 | -0.034 | 0.011 | 0.200 | 0.436 | 0.304 |
| dv_rating_beta | 0.478 | -0.758 | 0.169 | 0.425 | 0.478 | 0.589 | 0.371 | 0.797 |
| dv_rating_gamma | 0.598 | -0.810 | 0.108 | 0.530 | 0.600 | 0.618 | 0.253 | 0.833 |

## Joint characteristic residual audit

| AI measure | R² on characteristics | residual SD | effective occupations | top-five share | five largest contributors |
|---|---:|---:|---:|---:|---|
| aioe_admin_equal | 0.964 | 0.189 | 35.5 | 0.304 | Security guards and gambling surveillance officers (8.8%); Driver/sales workers and truck drivers (6.6%); Registered nurses (6.1%); Sales representatives, wholesale and manufacturing (5.2%); Hairdressers, hairstylists, and cosmetologists (3.7%) |
| aioe_ability_direct | 0.954 | 0.214 | 37.8 | 0.290 | Customer service representatives (9.7%); Driver/sales workers and truck drivers (5.6%); Maids and housekeeping cleaners (5.1%); Registered nurses (4.8%); Security guards and gambling surveillance officers (3.7%) |
| aioe_oews2018_source_weighted | 0.971 | 0.171 | 44.2 | 0.249 | Registered nurses (7.0%); Sales representatives, wholesale and manufacturing (5.3%); Chief executives (4.9%); Driver/sales workers and truck drivers (4.1%); Hairdressers, hairstylists, and cosmetologists (3.7%) |
| dv_rating_alpha | 0.368 | 0.795 | 31.5 | 0.337 | Bookkeeping, accounting, and auditing clerks (9.6%); Interpreters and translators (7.9%); Data entry keyers (7.2%); Driver/sales workers and truck drivers (6.1%); First-Line supervisors of office and administrative support workers (2.8%) |
| dv_rating_beta | 0.743 | 0.507 | 36.9 | 0.280 | Driver/sales workers and truck drivers (9.7%); First-Line supervisors of retail sales workers (7.3%); Bookkeeping, accounting, and auditing clerks (4.3%); Interpreters and translators (3.5%); Hairdressers, hairstylists, and cosmetologists (3.2%) |
| dv_rating_gamma | 0.811 | 0.435 | 31.5 | 0.297 | First-Line supervisors of retail sales workers (12.9%); Driver/sales workers and truck drivers (6.7%); Hairdressers, hairstylists, and cosmetologists (3.6%); Sales representatives, wholesale and manufacturing (3.5%); Bus and truck mechanics and diesel engine specialists (3.1%) |

## Definitions and scope

- Cognitive intensity is the mean O*NET Importance rating across the official `1.A.1` Cognitive Abilities branch.
- Manual/physical intensity is the mean Importance rating across `1.A.2` Psychomotor and `1.A.3` Physical Abilities.
- Education is the percentage-weighted mean category of O*NET `2.D.1` Required Level of Education; it is an ordered-category index, not years of schooling.
- Wage is log OEWS-2021 mean annual wage, collapsed with OEWS employment weights.
- STEM share is the OEWS-employment share of SOC major groups 15, 17 and 19 within each Census-2018 occupation mapping.
- RTI, teleworkability and O*NET computer-use importance are the already frozen YAX measures.
- Joint residual diagnostics use common complete support and frozen 2017-01–2022-11 employment-stock weights. They are measurement diagnostics, not post-outcome employment estimates.

Full pairwise sample sizes, weighted Spearman correlations, raw rankings, rank overlap, residual correlations, and named contributors are in the machine-readable files and receipt.
