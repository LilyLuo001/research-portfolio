#!/usr/bin/env python3
import pandas as pd
from build_protected_membership_sidecar import interval_relation

assert interval_relation('2022-01-01','2022-01-01','2021-01-01','2021-01-01')=='ROBUST_EXCLUSION_CONDITION_INSIDE_ANALYSIS_WINDOW'
assert interval_relation('2022-01-01','2022-01-01','2019-12-31','2019-12-31')=='ROBUST_EXCLUSION_CONDITION_BEFORE_ANALYSIS_WINDOW'
assert interval_relation('2022-01-01','2022-02-01','2020-01-15','2020-01-15')=='ROBUST_EXCLUSION_CONDITION_SPANS_BEFORE_TO_INSIDE_BOUNDARY'
assert interval_relation('2022-01-01','2022-01-01',None,'2021-01-01')=='UNKNOWN_MISSING_BOUND'
# Same calendar date as the upper boundary is not treated as an exact midnight.
assert interval_relation('2022-01-01','2022-01-01','2024-01-01','2024-01-01')=='UNKNOWN_BOUNDARY_CROSSES_SUPPORTED_INTERVAL'

# Package A is the minimum constituent bounds; I is the maximum constituent bounds.
d=pd.DataFrame({'alo':['2022-01-02','2022-01-01'],'ahi':['2022-01-04','2022-01-03'],'ilo':['2022-06-01','2022-06-02'],'ihi':['2022-06-03','2022-06-04']})
assert d.alo.min()=='2022-01-01' and d.ahi.min()=='2022-01-03'
assert d.ilo.max()=='2022-06-02' and d.ihi.max()=='2022-06-04'
print('6 fixtures PASS')
