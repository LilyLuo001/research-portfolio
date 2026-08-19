# refraction — deliverable manifest

执行手册 §0.4: 交付物 = 主产出文件 + manifest.md（输入清单+行数/哈希、环境、
局限、UNKNOWN 清单、下游注意事项）。缺 manifest 视为未交付。

This is the directory-level manifest covering every landed artifact. R13's
run-output manifest stays where its outputs are: `refraction/scans/manifest.md`.

## Artifacts and digests (sha256, first 16)

| file | sha256:16 |
|---|---|
| `refraction/pipeline/surprises.py` | `1633ae8063aeea9c` |
| `refraction/fetch_r1a_sources.py` | `d0915fc6e02d4ba6` |
| `refraction/scan.py` | `ffdccbe0b7eb2d44` |
| `refraction/pipeline/assert_panel.py` | `7d9fe34a7a99dcff` |
| `refraction/guards/prereg_guard.py` | `b58e85d74ca76d32` |
| `refraction/frozen_config.yaml` | `cf1943204634d97f` |

## Environment

Python 3.11.15 / pytest 9.1.1 in the session container. `scan.py` is kept
**3.6-compatible** because the always-on box venv is 3.6; the rest targets 3.11.
Test suite: 90 passing in `refraction/tests/`, all on synthetic fixtures.

## Deliverable 1 — R1b transform half (`pipeline/surprises.py`)

- **Inputs**: none at build time. At run time it consumes rows shaped by
  `ops/contracts/surprises.yaml` + `macro_calendar.yaml`, and reads every tunable
  from `frozen_config.yaml` (`surprise.standardize`, `surprise.exclude_unscheduled`,
  `panel.release_times_ET`, `sample.announcements_*`).
- **Limitations**: the PARSE stage is unimplemented by design — `parse_usmpd()`
  raises `NeedInfo`. No USMPD file has ever been seen by this repo.
- **UNKNOWN**: the eight items in `R1b_input_requirements.md`, chief among them
  which column is the registered FOMC surprise.
- **Downstream**: R1b's adapter maps pasted column names onto the seven contract
  columns; assertions A1/A3/A4/A5 are hard, A2 reconciles against R1a's calendar.
- **Caveat carried to R4/OSF**: `S_std` divides by the full-sample in-sample
  standard deviation (per C0-R), so an early announcement's scale embeds later
  variance. Disclose it; name expanding-window standardization as the variant.

## Deliverable 2 — R1a fetcher (`fetch_r1a_sources.py`)

- **Inputs**: seed landing pages only (`SEEDS`), never deep file URLs.
- **Limitations**: **never executed against a live network** — every lane that
  produced it was egress-blocked. Verified only against synthetic payloads.
- **UNKNOWN**: whether each seed URL is current. A wrong seed appears as a 404
  row in the registry rather than as a silent gap, which is the intended failure
  mode, but it means the first live run must be read by a human.
- **Downstream**: feeds R1a's three registries; its `r1a_file_heads.md` answers
  items 2 and 3 of `R1b_input_requirements.md` mechanically. It does **not**
  answer item 4 (which column is the registered surprise) — that is a
  verification judgement.

## Deliverable 3 — R13 resident monitor (`scan.py`)

Full manifest: `refraction/scans/manifest.md`. Same open caveat as deliverable 2:
never run live; cron wiring is a seat-D edit.

## Deliverable 4 — R0 repo contract (`guards/`, `pipeline/assert_panel.py`, `frozen_config.yaml`)

- 14 panel assertions (A1–A14), 13 hard + A5 soft by design.
- Both iron rules enforced as program invariants.
- **UNKNOWN / open**: four Gate-0 items listed in `AUDIT-2026-08-19.md` §"The
  four things to settle before Gate-0" — two null thresholds, one Plan-vs-manual
  conflict, one sample-window question. Two of the four are enforced as nulls so
  R3 stops rather than guesses.

## Downstream notes for anyone picking this up

1. Nothing here has touched a post-period outcome column; the R6+ path is
   guard-blocked and must stay that way until `REFR-GATE-OSF`.
2. `w_shrink` and `prereg.osf_timestamp` are still null — a test asserts it.
3. Deliverables 2 and 3 have never run live. Treat their first output as
   evidence to review, not as a result.
