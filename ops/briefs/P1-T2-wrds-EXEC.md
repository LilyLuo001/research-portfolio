# EXEC BRIEF — P1-T2-wrds (holdings pipeline → conv_exposure) [WRDS/box]

_Paste below the line into a Claude Code seat ON THE WRDS-provisioned node
(code_pro lane). This task needs licensed CRSP/WRDS data — it cannot run in the
seat-C sandbox. Wave construction is already done (deterministic); this step is
the WRDS holdings join + ConvExp math._

---

You are seat P1 executing **P1-T2-wrds**. Read `CLAUDE.md`, `p1/CLAUDE.md`,
`docs/Project_1.md` §T2 (verbatim spec), and `ops/contracts/conv_exposure.yaml`
(frozen output schema). Meta-rule 1 dominates: every holding / shrout / mapping
is code-on-real-data with a WRDS locator — nothing hand-filled; unmappable funds
go to a NEED_HUMAN file, never imputed.

## Pre-flight (owner/box)
- WRDS credentials live and auto-authing: `~/.pgpass` or `WRDS_USER`/`WRDS_PASS`.
  The username is **case-sensitive** — the earlier `.pgpass` did not auto-auth;
  verify `python -c "import wrds; wrds.Connection()"` connects before running.
- Confirm access to `crsp.holdings`, `crsp.fund_hdr`, `crsp.msf`, `crsp.stocknames`
  (and 13F / ETF-holdings tables for `pre_etf_ownership`).
- Gate: this task is authorized only if **P1-GATE-t2a** (kill-switch, from
  P1-T2a-power) returned non-pessimistic. Confirm with the owner if unsure.

## Inputs (already in the repo)
- `p1/events_merged.csv` — 131 confirmed conversions (T1 output, owner-signed).
- `p1/t2_wrds/waves.csv` — 78 waves, DFA 2021-06-11 = anchor (built by
  `build_waves.py`; rerun it if events_merged changes).

## Steps
1. `python p1/t2_wrds/build_waves.py` (refresh waves if needed).
2. Finish the fund→CRSP mapping in `p1/t2_wrds/holdings_pipeline.py::map_funds`:
   MF-ticker exact match is stubbed; ADD the fuzzy fund_name-within-family match
   and the EDGAR N-PORT fallback (CIK from `source_accession`) for funds absent
   from CRSP MF. Every converting fund must map to a pre-conversion holdings
   report or land in `unmapped_funds.csv`.
3. `python p1/t2_wrds/holdings_pipeline.py` → `p1/conv_exposure.parquet`
   (ConvExp = Σ_f shares / shrout×1000, per Project_1.md §T2) +
   `p1/t2_wrds/convexp_diagnostics.md` (ConvExp histogram, #stocks ≥0.5% / ≥1%
   per wave, DFA-wave share — the kill-switch gate-2 numbers).
4. Fill `pre_etf_ownership` (existing ETF ownership share per stock, pre-wave)
   from the 13F/ETF-holdings join — the field is stubbed empty; the contract
   allows min 0 so populate it, don't leave blank if the data exists.
5. Validate: `python ops/runner/contracts.py conv_exposure p1/conv_exposure.parquet`
   until **PASS** (required cols, primary key permno×wave_id unique, conv_exp≥0,
   mcap_decile 1–10).
6. Lineage: `python ops/runner/lineage.py p1/conv_exposure.parquet p1/events_merged.csv p1/t2_wrds/waves.csv`.

## Done
Contract PASS + diagnostics committed → the diagnostics feed **P1-T2-killswitch**
(human gate 2: the owner reads ConvExp ≥0.5%/≥1% counts and DFA-wave share and
decides go/no-go). Report to the owner: rows, distinct stocks, #treated at each
threshold, DFA-wave share, and the unmapped-fund count. Do NOT proceed to T4/T5
until the owner signs the kill-switch. `git add p1/conv_exposure.parquet
p1/t2_wrds/ ...`, commit, push. Stop.
