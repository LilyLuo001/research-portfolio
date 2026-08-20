# DAX W4 capability/cost capture

This directory implements the private measurement boundary for W4. Git carries
the schema, harness, frozen vintage registry, tests, and sanitized aggregate
receipts. It must never carry task text, prompts, raw responses, item outcomes,
private panel rows, API keys, encryption keys, checkpoints, or cost ledgers.

## Hard gates

Full capture is disabled until all of the following exist and agree:

1. the exact pushed `task/DAX-w3-mapa-execution-20260819` commit and a receipt
   with `PASS_TASK_IDS_ONLY`, adjudication `PASS`, mapping SHA-256, and row count;
2. authorized frozen per-task duration metadata (missing duration blocks the
   row; it is never inferred or constant-filled);
3. account-scoped model-list metadata confirming the exact measurement model;
4. `dax/capability_panel/budget_ceiling.json` with `status: PI_SIGNED`, a
   positive `usd_ceiling`, signer, and timestamp.

Without gate 4, only an explicitly invoked smoke mode may reserve at most USD
5 in aggregate. The current preflight has no API key and therefore spends USD
0. Project/provider alerts are not treated as hard stops; the harness reserves
cost atomically in SQLite before every request.

`gpt-4.5-preview` is excluded. Retired models use only the filed open-weight
stand-ins. Undated current aliases are blocked unless a separately approved,
cited alias-to-snapshot rule is added; listing an alias in current API docs is
not permission to rewrite history.

## Private SCC locations

- expected key file: `/usr3/graduate/qluo/dax-private/w4/.env`, mode `0600`;
- variable names: `OPENAI_API_KEY` and `DAX_W4_ENCRYPTION_KEY`;
- encrypted prompts/responses, task-ID manifest, checkpoints, and budget DB:
  `/usr3/graduate/qluo/dax-private/w4/` (mode `0700`).

The availability command reads the key inside its process; the value never
appears in argv:

```bash
python -m dax.capability_panel.availability \
  --registry dax/capability_panel/vintage_registry.json \
  --env-file /usr3/graduate/qluo/dax-private/w4/.env \
  --output dax/data_raw/w4_availability_audit_receipt.json
```

The official OpenAI Models endpoint returns account-scoped availability
metadata. The retirement schedule is pinned in the registry to the official
deprecations section. Reasoning tokens are recorded separately but not added
again to billed output tokens, following the official Responses accounting
guidance.
