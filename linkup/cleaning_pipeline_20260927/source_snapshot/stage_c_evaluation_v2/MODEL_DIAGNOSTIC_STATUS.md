# Model diagnostic status

The 1,000-record regional annotation frame is frozen: 600 calibration records
and 400 sealed-process records. The frame contains an 800-record probability
core and a separately marked 200-record prediction supplement drawn from 32
previously unused Kunshan-held shards. It is not a national or full-corpus
probability sample, and occupation coverage was not measured.

Job `123132130` produced the initial frame and then failed intentionally because
the 2020–22 pool had 157 eligible groups against a target of 160. Extension job
`123132322` completed the final frame. Observed overlap across the two splits was
zero for company-scrape identifier, exact normalized-text hash, and the
conservative masked-token signature. Parent/subsidiary/site harmonization and
semantic near-duplicate detection remain unverified.

Model review is diagnostic only. The planned calibration-only review uses 32
records for the primary model and a fixed 8-record subset for an independent
model-family check. No model may access the sealed-process records. No human
labels are available, so model agreement must not be reported as human accuracy
or used to claim semantic release.

At this snapshot, the model diagnostic has not been run. Git contains only this
status, code/contracts, and aggregate frame reports. Raw advertisements,
record-level selection metadata, annotations, hidden mappings, calibration
records, and sealed-process text remain outside Git.
