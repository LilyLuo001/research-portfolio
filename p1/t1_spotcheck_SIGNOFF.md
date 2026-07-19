# P1-T1-spotcheck — Human Gate 1 SIGNED OFF (owner, 2026-07-18)

The owner completed multiple verification rounds over events_merged.csv:
1. Gate-1 spotcheck (57-row sample) — caught 9 ETF-to-ETF false positives.
2. Full manual re-review of all events — 5 not_event, 1 no_event→event,
   96 recheck, 11 no_event flags (owner_full_review.csv).
3. Full-text recovery sweep (deepseek v4-pro, box): date recovery + target-type
   confirmation + re-categorization → **131 confirmed conversions** on main
   (commit 1de3532), contract PASS.

Owner instruction 2026-07-18: "I have recheck and reverify the events ...
proceed to the next step of P1." → Gate 1 PASS. events_merged.csv (131) is the
frozen T1 event set feeding P1-T2-wrds.
