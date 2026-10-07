# Bounded local inference route, 2026-10-07

This folder records one bounded attempt to establish a free local model-inference route for the LinkUp formal text measurement. It is an operational routeability and throughput check, not a semantic-quality evaluation or validation study.

The selected stack is the official Apache-2.0 `Qwen/Qwen3-8B-GGUF` Q4_K_M file with the official `ggml-org/llama.cpp` CPU runtime. The runtime source is pinned to commit `42b021b4dc42be573f1e1463528532fc8294c650`; the job resolves an immutable Hugging Face repository revision before downloading the model and records the model-file SHA-256 after download. The official model card documents Q4_K_M as approximately 5.03 GB and gives direct llama.cpp instructions. The official llama.cpp build guide documents the CMake CPU build used here.

`probe_compute.sbatch` ran as Slurm job `123914479`. Its sanitized result is `PROBE_RECEIPT.json`. `run_qwen3_8b_cpu.sbatch` was the only runtime/model trial. Job `123914627` requested 16 CPUs, 32 GB RAM, and a one-hour hard limit on `kshctest02`. It stopped after seven seconds because the configured compute-node proxy endpoint was unreachable. The subsequent EXIT trap also found that the job had not loaded the available Python module, so the scheduler exit code reflects that secondary receipt-writing error. `RUN_RECEIPT.json` preserves both causes and the scheduler evidence. No runtime or model bytes were downloaded, no advertisement reached inference, and the 10,000-record run was not started.

`submitted_failed.sbatch` is the exact 9,806-byte script retrieved from the remote submission path for job `123914627`; its SHA-256 matches the pre-correction submission hash in `RUN_RECEIPT.json`. The local `run_qwen3_8b_cpu.sbatch` has since been corrected to load `python/3.8.10` before installing the receipt trap and to derive attempted/completed document counts from actual inference markers and a validated PASS. This corrected version was not executed. A future rerun would also need a working compute-node egress route. That rerun was not made here because the authorization allowed one bounded runtime/model attempt.

`synthetic_source.txt` is an invented 125-byte fixture created for this routeability test. It contains no real advertisement text and is included for reproducibility. Model weights, build products, proxy configuration, and credentials stay outside this folder and outside Git.

Official sources:

- https://huggingface.co/Qwen/Qwen3-8B-GGUF
- https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
