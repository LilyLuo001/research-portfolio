# Formal800 finite review preparation

This directory contains the frozen methods, review schema, validators, bounded
audit merge helper, and scheduled SCNet sampler/analyzer for the approved
finite review of at most 800 ads from the fixed10k frame (A/B/C 320/320/160).
Sampling, validation, weighting, aggregation, and uncertainty calculations run
only as scheduled cloud jobs. The freeze stage remains pending its separate
SHA-only exclusion transfer receipt.

The sampler fails closed when required cloud assets are absent. Private packets,
canonical keys, raw text, row-level linkage, credentials, and review outputs
must never enter Git.
