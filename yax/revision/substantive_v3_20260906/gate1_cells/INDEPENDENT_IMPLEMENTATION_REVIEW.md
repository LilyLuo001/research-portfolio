# Independent implementation review

Review date: 2026-09-06

Reviewed builder SHA-256: `4ed76f7a570e785202b3cbd1b13953e5986d9461abd1e1191ba189507b0903c4`

Disposition at that hash: **PASS, conditional only on the declared terminal consumer/spec restamp**

After that review, one narrow semantics correction changed the builder to
`38c528dd45b8f932100a78d751bc7b513e4e6596e1d635401dd4b73660bccfc3`:
zero, unit, and strictly fractional bridge contributions are now classified by
exact comparisons, and any route weight outside `[0,1]` is rejected. The
full producer suite is 20/20 passing. An independent reverse application of
the four-line change reproduced the previously reviewed SHA byte-for-byte, and
boundary tests verified the current classification. **The PASS therefore
extends to the current SHA.**

The review found no remaining P0 or P1 defect in the aggregate-cell producer.
It independently checked that:

- production imports only the standard library, NumPy, and pandas and does not
  execute the historical analysis modules;
- the exact six-field, ages-22--65 target router matches the byte-locked
  inherited target on the supplied fixture and on an additional adversarial
  fixture containing positive-weight replaced March records, excluded ages,
  unmatched routes, and split bridges;
- the parity test loads only the byte-locked historical constants and three
  target functions into a controlled namespace rather than importing the
  historical dynamic closure;
- per-source and total record identities cover physical rows, eligibility,
  valid/invalid occupation records, early/current routes, matched/unmatched
  early records, expanded/direct contributions, and fractional/unit/zero route
  weights;
- weighted-stock conservation is checked separately by source and in total;
- command, runtime, Git, and committed-blob provenance and receipt sanitization
  are fail-closed; and
- the numerical consumer recomputes the producer accounting identities and
  authenticates the cell spec, Git state, committed files, command, runtime,
  and six-field build flags.

The reviewer obtained 16/16 passes on the non-placeholder producer tests and
2/2 passes on targeted consumer receipt/accounting tests. The remaining stale
hashes and IDs are the explicit fail-closed placeholders reserved for the
terminal cross-spec restamp; they are not treated as executed or validated.

After the terminal restamp, all 20 producer tests passed. One nonbinding edge
is retained transparently: the standalone bridge loader's `1e-12` mass
tolerance could accept an unused route one floating-point unit above one, and
pandas' declared parser maps textual `0.9999999999999999` to `1.0`. Neither
can affect this production run because bridge bytes and runtime are
authenticated; the canonical 595-row bridge has minimum weight `0.0036`,
maximum `1.0`, 447 exact-unit weights, 148 strict-fraction weights, and no
out-of-range value or parser/round-trip classification change.
