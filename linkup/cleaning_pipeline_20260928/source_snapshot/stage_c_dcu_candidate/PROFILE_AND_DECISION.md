# Profile and deployment decision

## Bounded local profile

The 32-item frozen diagnostic input was profiled with the unmodified V6 parser
and enrichment code. Results are evidence about this input, not the 298-million
row population.

| Step | Cumulative seconds | Share of parse + enrich |
| --- | ---: | ---: |
| Frozen V6/V5 parser | 0.527 | 89.8% |
| Enrichment total | 0.060 | 10.2% |
| Enrichment `_technologies` | 0.050 | 8.5% |

The implemented DCU mask can only reduce the last row. Even zero-cost, perfect
removal of that work has an end-to-end ceiling of about `1 / (1 - 0.085) =
1.09x`. Actual acceleration is lower because text must be batched and copied to
the card. The CPU implementation of the same mask produced exact output and a
1.03x median end-to-end speedup (0.484 s reference, 0.471 s candidate, five
iterations). That timing validates the harness and pruning effect; it is not a
claim about DCU speed.

Fourteen of 32 normalized texts contained non-ASCII and therefore took the
fail-safe all-pattern path. Across the sample, 10.56 of 20 technology families
remained enabled per row. The conservative policy is working, but the available
pruning is too small to support a claim that this candidate will beat the
existing 32-process CPU implementation.

## No-false-negative argument

Each frozen technology regex contains at least one necessary ASCII literal
listed at the same index in `ANCHORS`. The prefilter uses case-insensitive
substring matching without boundary restrictions, a strict superset of the
authoritative regex match. Patterns with alternatives have every alternative
represented. Any UTF-8 byte above ASCII enables every family, avoiding claims
about Python Unicode case-folding. The enrichment file SHA-256 and pattern count
are checked before use; drift fails closed. Python regex still decides every
match and output offset.

The table is auditable by family: large language model; LLM; generative AI;
ChatGPT/GPT; machine learning; deep learning; neural network; predictive model;
computer vision; natural language processing/NLP; artificial intelligence/AI;
Microsoft Office/MS Office; Excel; Power BI; Tableau; Salesforce; SAP; Python;
SQL; and Java.

## Decision

This historical profile motivated expansion beyond the original 20-family
candidate. It is not a production performance gate. The user later canceled
new benchmark and test-suite work and authorized the expanded hybrid path
without a 1.10x or 1.20x promise.

A materially larger opportunity would conservatively gate the frozen V5
software and AI modules, which accounted for 0.135 s and 0.084 s in this
profile. That requires a second, exhaustive necessary-literal proof plus a
candidate-owned copy of the V5 orchestration so normalization happens once.
It must not monkeypatch or edit frozen modules. Even perfect removal of software,
AI, and technology scans has a profile-specific ceiling around 1.85x; it still
cannot justify a promise that one DCU will outperform 32 CPU processes. The
experience and education regex engines remain on CPU and dominate the research
contract.

Wuzhen is known to be `gfx906`. Kunshan remains unprobed, so its pilot must set
`GPU_ARCH` from the actual device rather than reuse Wuzhen's value.

The delivered production candidate gates V5 software, V5 AI, and the 20
enrichment technology families. CPU retains HTML, education, experience,
complex regex semantics, evidence order, offsets, and truncation. Separate
single-decode Arrow IPC staging removes repeated Parquet row-group decompression;
that is an I/O optimization and is not DCU acceleration. The implementation is
hybrid and makes no claim of full-GPU execution or continuous 100% card use.
