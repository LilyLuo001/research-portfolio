# Generator usage

Run only after the full canonical frame and the heldout-400 key-only manifest are frozen. The private output path must be outside the repository.

```sh
python3 build_blind_review_pack.py \
  --frame /private/path/canonical_review_frame.csv \
  --frame-metadata /private/path/canonical_review_frame.metadata.json \
  --heldout-key-manifest /private/path/heldout_400_keys.csv \
  --reviewer-schema ../../execution_oct02_07/reviewer_pack_schema.json \
  --predictions /private/path/frozen_model_predictions.csv \
  --private-output-dir /private/path/human_review_pack_20261003 \
  --public-receipt /path/to/repo/analysis_transition_20260930/pre_revelio_execution_v1/human_review/ACTUAL_PACK_RECEIPT.json \
  --repo-root /path/to/repo
```

Frame metadata and the heldout JSON manifest must declare the same nonblank `key_namespace`, `stable_key_type: "string"`, and nonblank source provenance. The heldout manifest must contain a nonempty, unique `private_keys` list. Its intersection with the frame may legitimately be zero when the canonical frame was already heldout-excluded; the receipt records the observed intersection count.

The generator refuses a frame with embedded prediction columns, duplicate or blank private keys, blank text or strata, mismatched key namespaces, invalid metadata or heldout keys, more sampling strata than core slots, a private output path inside the repository, or a design other than 32 core plus at most eight challenge ads.

Private outputs are `reviewer_pack.csv`, `private_answer_key.csv`, and `review_assignments.csv`. Only the aggregate receipt belongs in the repository. Model predictions in the answer key remain hidden until human labels are locked.
