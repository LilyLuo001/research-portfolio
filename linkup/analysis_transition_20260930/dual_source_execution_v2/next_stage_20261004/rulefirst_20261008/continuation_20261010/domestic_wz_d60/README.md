# D60 Wuzhen bounded in-place wave

This directory records the first D60 production wave that ran wholly in place on Wuzhen after BU use ended. It uses the frozen D58 runner and the existing 1,106-entry Wuzhen regional plan. The four selected source/sidecar pairs were verified by full SHA-256 before execution; private shard identities and paths remain only on the protected cluster.

The `wzhdtest` QOS rejected a CPU-only submission and required a one-DCU reservation. All accepted jobs therefore reserved the minimum one Hygon DCU while executing CPU-only Python. This is an allocation constraint, not DCU acceleration.

`PREFLIGHT_PUBLIC.json` records the five-minute runtime and input gate. `QA_PUBLIC.json` records the aggregate mechanical acceptance result. `EXECUTION_PUBLIC.json` records scheduler resources, exits, memory use, storage, and the one pre-run wrapper failure. No raw text, row-level output, private manifest, record identifier, or credential is present here.

The result is bounded to four shards. It does not authorize an additional Wuzhen wave, a metadata join, or any renewed BU processing.
