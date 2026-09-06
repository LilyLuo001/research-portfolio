# Amendment 1: support-specific one-at-a-time panels

Status: **post-outcome amendment made after the initial common-support run and before the amended estimates were produced.**

The initial registered run used one literal support common to every static and generated characteristic. It retained 341 of 468 primary occupations and 76.34 percent of primary-support employment. That is useful for the cumulative model but unnecessarily changes the population for every one-at-a-time diagnostic.

To satisfy the prompt's requirement to separate sample loss from conditioning, the amended output adds, for each one-at-a-time control, a baseline and augmented estimate on that control's own maximal finite subset of the 468-occupation support. The SOC2 comparison uses all 468 occupations. Historical beta quintiles and Webb normalization remain anchored to the original primary universe. Each control is standardized with 2017--2019 employment weights on its declared subset. Common wild-score multipliers are used within each baseline/augmented pair.

This amendment was triggered by the common-support coverage fact, not by the direction or significance of any coefficient. The original common-support output is preserved in Git commit `8e3b876266e09679467b5a0c640c3c16b0c51974`; the cumulative panel continues to use the original 341-occupation literal common support. The amended run also reports every fitted slope and interval, rather than only the Q5 target, so suppressor relationships and unstable nuisance estimates are visible.

