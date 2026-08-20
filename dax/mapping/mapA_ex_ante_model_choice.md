# Mapping A ex-ante model and blocking freeze

**Frozen:** 2026-08-18T17:32:17Z, before computing or inspecting any
occupation-title or task-pair similarity.

## Model pin

- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Hugging Face revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
- License declared by the upstream model card: Apache-2.0
- Output dimension: 384
- Runtime: SCC module `pytorch/1.12.1` (`torch 1.12.1+cu116`) and
  `transformers/4.25.1` under Python 3.8.10
- Encoding: tokenizer truncation at the model's Sentence Transformers limit of
  256 wordpieces, attention-mask mean pooling, then L2 normalization; cosine
  similarity is the normalized-vector dot product. Because the release contract
  defines similarity on `[0, 1]`, negative cosine values are clipped to zero;
  this is below every grading threshold and therefore cannot change routing.

The model is English, compact enough to execute deterministically on SCC CPU,
and trained for sentence similarity. Its Apache-2.0 license and immutable
revision make the computational dependency independently retrievable. The
384-dimensional representation is adequate for short occupational task
statements without making the 19,259-by-block computation operationally
fragile. No mapping outcomes informed this choice, and the pin will not be
tuned after outcomes are observed.

## Frozen blocking rule

GDPval contains 44 occupation labels and 220 tasks. For every O*NET-SOC
occupation, embed its official O*NET occupation title and rank the 44 GDPval
occupation labels with the same pinned model. The candidate block is every
GDPval task belonging to the 10 nearest occupation labels. A cutoff tie is
resolved by the normalized occupation label and then the original label. This
produces about 50 candidates per O*NET task while retaining broad semantic
adjacency; it avoids a brittle exact-title crosswalk without requiring an
unregistered model or human judgment.

Within the block, task candidates rank by cosine similarity descending and
then `gdpval_task_id` ascending. The grading constants remain exactly the
pre-registered values: similarity floor 0.60, auto-accept 0.80, minimum margin
0.05, and occupation coverage floor 0.70. Every O*NET task must be accepted,
queued, or unmatched.

## License and sealing decision

The GDPval parquet and all text-bearing intermediates remain under
`/usr3/graduate/qluo/dax-private`. Neither task text, prompts, excerpts,
occupation labels, embeddings, nor derived textual content may enter Git or a
release artifact. Because task-ID redistribution rights have not been
affirmatively documented, the task-ID mapping and adjudication queue also stay
private; Git receives only aggregate receipts and a hash-addressed manifest.
