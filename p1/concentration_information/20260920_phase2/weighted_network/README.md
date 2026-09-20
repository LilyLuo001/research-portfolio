# Bounded CRSP weighted-network input check

This directory is a new phase-2 diagnostic. It does not amend prior execution results and does not calculate a weighted network.

`run_unit_contract_check.py` reads one named 2022 holdings partition on SCC, date-valid CRSP header classes, and 2022 `fund_summary2`. Only aggregate counts and source-path hashes are written locally. It reads no EPS, forecast, return, or quote fields.
