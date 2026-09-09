# Current-contract HonestDiD findings

These results apply only to the dynamic `P` functional: the equal-observed-post-month average of quarterly Q5-versus-Q1 coefficients relative to 2022Q4. They are not intervals for the nonlinear static coefficient.

## Results

- `unconditioned`, `full_2017Q1_2022Q3`: estimate -0.119889, conventional 95% interval [-0.263649, 0.023871]. zero: conventional interval already includes zero for dynamic P.

- `unconditioned`, `recent_2021Q1_2022Q3`: estimate -0.119889, conventional 95% interval [-0.263649, 0.023871]. zero: conventional interval already includes zero for dynamic P.

- `family_month`, `full_2017Q1_2022Q3`: estimate -0.207434, conventional 95% interval [-0.425163, 0.010295]. zero: conventional interval already includes zero for dynamic P.

- `family_month`, `recent_2021Q1_2022Q3`: estimate -0.207434, conventional 95% interval [-0.425163, 0.010295]. zero: conventional interval already includes zero for dynamic P.


## Interpretation limits

The full and recent windows are both reported. The recent calibration uses consecutive 2021Q1--2022Q3 quarters; no pandemic quarter was deleted from inside a retained sequence and no calendar gap was compressed. Smoothness constrains adjacent-quarter second differences, while relative magnitude constrains consecutive-quarter changes and unions over all signed maximal pre changes.

The official high-level package functions returned finite intervals, but do not expose every underlying optimizer status. The retained execution log therefore records returned results and warnings without claiming an unavailable per-optimization certificate.
