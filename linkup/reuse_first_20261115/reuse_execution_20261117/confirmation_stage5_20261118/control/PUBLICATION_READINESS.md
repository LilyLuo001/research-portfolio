# Stage5 outcome publication readiness

`publish_stage5_outcomes.py` is a separate explicit-file extension. Its default
operation is a read-only dry-run. It never stages, commits, pushes, calls a
model, or changes Azure. The original publisher and working source files remain
unchanged. Repaired runtime sources publish under `runtime_transport_v2`; the
original `runtime/`, initial delivery manifest, and initial status remain intact.

The fixed source table includes the six repaired runtime executables, their
transport test and required original synthetic fixture, the repair receipt,
README and original-source hash baseline, both controllers, Luna completion,
the original Kimi incident, Kimi v2 prepare/launch/final, future scoring and
Astra aggregate receipts, the progress snapshot, and the scoring adapter and
handoff, and the confirmed Astra diagnostic comparison/test/readiness files.
Missing files are reported, not treated as completed work. Nothing is
admitted through a source-directory glob. Every dry-run computes a plan SHA
bound to the exact source, rendered output, and scanner bytes.

Python loopback string spelling uses the same octal-dot convention as the
existing publisher. The extension additionally requires the entire Python AST
to remain equal. Raw strings that would change value are refused. Credentials,
record hashes, non-loopback addresses, and unreviewed UUIDs cannot be exempted.
Only the existing fixed deny-marker UUID and explicitly scoped operational
paths may receive exact file-SHA, line, rule, and literal-SHA exemptions.
Receipt paths and that deny marker are redacted; numeric aggregate values stay
unchanged. Extra JSON checks reject complete source documents, context hashes,
canonical keys, source-row values, case identifiers, response content, and
credentials even where the repository's lightweight scanner has no rule.

Completion receipts must be terminal and account for their selected slots.
Luna and Kimi roster hashes and selected counts must agree when both are
included. This is an accounting check, not semantic acceptance. The generated
outcome summary does not infer qualified fields or release a pilot. The original
Kimi incident is preserved separately from any later v2 final receipt.

Run the publisher's in-memory synthetic checks:

```sh
python3 -B control/publish_stage5_outcomes.py --self-test
```

Then run a read-only plan from the Stage5 working directory:

```sh
python3 -B control/publish_stage5_outcomes.py
```

After source review and once runtime files are stable, the root can invoke
`--apply --expect-plan-sha <the-current-dry-run-digest>`. A changed source or
scanner produces a different plan and blocks use of the old digest. `--only`
may restrict publication to a subset of the fixed names, but cannot introduce
new source files. Apply updates only these exact output paths and their
allowlist/exemption entries. It does not automatically stage anything.

The root should run the relevant repaired-transport tests before publication:

```sh
python3 -B -m unittest discover -s runtime_transport_v2 -p test_stage5_transport.py -v
python3 -B -m unittest discover -s protocol -p test_cloud_score_adapter.py -v
```

From the repository root, scan the resulting public tree, then stage only
the reviewed explicit paths and repeat the staged check:

```sh
python3 -B linkup/reuse_first_20261115/scan_public_git.py
python3 -B linkup/reuse_first_20261115/scan_public_git.py --check-staged
```

The repository scanner writes its derived scan receipt, so it is deliberately
not run by this preparation task. Its pure detector self-tests and each planned
copy are checked in memory. Scanner success supplements explicit review; it is
not a proof against arbitrary secrets or semantic mistakes. No public copies,
allowlist changes, Git changes, or full repository scan are claimed here.

Observed preparation checks: the publisher's eight in-memory tests and the
existing scanner's eight detector tests passed. Planned copies passed text and
JSON scans. The repaired transport's twelve offline synthetic tests passed
using the command above; it opens no sockets or provider sessions. The repair
controller's generated cloud-import source also compiled with fake transport
metadata and a fake VM interface, without executing cloud code or reading real
private files. Files still evolving require a fresh dry-run before apply.

The controller audit found its pre-launch zero-call and new-pin checks
consistent: old terminal/accounting/output SHA and empty admission tables are
checked; old pinned scientific files are copied unchanged; only six code pins
change; runtime loading verifies those pins plus predecessor and protection
bindings. Before upload, also compare the live repaired code to the saved v2
code pins, because bundling later-edited code would fail validation after import.
