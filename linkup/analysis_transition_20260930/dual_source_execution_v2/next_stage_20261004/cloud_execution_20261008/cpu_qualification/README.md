# Kunshan CPU fixed-32 qualification

This directory contains public control code and receipts for a bounded 32-record reproduction qualification. Private source text, accepted candidates, raw model output, and record identifiers remain on the clusters.

The runtime is pinned llama.cpp commit `42b021b4dc42be573f1e1463528532fc8294c650` with Qwen3-8B Q4_K_M revision `7c41481f57cb95916b40956ab2f0b139b296d974`. Runtime, model, Batch002 inputs, frozen D43 prompt/schema/exporter, and validator dependencies were streamed directly from Wuzhen or copied as public control code to Kunshan. Scheduled prep job `123978572` verified the frozen checksum manifest, executed the binaries on a compute node, resolved shared libraries, imported Python dependencies, and bound Batch002 processing positions 1–32 to the adjudicated `FINAL_CANDIDATES_PRIVATE.jsonl` reference.

Inference uses CPU-only `kshctest02` tasks with 8 CPUs, 16 GiB, a 20-minute limit, and no GRES. Concurrency is four tasks (32 CPUs maximum). The partition limits each user to 20 submitted jobs, so the 32 records are split into arrays `0-15%4` and `16-31%4`. A scheduled quota controller submits the second half when the first leaves the quota and retargets the existing finalizer dependency.

`run_fixed32_cpu_array.sbatch` preserves stdout and stderr, writes an EXIT receipt, records actual process exit and generated-token count, and rejects output that reaches the 2,048-token cap or lacks a measurable stop count. `finalize_fixed32_cpu.py` treats failed or incomplete processes as transport errors even if partial stdout happens to parse. It uses the frozen D43 field-level exporter, applies no semantic repairs, retains all 32 rows in status/missing denominators, and reports eligible comparable coverage separately for state, main, and years. Agreement with the archived adjudicated candidates is a reproduction diagnostic, not an accuracy claim or production gate.

See `QUALIFICATION_DEPLOYMENT_RECEIPT.json` for current job IDs and the running snapshot. `ROOT_CPU_DECISION.json` records the authorized scope.
