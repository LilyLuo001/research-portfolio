# YAX Phase 3 protected-reference audit

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.**

Audited before opening any new Phase 3 quantitative result. Phase 3 parent: `3feda26c698b19823d3370eecb3abf2a57ad9cfd`.

## Protected tags

| tag | `git rev-parse <tag>` | `git rev-parse <tag>^{}` | object type | previously frozen peeled commit | result |
|---|---|---|---|---|---|
| `v1.1-design-freeze` | `74d97a9b07e0cbedda2c646c5eed5938b8506f81` | `22fbf7924809b7a535e31ae0ab68f5b113ce8078` | annotated tag | `22fbf7924809b7a535e31ae0ab68f5b113ce8078` | PASS |
| `v1.1-confirmatory-results` | `31f9d02352f70fe81f5a01cd6690cc5e5400512c` | `b16109482c3bf5ca176f6f08976e120b04769945` | annotated tag | `b16109482c3bf5ca176f6f08976e120b04769945` | PASS |

The apparent discrepancy is exactly the annotated-tag object SHA versus the peeled commit SHA. It is not ref movement. The peeled commits agree with the design receipt, confirmatory audit, manuscript provenance receipts, and Phase 1/2 receipts already in the repository.

## Other immutable baselines

- V4.1 completed baseline: `ca5a02478b68f1a0e47eadd4e8816bbc96c9dcc3`.
- Phase 2 final seal: `9772a494afc2c1af5630979631c4b67640f4ff3f`.
- Phase 2.5/Gate 3 final seal and Phase 3 parent: `3feda26c698b19823d3370eecb3abf2a57ad9cfd`.

No protected underlying commit changed. The Phase 3 integrity gate therefore passes. Protected confirmatory outputs and the V4.1 manuscript baseline may be read as immutable inputs but may not be edited.

