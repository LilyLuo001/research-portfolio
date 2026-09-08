# Gate 2 support-inference failed execution 7483995

This is the permanent record of the first authorized Gate 2 support-inference
attempt. It is a failed pre-fit producer/consumer-handshake attempt, not a
numerical or scientific result.

- SGE job: `7483995`
- Run ID: `gate2_support_inference_sge_7483995`
- Implementation commit: `b3ae5bd33e5b3835f8ef4bbfe2fbbaf197b06344`
- Authorization commit: `b79b0fe69e00a16040a23f325aab083a095cb099`
- Authorization ID:
  `yaxgate2supportauth_v2_ee441112f656eb7091f95f777515a324b17af0365c775e6eec95e3add679a524`
- Authorization SHA-256:
  `fabab73cb831973aed76adbd74e81ce17c312076382eb447311b92595f8501c0`
- SCC host/queue: `scc-gr4.scc.bu.edu` / `econ`
- Start/end: `2026-09-07 13:28:11` / `2026-09-07 13:28:22` (SCC time)
- Accounting: `failed=0`, application `exit_status=2`, wall clock 11 seconds,
  maximum memory 454.273 MB
- SCC evidence directory:
  `/projectnb/econdept/qluo/yax-v3-gate2-support-runs-b3ae5bd`
- `sge.err` SHA-256:
  `92934c53b9db302c7bfbb76d719672e8d1af389a12f0b31cbe54e98e72559b43`
- `sge.out` SHA-256 (empty):
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

The runner failed closed before fitting any model with:

> BLOCKED: cell assignment fingerprint does not reproduce its receipt

No result receipt or scientific output was created. The SCC evidence directory
is retained unchanged.

The cause was a representation mismatch in the consumer handshake. Gate 1
created the exact fingerprint from pre-serialization fixed-membership Webb
values. Gate 2 separately confirmed that aggregate-cell Webb values matched
those values within the signed `1e-12` absolute tolerance, but then tried to
recreate the byte-level fingerprint from the CSV-round-tripped cell floats.
A sub-tolerance last-bit representation change therefore caused a false block.

The repair leaves all scientific inputs, assignments, estimands, models, and
tolerances unchanged. It reconstructs the exact producer fingerprint from the
authenticated fixed-membership quintile/Webb values and stable cell family
assignments only after the original exact-quintile and `1e-12` Webb semantic
checks pass. A regression test now requires sub-tolerance floating-point
representation drift to pass and above-tolerance semantic drift to block.

The authorization committed at `b79b0fe` was single-use and is preserved in
Git history. It is removed from the subsequent implementation state. Any retry
requires a new held SGE job, output-parent identity, authorization document,
authorization commit, and run ID.
