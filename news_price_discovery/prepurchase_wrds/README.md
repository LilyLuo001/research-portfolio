# prepurchase_wrds — no-purchase ETF/stock price-discovery feasibility

**Question (fixed):** do ETFs or their underlying stocks incorporate news first,
and does the ordering differ between monetary announcements and firm earnings?

This module runs the bounded, **no-new-purchase** feasibility test on the
archived WRDS mirror, and ends in a purchase-readiness recommendation. It
cannot establish subminute leadership and does not try to — daily and weekly
evidence is compatible with ETF-first, stock-first, or simultaneous adjustment.

## State: stage 0 built and tested; stages 1–5 not started

Not started **because no seat with archive access has run them yet**, not because
anything was found wanting. The session that built this package was a cloud
container that cannot reach `/projectnb` or `*.bu.edu`; the evidence is in
[`ACCESS_BLOCKER.md`](ACCESS_BLOCKER.md).

| stage | what | state |
|---|---|---|
| 0 | source discovery: manifest → real schemas → capability gates | **built**, 13 tests pass with no WRDS access |
| 1 | event and coverage census; ETF/security crosswalk | not started |
| 2 | portfolio approximation, weights, contribution in bps | not started |
| 3 | Hou–Moskowitz D1 delay; earnings-response curves | not started |
| 4 | optional FRBSF macro supplement; Rigobon variance diagnostic | not started |
| 5 | conditional precision table; acquisition manifest; recommendation | not started |

## Files

| file | what it is |
|---|---|
| `INSTRUCTION-2026-09-06.md` | the owner's bounded instruction, verbatim — **authoritative** |
| `REFERENCE-WRDS-Data-Usage-Manual.md` | archive orientation; an inventory, not a guarantee of any field |
| `config.yaml` | frozen parameters, set before any data was seen |
| `stage0_discover.py` | the discovery pass — footers only, no data rows, no concatenation |
| `tests/` | 13 tests against a miniature fixture archive |
| `ACCESS_BLOCKER.md` | the NEED_HUMAN record and how to clear it |

The execution brief for a seat that *does* have the archive is
[`ops/briefs/opus/OPUS-NPD-prepurchase.md`](../../ops/briefs/opus/OPUS-NPD-prepurchase.md).

## Running stage 0

```bash
python news_price_discovery/prepurchase_wrds/stage0_discover.py \
    --out news_price_discovery/prepurchase_wrds/out
python ops/runner/contracts.py npd_source_catalog \
    news_price_discovery/prepurchase_wrds/out/source_catalog.tsv
```

Override the archive root with `--archive` or `$P1_WRDS_ARCHIVE`. Exit 3 means
`NEED_HUMAN` — the archive was unreachable and nothing was written, which is the
intended behaviour rather than an empty catalog.

Stage 0 answers, from observation rather than assumption: which of the needed
families are physically present; which manifest entries do not resolve on disk;
how many schema variants a family really has; and whether the four columns that
gate stages 1–3 exist. Its `purchase_recommendation` is always `null` — the
recommendation is a stage-5 output made on empirical results, and an inventory
scan is not one.

## Two standing constraints

**Nothing from memory.** Every number in the final package traces to code run on
the archive or to an extraction carrying a raw-source locator. The manual's
coverage table is orientation; the local min/max dates are what your code
computes.

**No expanding after seeing results.** The instrument universe (SPY, XLK, XLF),
the 2019–2023 window, the 120-day report-age rule and its 30/60/90/120 bins, and
the residual-SD grid are all fixed in `config.yaml` ahead of the diagnostics.
2024–2025 stay unexamined; if they are ever inspected, that is disclosed.
