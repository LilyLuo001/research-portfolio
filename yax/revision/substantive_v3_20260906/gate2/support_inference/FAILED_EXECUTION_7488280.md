# Gate 2 support-inference failed execution 7488280

This is the permanent record of the third authorized Gate 2
support-inference attempt. It is a failed pre-fit command-binding attempt, not
a numerical or scientific result.

- SGE job: `7488280`
- Run ID: `gate2_support_inference_sge_7488280`
- Implementation commit: `6497ef55fded6c5ef68e62721b2e624530c0724d`
- Authorization commit: `068037925bc094420a878669c674663d5cd88f99`
- Authorization ID:
  `yaxgate2supportauth_v2_1907ef4fdc1d06fb13d7c18d18aa453792a9a35a41da8ca4580e95ba46455fa7`
- Authorization SHA-256:
  `6b28d9583b08bd5249bc92063887dc45c89b78f3bdd54436bad7a8de5e8b6310`
- Run-identity ID:
  `yaxgate2runidentity_v1_fe5756fc896fcc7f410720f8568333c6dba29fd1ddc538dc4c1d9ccc1ac3f12a`
- SCC host/queue: `scc-gr4.scc.bu.edu` / `econ`
- Start/end: `2026-09-07 21:40:16` / `2026-09-07 21:40:19` (SCC time)
- Accounting: `failed=0`, application `exit_status=2`, wall clock 3 seconds,
  maximum memory 452.086 MB
- SCC evidence directory:
  `/projectnb/econdept/qluo/yax-v3-gate2-support-runs-6497ef5`
- `sge.err` SHA-256:
  `8d669bd84ade33f6064055743ffc9d317535a317cb778c46b532038e024ba4e4`
- `sge.out` SHA-256 (empty):
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

The runner failed closed before fitting any model, but not before reading the
aggregate cells, with:

> BLOCKED: pre-execution authorization run binding differs

No result receipt, failure-evidence leaf, or scientific output was created.
The SCC evidence directory is retained unchanged.

The implementation at `6497ef5` called `authenticate(args, spec)` before
`execution_provenance(...)`, and the latter was the first call that validated
the committed pre-execution authorization. Consequently, the hash-pinned
aggregate-cells file and receipt were opened and authenticated before the
command-binding mismatch blocked execution. This ordering defect does not
change any scientific result—no fit began—but it invalidates any claim that
this failed attempt read zero protected aggregate outcomes. The subsequent
implementation moves committed authorization validation ahead of every
aggregate-cells or cells-receipt read and retains the later full-provenance
revalidations.

The authorization bound the support matrix, support edges, and direct-tail
membership files inside the exact authorized Git checkout. Those files remained
present and retained their authorized path hashes, devices, inodes, and content
hashes. The submitted job instead named byte-identical copies from the
authoritative support-accounting output directory. Content identity therefore
held, but the stricter authorized command-path identity correctly failed.

The authorization committed at `0680379` was single-use and is preserved in
Git history. It is removed from the subsequent implementation state. Any retry
requires a new held SGE job, output-parent identity, authorization document,
authorization commit, and run ID. The retry must derive both authorization and
execution arguments from one retained machine-readable manifest rather than
separately transcribed path lists.
