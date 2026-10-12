# Publicity check

Checked 2026-10-12, bounded to the new `linkup/corpus_release_20261012/` tree, its public aggregate reuse CSV/JSON artifacts, `linkup/formal800_20261012/METHODS_ESTIMANDS.md`, and `linkup/retrospective_20261012/ARTIFACT_REUSE_AUDIT.md`. No raw advertisement text, row-level data files, private catalogs/views, credentials, or secret values were found in the intended release artifacts. Public aggregate old-CSV reuse is within scope.

Relative Markdown links sampled across the release and both changed documents resolve to existing repository paths, including the release receipts, public schema, reused aggregates, Formal800 receipts, and retrospective references.

Concrete packaging issue: two compiled Python bytecode files are present under the new release tree and should be excluded before publication:

- `linkup/corpus_release_20261012/__pycache__/build_corpus_release.cpython-310.pyc`
- `linkup/corpus_release_20261012/weights/__pycache__/audit_sample_weight_lineage.cpython-310.pyc`

No other issue was identified in this bounded check. No cloud jobs, research data, or Git state were modified.

Root packaging resolution,2026-10-13: a release-local `.gitignore` excludes both bytecode directories/files, private artifacts and Parquet data. Only public source, documentation, aggregates and receipts are staged for publication; no cache deletion was needed.
