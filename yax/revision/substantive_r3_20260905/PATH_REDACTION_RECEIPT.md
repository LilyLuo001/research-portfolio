# Public-package path-redaction receipt

Date: 2026-09-06

Scope: tracked files under `yax/revision/substantive_r3_20260905/` only. The
pass replaced 162 occurrences across 45 pre-existing tracked files. It did not
change numerical results, stored hashes, or scientific claims.

Replacement classes:

- Public shell runners now take the writable compute root from
  `YAX_SCC_PROJECT_ROOT` and the restricted input root from
  `YAX_PRIVATE_ROOT`.
- `YAX_REPO_ROOT` may select a clean worktree; `YAX_PYTHON_BIN` may select the
  interpreter and otherwise defaults to `python3`; and
  `YAX_LEGACY_PYTHONPATH` is optional.
- Documentary records, JSON receipts, historical logs, and manifests use
  explicit angle-bracket placeholders such as `<YAX_SCC_PROJECT_ROOT>`,
  `<YAX_PRIVATE_ROOT>`, and `<YAX_PYTHON_BIN>` rather than user-specific
  absolute roots.
- Local referee-report and execution-prompt locators use stable
  `<SUPPLIED_INPUT:...>` labels. Their previously recorded content hashes are
  unchanged.
- Scheduler `-o` directives containing an absolute user-specific path were
  removed because scheduler directives do not portably expand shell
  variables. A caller may provide an output path at submission time.

The original operational paths remain in private execution history outside
the public package. Reproduction requires the corresponding restricted inputs
to be supplied through the documented environment variables; no private data
were copied into this directory.

Validation: a recursive scan of this directory finds no literal personal
absolute root beginning with the former project-volume, user-home, or local
desktop prefixes.

After SCC job 7471585 extended the endpoint grid, its regenerated dynamics
receipt was passed through the same rule before inclusion: two restricted-input
locators were restored to `<YAX_PRIVATE_ROOT>`.  The final dynamics self-check
then passed with the redacted receipt and unchanged statistical-artifact
hashes.
