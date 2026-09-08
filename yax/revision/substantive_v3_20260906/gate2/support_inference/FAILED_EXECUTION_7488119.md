# Gate 2 support-inference failed execution 7488119

This is the permanent record of the second authorized Gate 2
support-inference attempt. It is a failed pre-fit producer/consumer-handshake
attempt, not a numerical or scientific result.

- SGE job: `7488119`
- Run ID: `gate2_support_inference_sge_7488119`
- Implementation commit: `0c11f5a488ef6bf1f7b0f7dc35ddc4dba2590746`
- Authorization commit: `888bd2b98af7ab98802ef62d88d256159cd09904`
- Authorization ID:
  `yaxgate2supportauth_v2_8910abb092f6cf68d7068b6d09d926fe1564b5d33502a1916c7e501d646cff69`
- Authorization SHA-256:
  `6ac872924eedf823691196de76927f39f1ce0ca659099e33f0508c3d9bee942a`
- Run-identity ID:
  `yaxgate2runidentity_v1_074c764b70f341f4e4f987bef8cfa8965544ace637431b1e1e547b7c84b85ebb`
- SCC host/queue: `scc-gr4.scc.bu.edu` / `econ`
- Start/end: `2026-09-07 21:11:24` / `2026-09-07 21:11:27` (SCC time)
- Accounting: `failed=0`, application `exit_status=2`, wall clock 3 seconds,
  maximum memory 452.055 MB
- SCC evidence directory:
  `/projectnb/econdept/qluo/yax-v3-gate2-support-runs-0c11f5a`
- `sge_retry.err` SHA-256:
  `92934c53b9db302c7bfbb76d719672e8d1af389a12f0b31cbe54e98e72559b43`
- `sge_retry.out` SHA-256 (empty):
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

The runner failed closed before fitting any model with:

> BLOCKED: cell assignment fingerprint does not reproduce its receipt

No result receipt or scientific output was created. The SCC evidence directory
is retained unchanged.

The preceding repair selected the correct semantic source for each fingerprint
field, but its fixed-membership input still used pandas' default float parser.
Gate 1 parses the fixed-membership CSV with `csv.DictReader` followed by Python
`float()`. On the authenticated public membership file, pandas' default parser
produces a different `float.hex()` value for 95 of 468 Webb values (maximum
absolute difference `2.220446049250313e-16`). Pandas' `float_precision="round_trip"`
reproduces all 468 producer values bit-for-bit. The consumer now uses that
round-trip parser and a regression test verifies both the original mismatch and
the exact repaired agreement using the hash-pinned public membership file.

The authorization committed at `888bd2b` was single-use and is preserved in
Git history. It is removed from the subsequent implementation state. Any retry
requires a new held SGE job, output-parent identity, authorization document,
authorization commit, and run ID.
