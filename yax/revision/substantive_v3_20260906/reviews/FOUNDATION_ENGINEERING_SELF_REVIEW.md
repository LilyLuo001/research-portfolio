# Foundation engineering self-review

Review role: execution-agent self-review, not independent scientific review  
Reviewed: 2026-09-06

The executable checks cover four distinct failure classes:

- canonical JSON and immutable `spec_id` construction, including changes to
  endpoint, age group, objective, and membership;
- explicit incompatibility failure when modules receive different required
  contract fields;
- run-DAG fingerprints that bind code, environment, command, specification,
  upstream result IDs, upstream artifact hashes, and output hashes; and
- numerical claims that must resolve to a hashed result object and a unique
  declared canonical target.

Regression tests deliberately tamper with specifications, commands, upstream
hashes, source numbers, and manuscript-claim values and require failure. They
also retain a failed branch while allowing an unrelated successful branch.

Limits: the empty initial run and claim ledgers validate their schemas but do
not establish that later empirical modules use them. G06 and G07 therefore
remain implemented but unverified until real dependent runs and manuscript
claims populate those ledgers. The stamped baseline contract is an actual
nonempty specification and is eligible for G05 verification after the receipt
and ledger dependency checks pass.
