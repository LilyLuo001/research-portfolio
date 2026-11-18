# Stage5 frozen field-local confirmation

This bundle contains no real inputs, model outputs, new labels, cloud operations,
or changes to historical artifacts. `CONFIRMATION_PROTOCOL.json` fixes 51 measures,
the existing thresholds, and B/D core, A/C support, E extension dependencies.

The unchanged Formal800 schema and local validator are hash-pinned. The existing
`FieldValidator` isolates unrelated field errors. Primary structured agreement
uses one-to-one matching on represented values and frozen source sentence/line
units. Exact quote existence remains mandatory; exact quote boundary agreement
is diagnostic only. `object_detail` and branch `condition` display prose remain
in the original reviews but do not determine scores.

This does **not** qualify exact named-object concepts, arbitrary qualification
condition semantics, universal posting minimum years, or complete computable B
logic. Advertisement entry labels also do not qualify person-level D histories.
All five modules remain in the contract; production dependencies are selective.

Before any fresh model request, the runner must:

1. Exclude every previously exposed and protected context using trusted manifests.
2. Freeze at most 150 unique identities and contexts. Assign `confirmation` or
   `challenge` beforehand; challenges never contribute gate support or coverage.
3. Compute `source_units_sha256 = digest_json(source_units(full_document))` using
   `field_score.py`. Freeze the actual frame and this bundle's receipt SHA.
4. Preserve unchanged private Formal800 outputs, blind Kimi to Luna, and preserve
   complete accounting even when a call fails or a field is unknown.

Frame JSONL rows contain `record_id`, `context_sha256`, `partition`,
`protected: false`, `fresh_never_exposed: true`, and `source_units_sha256`.
Cases JSONL rows contain the same identity, the original `packet` including its
trusted `assignment`, and `candidate`/`reference` Formal800 objects or `null`.
Optional `*_processing_status` distinguishes missing/failed work. A late-protected
row uses `protection_blocked: true` and metadata only; do not load its payload.
The scorer fills missing rows as unprocessed and keeps every frozen slot.

The external frame-freeze receipt must contain:

```json
{
  "frame_sha256": "SHA256 of the actual frozen frame file",
  "protocol_bundle_sha256": "SHA256 of PROTOCOL_FREEZE.json",
  "frozen_before_first_request": true
}
```

The runner must retain trustworthy evidence for that assertion, freshness,
blindness, budget admission and request ordering; this scorer cannot establish
those historical facts from a Boolean.

```sh
python3 -m unittest -v test_field_score.py
python3 field_score.py --frame /private/frozen_frame.jsonl \
  --cases /private/joined_cases.jsonl --frame-freeze /private/FRAME_FREEZE.json \
  --repo /path/to/reproducibility_git --out /private/new_stage5_scores.json
```

Reports contain only aggregate scores and at most six hash-ranked diagnostic
Astra case identifiers. The queue neither calls Astra nor alters the original
Kimi primary reference. It is not authority to exceed the $50/150-input/6-Astra
caps. A later <=10,000-input pilot still requires only the qualified dependencies
actually used and the separate authorized runtime controls.
