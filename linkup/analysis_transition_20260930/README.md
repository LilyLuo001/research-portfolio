# First-wave analysis handoff

The October 2/5/7 delivery schedule is in
[`EXECUTION_ADDENDUM_OCT02_07.md`](EXECUTION_ADDENDUM_OCT02_07.md).
It adds execution milestones without replacing `NEXT_ANALYSIS_AGENDA.md`.
The first linkage coverage report establishes a reproducible engineering
baseline, not historical panel validity. The user or RA has confirmed human
review participation; the blind pack is due October 5.

This directory turns the frozen Stage C release into analysis inputs without
rerunning or changing the parser. `analysis_spec.json` is the variable-use and
output contract. It gives the 2026-09-28 final cleaning contract, release-v1
decision, and closure32 diagnosis precedence over the stale 2026-09-27 V5
variable register. Engineering production status does not promote candidate
labels to human-validated measures.

`run_first_wave.py` reuses `stage_c_release_v1/build_release_first_tables.py`.
It refuses to start unless `ALL_REGIONS_VERIFIED_COMPLETE.json` covers the
frozen 2,464 shards and the manifest IDs exactly equal the union of the frozen
regional plans. Published-receipt identity and the on-disk `SHARD_COMPLETE`
digest/content must agree. It then builds one anonymous additive summary per shard,
skips already valid summaries on restart, uses 1--8 local subprocesses, and
reuses a summary only when its leaf ID equals the current receipt hash, and
binds the work directory to the builder/gate/manifest/plan digests before any
resume. It merges only after every summary succeeds. It submits no cluster job and reads
no description text directly.

Prepare a private JSONL manifest outside Git with exactly one row per frozen
shard:

```json
{"shard_id":"...","shard_dir":"/absolute/path/to/published/shard","receipt":"/absolute/path/to/shard.published.json"}
```

Run on the host holding the published lean tables:

```bash
python analysis_transition_20260930/run_first_wave.py \
  --gate /absolute/path/ALL_REGIONS_VERIFIED_COMPLETE.json \
  --plans /absolute/path/kunshan-plan.jsonl /absolute/path/wuzhen-plan.jsonl \
  --manifest /private/path/analysis_shards.jsonl \
  --work-dir /private/path/first_wave_run \
  --workers 2
```

The merged outputs are the release funnel, CREATED first-observed queue
coverage, and candidate technology-by-experience cells. Their cells can be
nonexclusive because one ad may carry several evidence values. Unknown,
no-detection, non-applicant-context, and incomplete-processing states remain
visible. Education and explicit-no-experience counts stay audit-only.

Firm, title, BASE_HASH, and occupation are absent from the lean `ad_status`
schema. The next join should project only verified columns from Records/ONET,
account for every match failure, and attach them to the typed release keys. It
does not require raw-text parsing. Reuse the existing Stage D occupation and
taxonomy-membership tables before requesting any rescan.

CREATED supports delivery-snapshot first-observed queue descriptions only.
Complete-quarter reporting ends at 2026Q2; 2026Q3 is partial. No output here
supports historical-text, adoption-date, or causal claims. Revelio remains
unavailable and is outside this run.
