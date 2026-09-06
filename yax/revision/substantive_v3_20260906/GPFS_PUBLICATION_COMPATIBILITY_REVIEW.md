# Final GPFS publication compatibility review

Review date: 2026-09-06 UTC.

The first protected SCC attempt failed closed before publication because the
mounted GPFS filesystem returned `EINVAL` for Linux
`renameat2(RENAME_NOREPLACE)`. No scientific output from that failed attempt is
treated as executed, transferred, or validated.

The terminal implementation attempts kernel no-replace first. An explicit
unsupported-filesystem result permits a same-parent atomic ordinary rename only
under an exclusive cooperating-publisher sibling lock, after lock-identity,
staging-identity, and immediate target-absence checks. This fallback is not
represented as kernel no-replace. It retains a bounded noncooperating same-user
empty-directory check-to-rename race. The durable numerical receipt discloses
both permitted paths before publication; the numerical runner attempts to emit
the actual backend after commit. Postcommit destination probes were removed,
cleanup failures are advisory and reported, and output-stream failures cannot
turn a committed leaf into a nonzero retry signal.

## Terminal bindings

- canonical spec ID:
  `yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3`;
- numerical spec ID:
  `yaxnumspec_v1_4c784c23726ad5ce258af6151afdf83e1e05efe6d1086d43007e5d06a5843991`;
- numerical spec SHA-256:
  `152cb4b5a27ff168a0bcfae898ac68b479fb2ae4ae2c811722a145560fc6b2ce`;
- cell spec ID:
  `yaxcellspec_v1_e08b69694a4ebb0b15919b6af989cca98cea9e86eea80ef252f93b5cfccaa08b`;
- cell spec SHA-256:
  `09f49d3f459fd532dd37f76dfd111fc0c0a7aa10e1fffe869b08596cad665a15`;
- target spec ID:
  `yaxtargetspec_v1_e0598066c90d6b7efad743ea68e074b5be2b455fb12eddf4b998430c0081b83b`;
- target spec SHA-256:
  `fa425dce6d75475b6f562aba52898b8e71c7db0269d549f17ef9645720052651`.

Terminal code SHA-256 values:

- cell runner: `70b9bf3d756536a9d5bf38938235b84a83d9d1a8defcc3dbecb5c19b6916bc34`;
- target runner: `b62cfd28c71d7c7a933158ba4afefec0fa314be4b1f6bd4d205a0991088e80b9`;
- numerical runner: `23f4a4dd70fb1ff5798405248fb742a07e4204a0a42bff9d9e24ad816f47df02`;
- numerical artifact safety: `6c03ad94fb5d4ecb618e3cd0e4f9de6ece0a5f20e633283002f3fc01d1248fd2`;
- transfer normalizer: `e4652c023262b3d924c9b940074cb6b4cc9cd8416fff49e39ea15114c309177f`;
- transfer template: `1cbb5f08bbf2f6d9c63fc2d32368db8bccdfa67fc4a3c4cf94084bb2b1a1da76`.

## Validation and disposition

The integrated focused suite passed 263 tests and 17 numerical subtests. The
complete repository suite passed 1,057 tests and 17 subtests, with three
documented skips. An independent final review separately passed 280 tests and
17 subtests: 29 cell, 47 target, 75 numerical plus 17 numerical subtests, 118
transfer, and 11 cross-spec contract tests.

The reviewer independently recomputed all self-identifiers, cross-spec
bindings, relevant code and source-evidence hashes, and transfer
constant/template bindings to live repository bytes. No P1 or P2 defect
remained. The earlier cell, target, and numerical implementation reviews are
retained as explicitly superseded historical records.

Disposition: **PASS for a freshly authorized protected SCC execution.** This
is an implementation disposition only. Protected empirical Gate-1 outputs
remain unvalidated until the replacement execution and terminal transfer gates
complete.
