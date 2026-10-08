# Wuzhen active-artifact migration scope

This migration preserves the complete active execution state under the four
required directories: code, schemas, prompts, receipts, aggregates, historical
labels and predictions, small exact-text queues, and their sampling/source
mappings. Historical labels and predictions retain their local/Codex
provenance and are not evidence of cloud inference.

The first transport archive excluded six queue/source-map filename classes.
That archive and its job are classified as partial preservation. A supplemental
archive restores every excluded active file at its original relative path, and
the final scheduled job verifies the union manifest. Only Python/pytest caches,
model weights, unrelated original attachments, and the external massive raw
Parquet corpus remain excluded.

The scheduled Wuzhen job performs only SHA-256 transport verification and
required-directory/exclusion checks. It performs no LLM inference and makes no
production-completion claim. Private SSH connection details remain outside
this directory and outside Git.
