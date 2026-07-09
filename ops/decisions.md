# decisions.md — the L3 reply channel (arch §2)
#
# Reply to digest items here, one decision per line (no leading '#'). The box
# applies them on its next cycle (`runner.py --apply-decisions`) and prefixes
# applied lines with '# applied:' so nothing runs twice. Recognized forms:
#
#     gate <TASK-ID> pass
#     gate <TASK-ID> fail
#     complete <TASK-ID>
#
# Unknown task ids are ignored (and logged). Anything else is commentary.

NEED_HUMAN (2026-07-09, E2 dual-channel conflict): FalconX Credit Vault
(AA_FalconXUSDC collateral) launch date — research plan §10 says 2025-08
(marked 已核实), but Gemini channel B answered 2025-06 backed by 34 grounded
searches (raw reply: ops/l1/out/E2-T1-facts-B.void.json). Likely an
announce-vs-mainnet-launch ambiguity. Please verify on Pareto/FalconX primary
sources and correct either the plan §10 table or e2/registry.csv notes.
The sentinel that used this fact has been replaced (unambiguous facts only).
