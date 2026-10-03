# L2 measurement status — 2026-10-04

## Completed locally

- Versioned extraction schema and model/agent prompt are frozen at `v1.0.0` for this scaffold.
- JSON Schema validation plus semantic checks enforce exact source spans, object/duration binding, alternative-branch representation, and state separation.
- Development and evaluation preparation commands accept real local JSONL or Parquet text, audit exact locators and readability, and write private packs outside `measurement/`.
- The development route can materialize the frozen D25 two-configuration 80 only from L1's exact 80-key manifest; it never redraws that subset.
- Offline prediction import, validation receipts, local text-length/token-proxy receipts, and a hard unavailable batch gate are implemented.
- One synthetic suite passed all eight checks. It includes intentional bad offsets, unbound years, zero-filled negative/unresolved cases, misuse of `develop_train` for AI-assisted software writing, exact config80 manifest use, and evaluation-lock refusal.

## Real-input status

Selection job `123581861` subsequently failed after four seconds on a DuckDB file lock. Recovery job `123582600` uses isolated output and temporary database directories; its last observed state was pending for priority. See `../linkup_sample/EXECUTION_STATUS.json` for the dated observation. No core sample receipt or 200 materialized texts is yet available. Provisional keys are not final, and there is no background text materialization.

After selection, the next operator must run the supplied regional adapter/materializer to produce the 200 development rows using `JOB_HASH + SOURCE_FILE + SOURCE_ROW`, verify the source schema, and provide the actual text-column name plus its config80 manifest. At that point run `prepare` and `cost` from `README.md` to create the 200-record readability receipt and private 80-record comparison pack.

## Explicitly not completed

- No real 200-record text/readability receipt or 80-record private text pack exists yet.
- No model labels were generated and no configuration comparison was run.
- No evaluation set was revealed.
- No external or paid API call occurred. Batch API status is `unavailable_no_api`; production L3 has not started.
