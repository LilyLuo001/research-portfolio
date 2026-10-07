# Ready-to-run capped compact round

The implementation is frozen before sample access. Root owns the private four-known plus sixteen-new source manifest, blind review, quality gate, and run decision. Model inference receives source text, this directory's prompt, and the compact model-output schema only; it never receives reference labels.

Use the existing pinned CPU stack only: llama.cpp commit `42b021b4dc42be573f1e1463528532fc8294c650`, `llama-completion` SHA-256 `66c94c83f239a97c458e772295c9fc556ca8ea743dbb7c704e20ffb758bd533a`, and Qwen3-8B Q4_K_M revision `7c41481f57cb95916b40956ab2f0b139b296d974`, file SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`. Do not search for another model or build a GPU runtime in this round.

Execution gates:

1. Tokenize the full rendered prompt before generation. Reject embedded NUL, prompt-plus-output overflow, and any need for context shifting. Do not truncate.
2. Run two to four known development records first, one generation per record, with raw output preserved privately. Do not retry or resample a failed record.
3. Apply `expand_and_validate.py` exactly once. It may add caller metadata and unique exact offsets; it performs no label repair.
4. Root compares the known records to existing adjudication. A repeated core object-binding, qualification-scope, or experience-versus-knowledge failure stops the round before held-out records.
5. Only after root accepts the development gate, run up to sixteen new records. Keep the total actual scheduler allocation across both phases at or below one hour. A time-limited second phase may complete fewer than sixteen records; record attempted, completed, partial, and unattempted counts.
6. No bulk run follows automatically. Root decides after quality and measured cost.

The previous full contract measured 3,891 chat-templated prompt tokens plus 1,414 generated tokens on one deliberately difficult record. It took 148.9 seconds for prompt evaluation and 289.4 seconds for generation on 16 CPU cores. The compact prompt and output should be materially smaller, but this is an unmeasured estimate. A planning range of roughly 2.5–4 minutes per record implies 50–80 minutes for twenty serial records, so all twenty may not fit the one-hour allocation. The development-first stop gate protects the budget; observed compact token counts and timing replace this estimate after the first two to four records.

The Wuzhen scheduler requests two DCU cards even though this route uses 16 CPU cores. The one-hour new-round allocation cap therefore represents at most 2 reported DCU-card-hours. Applying the provisional 2.5–4 minute range mechanically to 7,635 unique texts would require roughly 318–509 scheduler hours, or 636–1,018 DCU-card-hours at that allocation shape, before overhead. That planning projection exceeds the historical 200-card-hour entitlement and cannot support a bulk decision. The 200 hours are a historical total entitlement, not a verified remaining balance; measured compact timings and a fresh quota check are required before any later production decision.

Private artifacts must include source, rendered prompts, raw model output, tokenizer counts, inference logs, expanded valid output, and the full validator receipt. Public receipts contain hashes, aggregate counts, timing, and error categories only—never source quotes, record IDs, or raw output.
