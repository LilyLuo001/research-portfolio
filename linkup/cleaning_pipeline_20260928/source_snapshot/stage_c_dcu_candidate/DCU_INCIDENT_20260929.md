# Wuzhen DCU incident and bounded usage note — 2026-09-29

Wuzhen job 45489216 was canceled at 12:18:33 +08:00 after 5,174 seconds,
accounting for 1.4372 card-hours. It completed no new shards. The previously
completed 349 shards remain preserved: 270 are published and 79 are sealed.
At that incident checkpoint, production was stopped and no replacement job
had been submitted.

A 113-second observation containing 15 samples identified the assigned device
as `renderD128`; Slurm device index 0 and the process-visible device agreed.
Every GPU-busy sample was zero. Observed VRAM was 34,287,616 of 17,163,091,968
bytes (about 0.2%), and power stayed near 23.93 W within the observed 23–24 W
range. Twenty-two `dcu_anchor_scan` processes were present but consuming CPU.
Process presence alone was therefore insufficient evidence that useful DCU
work was occurring. The root cause has not been identified.

Visible `sacct -S 2026-09-07 -X` records for `wzhdtest` sum to 14.016944
card-hours, about 7.0% of a 200-card-hour reference allocation. Subtracting
that sum gives 185.983056 card-hours, but this is only an arithmetic remainder
under the assumption that there is no usage outside the visible accounting
records. It is not an official balance or quota reading.

This note records the incident and bounded accounting evidence only. Raw logs,
private paths, credentials, and private shard manifests are excluded. The
separate work to improve stage logging and timeouts was incomplete at this
checkpoint and is not claimed as a fix.

## Recovery status

After the single-owner 8,192-row run completed its writer path, the writer was
updated to reuse one 32-process pool for parallel normalization and subsequent
authoritative CPU parsing/writing, with one coordinator-owned DCU batch scan
between those phases. Stage wall times and HIP-event kernel milliseconds are
now included in the lean completion receipt.

Recovery job **45492940** started at 12:43:48 +08:00 on `b01r3n14` with 32
CPUs, 96 GB, one DCU, and a 48-hour limit. At the first recorded checkpoint it
was running, but its first new shard output had not yet been validated. This is
not evidence of continuous accelerator saturation or an end-to-end speedup.
The preserved 349 shards remain outside the 757-shard recovery plan.

At 12:45:06 +08:00, the first recovery shard completed, sealed, and queued:
83,544 rows in 105.541 seconds. Measured stages were 10.982 seconds for
normalization, 2.327 seconds for the GPU-call phase, and 86.613 seconds for the
parallel CPU parse/write phase. Within the latter phase, the worker interval
unions were 85.875 seconds for parsing and 6.966 seconds for writing; those
intervals overlap and must not be added. The single HIP call reported 740.410
kernel milliseconds. One device sample observed 100% busy, 1.97% VRAM use,
and 99 W, which confirms activity at that instant but cannot establish
continuous saturation. CPU parsing remains the dominant measured stage.

## Two-node continuation

After six of the 757 DCU-version shards were sealed, the remaining 751 were
frozen into two disjoint plans: 378 shards representing 45,432,289 raw rows
and 373 shards representing 45,432,965 raw rows. Jobs **45493551** and
**45493552** then ran concurrently on different Wuzhen nodes, each with 32
CPUs, 96 GB, and one DCU. Their first sealed shards contained 84,059 and
83,318 rows respectively; the first partition subsequently sealed a second
shard.

Each partition writes to its own 3.5 GB buffer under a shared checkpoint
namespace. Together with the measured 0.748 GB preserved root backlog, this
stays below the existing 8 GB regional buffer limit. The publisher for the two
new subdirectories and the existing root publisher scan disjoint directory
levels, so they cannot consume the same sealed shard. A separate controller
accepts completion only when the frozen sets reconcile as 6 + 378 + 373 = 757,
then applies the existing mixed-version 349 + 757 = 1,106 code, provenance,
and receipt gate. These observations establish concurrent execution and valid
first outputs; they do not establish continuous DCU saturation or a speedup.
