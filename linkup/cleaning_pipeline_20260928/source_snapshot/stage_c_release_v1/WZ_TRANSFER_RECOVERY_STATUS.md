# Wuzhen transfer recovery status

Status at 2026-09-29 10:14 CST:

- The configured private key and pinned host-key file had disappeared from the Wuzhen private runtime. They were restored atomically with mode `0600`; no credential content is stored in this repository.
- The Wuzhen transfer wrapper now loads the authorized regional proxy environment, supports Bash 4.2 empty arrays, and uses a fresh ControlMaster path. The proxy helper and SSH configuration remain private runtime files outside Git.
- Direct and proxied connections to the Huazhong E-shell remain intermittent at SSH key exchange. A single 60-second-connect/75-second-total proxy test was rejected immediately at key exchange, so increasing the timeout does not resolve the current failure.
- The sole publisher remains alive and fail-closed. Generated sources are retained until byte, SHA-256, manifest, and target publication checks pass. No raw input was deleted.
- At the recorded time, 97 Wuzhen shards were published and 345 were computed/queued. The local generated backlog contained 248 sealed shard directories with about 4.29 GB of output payload plus one active work directory. Canonical preparation files referenced in historical receipts were no longer present and are excluded from this live-size figure.
- `hx1hdnormal` is a Slurm partition, not an SSH hostname. No Huazhong compute allocation was opened for this recovery.

At 2026-09-29 10:25 CST, the user authorized stopping Wuzhen semantic compute
to prevent the bounded local output buffer from filling while publication was
blocked. The stop preserved all completed work: 349 of 1,106 shards were done,
comprising 97 already published shards and 252 sealed local shards. The
remaining 757 shards had not completed. Raw input was not deleted. Kunshan
part 0 and part 1 continued on their CPU jobs and were not changed.

Unresolved operational dependency: new SSH sessions from Wuzhen to the Huazhong E-shell must become available, or an approved persistent relay must be deployed. Final publication timing cannot be estimated while this connection-layer failure continues. Any recovery must resume from the existing published and sealed receipts rather than recomputing those 349 shards.

## DCU remaining-shard recovery

The first DCU submission, job 45489052, was canceled. The login environment
had exported `SBATCH_GRES_FLAGS` / `SLURM_GRES_FLAGS=enforce-binding`, which
overrode the reviewed batch directive and constrained the CPU request. The
fail-closed submission wrapper now removes both inherited variables and passes
`--gres-flags=disable-binding` explicitly on the `sbatch` command line.

Authoritative recovery job **45489216** started at 10:52:19 +08:00 on
`b01r3n14` with 32 CPUs, 96 GB, and one DCU. At 10:53:22 the 32-worker regional
runner and an actual `dcu_anchor_scan` process were observed. The run retains
the original 349 completed shards and addresses only the remaining 757. This
is execution evidence, not a claim of continuous 100% accelerator utilization
or improved end-to-end speed. No new test suite or performance gate was run.
