# Formal800 static analysis QA — 2026-10-12

Scope was limited to static inspection of `code/analyze_formal800.py`, `code/validate_reviews.py`, the frozen execution decisions, review instructions, methods, and JSON schema. No real-data files were opened or calculated.

## Blocking issues

None remain in the patched analysis path for the two core comparison families. Before the patch, the main comparison silently excluded `genai_traditional_overlap` even though the prereview decision defines GenAI use with or without traditional software as the GenAI arm. Missing occupation values could also be stringified to `"None"` and qualify as a common-support occupation cell. Both paths are corrected: detailed overlap remains a T3 label, while main rates/comparisons/T5 combinations use the mapped GenAI arm; `None`, `null`, empty, and `unknown` occupation values are excluded from common-support construction.

Technology precedence was also corrected so only active predictive-AI roles exclude a comparison arm, AI development/implementation is classified before predictive/background labels, and company/recruiting background mentions do not displace clear active use.

## Limitations / follow-up

The optional resolution overlay is identity-bound to the primary record and requires validator-shaped metadata, but the analysis interface has no separate validator-receipt argument for the replacement payload. A future production overlay should carry a validator receipt hash (or be validated in a separate mandatory step) before acceptance; this was not changed in the bounded pass because it would alter the frozen overlay interface.

The composition-file branch checks required columns but does not reject duplicate occupation rows or negative/non-finite composition counts. It is outside the two core comparisons and remains a delivery-time validation item.

`validate_reviews.py` correctly enforces schema, trusted packet identity, cross-field consistency, exact quote presence, and no partial-review nonmention. It does not and should not infer semantic accuracy or aggregate estimates.

The bounded `merge_formal800_audit.py` helper now requires passing receipts for both validated inputs, matches the audit set exactly to the frozen private audit packet, rejects duplicate/mismatched hidden blind IDs, compares governed mechanical signatures (including qualification alternative structure), writes private row-level differences, and prepares a root packet only from already audited contexts. It emits no final overlay until an explicit root replacement JSONL exactly covering the selected packet and a separate passing receipt are supplied. Final raw reviews mask unresolved experience/entry/duty evidence and technology inventory while preserving originals in the private difference history. The analysis entry/duty derivations now preserve unknown responsibility fields before inspecting items, and any supplied overlay is fail-closed on its own receipt/hash.

## Checks run

`python3 -m py_compile` passed for analysis, validator, and audit merge helper. Synthetic unit probes confirmed overlap maps to the GenAI main arm, background mentions do not displace active use, active AI development is excluded, missing occupation sentinels are not usable support cells, and governed signature differences are detected.
