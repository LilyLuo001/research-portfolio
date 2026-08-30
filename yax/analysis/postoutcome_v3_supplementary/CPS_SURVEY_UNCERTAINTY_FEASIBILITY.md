# CPS Survey-Uncertainty Feasibility

> **POST-OUTCOME SUPPLEMENTARY ANALYSIS — NOT PART OF CONFIRMATORY YAX v1.1**

No design-consistent first-stage CPS survey resampling is implemented: the extract contains CPSID, SERIAL, CPSIDP, and MISH, but no public stratum/PSU variables or replicate weights. The available household, person-panel, and rotation identifiers can represent repeated-sample dependence, but cannot reconstruct the CPS multistage sample design or calibration-weight uncertainty.

Accordingly, no ad hoc microdata bootstrap was run. Reported confirmatory confidence intervals remain conditional on the realized CPS weighted employment-stock estimates and do not separately propagate first-stage survey-sampling uncertainty.
