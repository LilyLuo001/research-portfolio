# P1-T13 — ANT semi-transparent control set: dual-channel arbitration

_Seat C, 2026-08-19. Produced during the P0-1 state reconciliation, when both
channel outputs were found sitting in `ops/l1/out/` unregistered and undiffed._

## Why this file exists

`P1-T13-ant` (kimi) and `P1-T13-ant-B` (qwen) are a dual-channel pair under
CLAUDE.md meta-rule 2 — different vendor families, machine-diff, **third model +
human on splits**. Both produced output. The diff had never been run, so neither
channel could honestly be marked complete: doing so would have ratified an
un-arbitrated extraction, which is exactly the half-enforcement meta-rule 2 exists
to prevent.

## The diff

Both channels covered the **same 414 accessions** — no coverage gap in either
direction.

A naive equality diff reports 323 splits, but that is an artifact: channel A
returns a JSON *string* where channel B returns a JSON *object*, and the two
channels use different enum casing (`"Proxy Portfolio"` vs `proxy_portfolio`).
The comparison below normalises both before judging — parse A's strings, then
lowercase / underscore the enum values.

| | count | share |
|---|---:|---:|
| Agree after normalisation | 287 | 69.3% |
| **Substantive split** | **127** | **30.7%** |
| — `no_event` vs classified | 43 | 10.4% |
| — `proxy_basket_type` differs | 84 | 20.3% |
| — `disclosure_regime` differs | 0 | 0% |

Split table: `p1/t13_ant/t13_channel_diff.csv` — one row per disagreement, with
both channels' answers and empty `resolution` / `resolved_by` columns for the
arbitration lane to fill.

## Reading the two failure modes

**`no_event` vs classified (43).** Channel A says the filing carries no ANT
event; channel B classifies it as `semi_transparent` with
`proxy_basket_type = "na"`. This is an *existence* disagreement, not a labelling
one, so it is the more serious of the two — it changes the size of the control
set. Note B's `"na"` basket type is itself weak: it asserts a regime while
declining to name the mechanism, which is the shape of a guess.

**`proxy_basket_type` differs (84).** Both channels agree the filing is
semi-transparent but disagree on the mechanism — e.g. `proxy_portfolio` vs
`factor_model_based`. Since T13's purpose is a *semi-transparent control set*,
these 84 do not threaten membership, only the mechanism sub-label. If the design
only ever keys on `disclosure_regime`, they are non-blocking; if any spine or
robustness cut keys on basket type, they are blocking. **That is a design
question, not an extraction question** — see the NEED_HUMAN below.

`disclosure_regime` never differs where both channels see an event, which is
mild evidence that the regime call is the robust part of the extraction and the
basket-type call is the fragile part.

## Status

`NEED_HUMAN: P1-T13 dual-channel split at 30.7% (127/414). Meta-rule 2 requires a
third model + human adjudication on splits; the third channel needs the L1 lane,
which has been dead since 2026-07-10. Neither P1-T13-ant nor P1-T13-ant-B may be
marked complete until the split table is resolved.`

Two things the owner can settle without the L1 lane:

1. **Does any P1 spine or robustness cut key on `proxy_basket_type`, or only on
   `disclosure_regime`?** If only the regime, 84 of the 127 splits (66%) stop
   being blockers immediately and the arbitration shrinks to the 43 existence
   disagreements.
2. **Which channel wins on a bare `no_event` vs a `"na"`-basket classification?**
   A defensible default is to treat `"na"` as non-evidence and require a named
   mechanism before admitting a filing to the control set — but that is a sample
   definition and must be fixed *before* it can be read against any outcome.

## What was deliberately not done

The splits were **not** auto-resolved by picking a channel. With no third
channel available and no owner rule on record, choosing a winner would be
guess-filling (meta-rule 4) and would silently set a sample definition.
