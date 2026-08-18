# W2 price-panel coverage against the frozen event registry

Channel B (git price table): **71** interval rows across **22** model snapshots.
Channel A (archived pricing pages): **run**.

A row reaches `verified` only when both channels agree. Everything else
stays `single_channel` or `conflict` and, per meta-rule 4, the event it
feeds stays ineligible until a human resolves it.

| Event | Registry price_status | Models | Priced models | Panel rows | Panel status |
|---|---|---|---|---|---|
| `GPT4_LAUNCH` | pending_w2 | 1 | 1 | 2 | single_channel |
| `GPT4_TURBO_PREVIEW` | pending_w2 | 1 | 1 | 2 | verified |
| `GPT4_TURBO_GA` | pending_w2 | 1 | 1 | 2 | verified |
| `GPT4O_LAUNCH` | relative_price_verified | 1 | 1 | 2 | verified |
| `GPT4O_MINI_LAUNCH` | pending_w2 | 1 | 1 | 3 | verified |
| `O1_PREVIEW_LAUNCH` | pending_w2 | 1 | 1 | 3 | verified |
| `O1_FULL_LAUNCH` | pending_w2 | 1 | 1 | 3 | verified |
| `O3_MINI_LAUNCH` | pending_w2 | 1 | 1 | 3 | verified |
| `GPT45_PREVIEW_LAUNCH` | n_a | 1 | 1 | 3 | conflict |
| `GPT41_LAUNCH` | pending_w2 | 1 | 1 | 3 | verified |
| `O3_O4MINI_LAUNCH` | pending_w2 | 2 | 2 | 9 | verified |
| `O3_PRICE_CUT` | pending_w2 | 1 | 1 | 6 | verified |
| `GPT5_LAUNCH` | pending_w2 | 1 | 1 | 3 | verified |
| `GPT51_LAUNCH` | pending_w2 | 1 | 1 | 3 | verified |
| `GPT52_LAUNCH` | pending_w2 | 1 | 1 | 3 | verified |
| `GPT54_LAUNCH` | conflict_b | 1 | 1 | 3 | conflict |
| `GPT54_MINI_NANO_LAUNCH` | conflict_b | 2 | 2 | 6 | verified |
| `GPT55_LAUNCH` | conflict_b | 1 | 1 | 3 | conflict |
| `GPT56_FAMILY_LAUNCH` | conflict_b | 3 | 3 | 15 | verified |
| `GPT56_PRICE_CUT` | pending_w2 | 2 | 2 | 12 | verified |
| `GPT56_FAST_LONG_CONTEXT` | pending_w2 | 3 | 3 | 15 | verified |

## Events with no price row in either channel

- none

These stay UNKNOWN. They are not filled by inference, and the events
they belong to cannot enter the primary stacked analysis until a dated
price row exists. That is the intended outcome, not a harvester failure.

## Known limits

- Channel B's table begins 2023-09; events before that date can only be
  priced by Channel A. `GPT4_LAUNCH` (2023-03) is in that window.
- Channel B dates are upper bounds (see `channel_git` docstring), so a
  single-channel row's interval can be wide. Only Channel A narrows it.
- Channel B is a third-party record. It corroborates; it never overrides
  an official capture.
