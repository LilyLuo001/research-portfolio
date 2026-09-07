# A1 compatibility correction 01

Date: 2026-09-07

Status: **preserved failed execution; same-operation compatibility repair**

The first full SCC execution under A1 was scheduler job `7482111`. The
scheduler completed normally (`failed=0`) after 605 seconds with peak virtual
memory 1.932 GB. The application correctly returned exit status 2 and published
an immutable blocked receipt because all 11 models stopped before solver
certification with the same exception:

```text
AttributeError: module 'numpy' has no attribute 'row_stack'
```

The run used numerical specification
`yaxnumspec_v1_e0b71ceb9f1d0daf501300114234121c087d1ee145a401107fbaa2caf6df18a4`
(SHA-256
`7d5798546004e5d6804a1f1440158e4f168eb1adf54e692f93bf60df00b47cca`),
runner SHA-256
`80cbf824a5aef833fa4f748fb0a027ca50f717f08ea0467bc976102b8d1f5cc7`,
and authenticated cells SHA-256
`5e10dabf78b1b1cbc8b6aa9f8745435224b9fe3cb078e73cd9d9e27a9c292717`.
Its execution receipt SHA-256 is
`d6bd6b5d743c9510c124caeacfad5f3505bafc8cc57af972c05e75420bc7f59e`;
its `MODEL_AUDIT.json` SHA-256 is
`18869185dfecad9f546bb51609e3bbf51d8c85fdb3fef4f6fd6c218032c4fc74`.
Every model is classified
`BLOCKED_UNEXPECTED_NUMERICAL_FAILURE_NO_SUBSTITUTION`. No coefficient or
target from this run is certified.

## Authorized repair

NumPy 2.5 removed `row_stack`, an alias for vertical array stacking. The one
failing call in the problem-binding digest now uses `np.vstack` with the same
list of arrays, order, dtype conversion, contiguity conversion, and downstream
hash construction. This changes no mathematical operation, input, model,
objective, target, threshold, solver, or acceptance rule.

A regression test executes the binding routine while `np.row_stack` is
explicitly unavailable. The replacement runner SHA-256 is
`9f66a4f97ba3630fc263a06315ed5887efa99a1abf3848839d77d805d528fd8a`;
the replacement synthetic-test SHA-256 is
`94c0e8aed55cceab7ba112073937d2f9f6e30eb672413bbca4200ab3e94ce814`.
The replacement numerical specification is
`yaxnumspec_v1_5989d8d88e772711ff47c43011e9f90f4764dc8d89230ef5486b6687f59dc05c`
(SHA-256
`07d6053a5c40959f777409d269a9edbe55e5e9368992602c6b78cf1e99ce231e`).
Its scientific-target fingerprint remains the unchanged A1-parent value.

The failed execution and its classifications are retained. A replacement run
requires a fresh implementation commit and a new one-file pre-execution
authorization; it may not overwrite or reinterpret job `7482111`.
