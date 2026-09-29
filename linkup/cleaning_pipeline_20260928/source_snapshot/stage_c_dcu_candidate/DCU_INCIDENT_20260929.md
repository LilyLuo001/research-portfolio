# Wuzhen DCU incident and bounded usage note — 2026-09-29

Wuzhen job 45489216 was canceled at 12:18:33 +08:00 after 5,174 seconds,
accounting for 1.4372 card-hours. It completed no new shards. The previously
completed 349 shards remain preserved: 270 are published and 79 are sealed.
Production remains stopped, and no replacement job has been submitted.

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
