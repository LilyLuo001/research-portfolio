# Kunshan CPU qualification controls and receipts

This directory records the D47 CPU-only qualification control plane. It is a
32-record diagnostic comparison against the accepted Batch002 reference, not
production inference and not a new accuracy estimate. No DCU or HIP route is
used. The runner requests 8 CPUs per task, 16 GiB, and a 20-minute limit; two
waves use array concurrency 4, keeping maximum concurrent inference at 32
CPUs.

The frozen D43 exporter compares field-level values for `general_work`,
`occupation_task`, and `industry_domain`. Missing, unknown, or invalid fields
remain null/error values. The reference is an accepted model-assisted output,
not human gold. Full source text is passed to the pinned runtime without
truncation; the token cap fails a task when the input is too long.

Preparation first failed on the scheduled node because the JSON-schema
dependency was unavailable. The recorded follow-up chain therefore has
`production_started=false`; the finalizer also failed for the same missing
`jsonschema` dependency. These receipts preserve actual scheduler outcomes.
No successful inference or qualification acceptance is claimed.

The scripts bind the pinned runtime, model, prompt, schema, and archived
source/reference paths by SHA-256. Raw inputs and model outputs remain in the
cluster run directory and are not part of this Git publication.
