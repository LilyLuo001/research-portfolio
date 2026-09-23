# Result authority

The final delivery uses corrected equal-issuer/equal-event/equal-available-sample model weights. The authoritative safe tables and figures are in `final/`, with the independent review in `REVIEW.md` and `REVIEW_RECEIPT.json`. Read the parent `RUN_RECEIPT.json` for completion state and SCC source paths; file existence alone is not a review PASS.

The original `model_parts/` receipts and validation traces are historical **pre-weight-correction** records. Their model losses remain on SCC in `model_parts/`; corrected fits/losses are in `model_parts_v2/`. Do not mix those versions or use the old statistics as the final conclusion.

The original `path_summary/` aggregate tables are historical **anchor-baseline, zero-inclusive persistence** records. The final path tables distinguish candidate-minus-one-second and candidate-anchor baselines and separate zero moves from nonzero same-direction persistence. The first-public clock remains unverified; a pre-anchor baseline is not guaranteed pre-news.

Raw DBN, feature panels, fitted objects, per-center predictions, event-level loss rows and detailed event paths stay on SCC. Only permitted aggregate tables, figures, code and receipts belong in Git. Charts of event paths are rendered on SCC rather than transferring the underlying detailed rows.
