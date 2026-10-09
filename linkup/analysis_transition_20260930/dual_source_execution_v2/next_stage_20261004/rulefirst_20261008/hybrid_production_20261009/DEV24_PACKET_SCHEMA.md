# Development relation decision packet

The scheduled selector emits at most 24 unique development documents, at most
four assigned to each disclosed relation group. It never reads eval80.

Each private JSONL row contains:

- stable source SHA, frozen arm and queue position;
- one assigned `decision_group`, all mechanically matched groups, and the
  predicate details responsible for selection;
- full normalized review text and its Unicode-offset coordinate system;
- all frozen v1.2 flags, review reasons and evidence, without repair;
- empty `review_fields` for root's bounded Pro review.

The public receipt contains only input hashes, row counts, candidate/selection
counts, scheduler provenance and the private packet hash. It contains no text,
record identifiers, evidence quotes or model output.
