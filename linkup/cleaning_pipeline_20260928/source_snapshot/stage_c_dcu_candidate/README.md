# Stage C DCU candidate

This is an isolated feasibility candidate. It does not modify frozen V5/V6,
the production enrichment module, or either running Kunshan job.

## Accelerated boundary

The only offloaded operation is a batched, conservative substring scan for the
20 frozen technology-regex families. The DCU returns a bit mask saying which
unchanged Python regexes may be worth running. CPU code still performs HTML
normalization, every authoritative regex match, boundary check, evidence
offset, relation decision, ordering step, and Parquet operation. Non-ASCII
normalized text enables all regex families as a fail-safe. False positives are
allowed; false negatives fail the oracle test.

This is a hybrid CPU+DCU path. It does not accelerate the V5/V6 education and
experience parser and does not promise full-card or continuous 100% use. A full
regex/HTML GPU port would be a separate large project with substantial
equivalence risk and is outside this candidate.

## Build and check on a reserved card

Wuzhen's observed card is `gfx906`; Kunshan must be probed before choosing its
target. The architecture is a build parameter rather than a source constant:

```sh
make HIPCC=/public/software/compiler/dtk-21.10/bin/hipcc GPU_ARCH=gfx906
export LINKUP_DCU_EXECUTABLE_SHA256=$(sha256sum dcu_anchor_scan | awk '{print $1}')
```

The user canceled further test-suite and performance-gate work. Operations runs
one representative staged shard only to confirm compilation, HIP launch,
receipt provenance, output conservation, and absence of hidden CPU fallback.
No 1.10x or 1.20x threshold is a release promise.

Historical evidence must be read by version. The original 237-case check
covered only the 20-family enrichment candidate. The later CPU-oracle check of
the expanded software+AI+technology adapter covered 285 cases and matched the
full V6 payload and enrichment output, but it did not execute the expanded HIP
binary on a DCU. True-device validation remains the one-shard operational check.

The candidate is pinned to enrichment SHA-256
`cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6`.
Any frozen-module change fails closed until the anchor proof is reviewed.

## Remaining-shard production entrypoint

`lean_writer_dcu.py` is a drop-in writer CLI. It normalizes batches once, sends
up to 4,096 normalized texts to the HIP scanner (4,096 independent blocks of
64 threads), then runs the unchanged CPU authority for all retained families.
It fails if the compiled scanner is missing, so a run cannot silently fall back
to CPU-only behavior.

The entrypoint also fixes an independent input bottleneck: the coordinator
decodes each source Parquet row group once and writes the original 32 equal row
ranges as node-local Arrow IPC. Each CPU worker reads only its own range. This
avoids the old behavior where 32 workers reopened and decompressed the same 12
row groups. This gain is CPU/I/O work and must not be attributed to the DCU.

Create a new remaining-only plan without overwriting the canonical full plan:

```sh
python3 make_remaining_plan.py \
  --full-plan "$SEMANTIC/plan.jsonl" \
  --checkpoint-root "$SEMANTIC/checkpoints" \
  --output "$SEMANTIC/plan.dcu_remaining.jsonl"
```

The reported counts must match the operational checkpoint (currently expected
to be 349 sealed and 757 remaining) before submission. Build with the observed
Wuzhen architecture and submit `run_wuzhen_dcu_remaining.sbatch` only after a
one-shard compile/run/output check.

The remaining job writes `REGION_QUEUE_COMPLETE.dcu_remaining.json`, not the
canonical full-region marker. After all 1,106 shards are published, operations
must reconcile the full plan and write the standard marker. The existing final
gate accepts only the old lean-writer SHA; it must not be run unchanged on mixed
old/new writer receipts. A provenance-aware gate must accept exactly the old
writer hash for the preserved 349 receipts and the reviewed DCU writer hash for
the remaining plan while retaining the same parser and enrichment hashes.
