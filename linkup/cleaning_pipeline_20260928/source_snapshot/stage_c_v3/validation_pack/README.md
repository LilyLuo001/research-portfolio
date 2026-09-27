# USA validation pack (development review only)

This pack contains 120 ads: 20 from each of six Records `CREATED` cohorts. It is drawn only from the 1,030 USA ads in the existing deterministic 64-shard Kunshan pilot. It is not nationally representative, a full-corpus probability sample, an independent holdout, or a human gold standard.

Known real cases found in the bounded semantic review, targeted regression ledger, and `test_v3.py` were excluded (36 USA hashes). Other prior human inspection cannot be reconstructed completely, so unknown development contamination remains possible. No parser prediction was used in selection. O*NET was not joined, so occupation balance is not claimed.

Exact normalized-template groups are global across cohorts. One fixed-seed representative is retained per group before balanced cohort selection, preventing the same normalized template from appearing twice. Conditional inclusion probabilities and weights describe only this realized pilot frame.

`validation_sample.parquet` retains raw DESCRIPTION, source pointers, record dates, temporal-risk fields, the original selected-shard weight, normalized-template metadata, and conditional validation weights. `annotation_template.csv` is blank and must be completed through independent reading and evidence copying under `annotation_schema.json` and the Stage C annotation protocol.
