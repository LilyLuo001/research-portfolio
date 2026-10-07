# Bounded local inference route, 2026-10-07

This folder records one bounded attempt to establish a free local model-inference route for the LinkUp formal text measurement. It is an operational routeability and throughput check, not a semantic-quality evaluation or validation study.

The selected stack is the official Apache-2.0 `Qwen/Qwen3-8B-GGUF` Q4_K_M file with the official `ggml-org/llama.cpp` CPU runtime. The runtime source is pinned to commit `42b021b4dc42be573f1e1463528532fc8294c650`; the job resolves an immutable Hugging Face repository revision before downloading the model and records the model-file SHA-256 after download. The official model card documents Q4_K_M as approximately 5.03 GB and gives direct llama.cpp instructions. The official llama.cpp build guide documents the CMake CPU build used here.

`probe_compute.sbatch` ran as Slurm job `123914479`. Its sanitized result is `PROBE_RECEIPT.json`. `run_qwen3_8b_cpu.sbatch` was the only runtime/model trial. Job `123914627` requested 16 CPUs, 32 GB RAM, and a one-hour hard limit on `kshctest02`. It stopped after seven seconds because the configured compute-node proxy endpoint was unreachable. The subsequent EXIT trap also found that the job had not loaded the available Python module, so the scheduler exit code reflects that secondary receipt-writing error. `RUN_RECEIPT.json` preserves both causes and the scheduler evidence. No runtime or model bytes were downloaded, no advertisement reached inference, and the 10,000-record run was not started.

`submitted_failed.sbatch` is the exact 9,806-byte script retrieved from the remote submission path for job `123914627`; its SHA-256 matches the pre-correction submission hash in `RUN_RECEIPT.json`. The local `run_qwen3_8b_cpu.sbatch` has since been corrected to load `python/3.8.10` before installing the receipt trap and to derive attempted/completed document counts from actual inference markers and a validated PASS. This corrected version was not executed. The initial attempt stopped at its predefined operational budget.

The bounded Wuzhen recovery is documented in `recovery_20261007/RECOVERY_PROBE_RECEIPT.json`. Job `46032122` proved an authenticated private GCC 11.2.1 toolchain and C++17 `std::filesystem` support. Build-gate job `46032252` then requested 16 CPUs, 32 GB, two scheduler-required DCUs, and a one-hour limit. It ended after 47 seconds: CMake configured the pinned llama.cpp source, but the generated tree had no `llama-cli` target. `recovery_20261007/submitted_build_46032252.sbatch` preserves that exact failed submission.

Inspection of the pinned source showed that `llama-cli` is gated behind the disabled server option, while `llama-completion` and `llama-tokenize` are available tool targets. Corrected same-stack job `46032322` was submitted to build those targets with the explicit private compilers and the same resource bounds. `recovery_20261007/BUILD_SUBMISSION_46032322.json` records the live submission state. At that recorded boundary, no model had been downloaded, no document had reached inference, and no bulk run had started.

The route was subsequently completed and stopped after bounded evidence. The corrected build succeeded; the official pinned Qwen3-8B Q4_K_M artifact was verified; an invented fixture completed; and the fixed four-record pilot began. One pilot record completed and a second was partial when root adjudication found a decisive experience-object binding failure and stopped job `46035182`. The raw output also failed the strict v1.1 validator after runtime-envelope removal and still failed after lossless unique-quote offset repair. `RUN_COMPLETION_RECEIPT.json` records deidentified validation counts, timing, hashes, every scheduler allocation, and the no-bulk decision. Raw outputs, source text, identifiers, and full validator errors remain private.

`synthetic_source.txt` is an invented 125-byte fixture created for this routeability test. It contains no real advertisement text and is included for reproducibility. Model weights, build products, proxy configuration, and credentials stay outside this folder and outside Git.

Official sources:

- https://huggingface.co/Qwen/Qwen3-8B-GGUF
- https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
