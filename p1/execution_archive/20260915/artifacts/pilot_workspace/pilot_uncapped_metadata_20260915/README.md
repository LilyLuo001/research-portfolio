# Uncapped metadata census status

The original root artifacts `run_uncapped_census.py`, `uncapped_metadata_aggregate.csv`, and `uncapped_metadata_receipt.json` are preserved as **INVALID_REQUIRED_SEMANTICS**. Their counts must not be used. The original implementation filtered identity links to candidate PERMNOs before assessing full source-row/date ambiguity, silently converted open link ends to 2099, merged analyst status on an incomplete key, and did not preserve all candidate denominator states.

The corrected implementation and its bounded pilot are under `corrected_v2/`. No corrected full batch may run without a matching `METADATA_PILOT_PASS.json` and explicit acknowledgement after the pilot receipt is returned.
