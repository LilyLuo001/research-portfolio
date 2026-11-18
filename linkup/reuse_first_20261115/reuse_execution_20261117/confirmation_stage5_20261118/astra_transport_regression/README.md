# Astra transport regression — unapplied proposal

**Astra diagnostics are NOT complete.** The six authorized physical attempts are exhausted: six HTTP 400 input-validation rejections, zero model outputs and zero completed field validations. Six accounted denominator slots are not six successful outputs. This repeats the documented historical Responses `json_object` transport defect; it is not evidence of model failure or comparative model quality.

No recovery calls, retries, launches, cap reset or runtime edits are authorized by this package. No provider call or cloud command was made while preparing it. Original evidence and the current cap of six remain unchanged. Historical recovery permission and historical cap changes do not apply here.

## Minimal proposal

1. Prefix Astra Responses `input` with literal `Return JSON.\n`. The original UTF-8 source JSON remains the exact suffix; schema, instructions, deployment, effort, output limit and all other payload fields are unchanged.
2. Stop admissions after the first non-filter Astra HTTP 400. This is a conservative stop, not a claim that every 400 has the same cause. Existing provider-filter quarantine, authentication stops and confirmed-retry rules remain intact.

**The patch is UNAPPLIED.** Its exact bytes are reproduced below for the public publisher, which accepts Markdown but not `.patch` files.

Original file: `ASTRA_TRANSPORT_FIX_UNAPPLIED.patch`  
SHA-256: `f2f633d78303be293f6c9a8864c7c6078c256f44a4299aa3ea95941f959c30b0`

```diff
--- a/runtime/stage5_common.py
+++ b/runtime/stage5_common.py
@@ -295,7 +295,7 @@
     system = NOTICE + (Path(directory) / "INSTRUCTIONS.md").read_text() + "\nFrozen JSON schema:\n" + (Path(directory) / "SCHEMA.json").read_text()
     if leg == "Astra":
         return dict(model=p["deployment"], store=False, instructions=system,
-                    input=encoded(row).decode(), max_output_tokens=p["output"],
+                    input="Return JSON.\n" + encoded(row).decode(), max_output_tokens=p["output"],
                     reasoning={"effort": p["effort"]}, text={"format": {"type": "json_object"}})
     return dict(model=p["deployment"], messages=[{"role": "system", "content": system},
                 {"role": "user", "content": encoded(row).decode()}],
--- a/runtime/stage5_cloud_worker.py
+++ b/runtime/stage5_cloud_worker.py
@@ -123,7 +123,7 @@
                         if state == "retryable_confirmed_http" and ledger.latest(case)["attempt"] < 2:
                             continue
                         carrier["status"] = state
-                        stop = status in (401, 403)
+                        stop = status in (401, 403) or (args.leg == "Astra" and status == 400 and not filtered)
                         break
                     view = visible_view(args.leg, parse_json(raw))
                     detail.update({k: view[k] for k in ("returned_model", "usage", "complete", "filtered", "refusal")})
```

## Offline verification and limits

- 13 tests passed. They reuse the existing runtime fixture and cap-six test; no runtime copy is stored.
- Proposed modules are compiled only in memory. Synthetic sources, validators, ledger, identity token and HTTP responses live only in test temporaries; socket connections are blocked.
- In-memory modules deliberately retain original filenames for the reused fixture's hash checks. This is not a deployable pinned runtime or evidence that a patched deployment would be admitted.
- Tests cover exact source suffix bytes and unchanged other payload fields; protection before body access; unchanged Luna/Kimi behavior, policy, rates and budgets; one synthetic 400 then five unprocessed slots; filter quarantine; authentication stop; confirmed retry; and the unchanged physical cap of six.
- All 17 original runtime files (including existing bytecode) and four public evidence receipts hash-match the before snapshot. The standalone patch and this fenced copy also match exactly.
- These results do not establish provider acceptance, completed diagnostics, scoring qualification, production admission, or authority to make another request.

Run only the offline regression from this directory: `PYTHONDONTWRITEBYTECODE=1 python3 -B test_astra_transport_regression.py`.

Evidence: `ORIGINALS_BEFORE_PUBLIC.json`, `REGRESSION_PUBLIC.json`, and the saved `OFFLINE_TEST_RESULTS.txt`. Public receipts contain metadata and hashes only, not source rows, model output bodies, credentials, or record identities.
