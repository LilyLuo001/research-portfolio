# R1b input requirements — exactly what must be pasted, and why each item

`REFR-R1b-parse` is blocked on two things: `REFR-R1a-verify` (the registry) and
"the owner-pasted file heads". That second phrase has never been made specific,
so this is the specific version — derived from the frozen contracts
(`ops/contracts/{macro_calendar,surprises}.yaml`), `frozen_config.yaml`, and the
C0-R definitions, not from anyone's impression of what USMPD contains.

**The transform half of R1b is already built and tested**
(`refraction/pipeline/surprises.py`): standardization, the scheduled-window
policy, and the acceptance assertions. What remains is an adapter from the real
file's columns to the contract's columns. Supply the items below and R1b is a
short, mechanical task rather than a research one.

## What to paste

| # | Item | Why it is needed | Consumed by |
|---|---|---|---|
| 1 | The **file name, format and version** of the USMPD download, and the page it came from | provenance for the manifest; the file's own version string is the only legitimate source | manifest, R1a registry |
| 2 | The **complete column list**, verbatim | the adapter may use only pasted names — inventing one is an iron-rule-1 violation | `parse_usmpd()` |
| 3 | The **first 20 rows** | reveals date format, decimal convention, units, and null encoding, none of which are guessable | `parse_usmpd()` |
| 4 | **Which column is the registered FOMC surprise**, with the official definition quoted (≤25 words) and its page/URL | `S_raw` for FOMC. The database carries several surprise measures; choosing one after seeing results would be specification search, so it is registered here, before any estimation | `S_raw`, prereg |
| 5 | How the file **flags unscheduled meetings** | `is_scheduled`, which drives an exclusion `frozen_config` already fixes (`surprise.exclude_unscheduled: true`) | `is_scheduled` |
| 6 | Whether **statement and press-conference windows** are separate columns or separate rows | decides whether one FOMC date can produce two rows — and the contract's primary key is `(type, date_ET)`, so this is a schema question, not a detail | primary key, A1 |
| 7 | The **timezone convention** of the date/time fields | C0-R stores dates UTC and announcement clocks in ET; a silent timezone assumption would misalign every announcement window in R2 | `time_ET`, assertion A4 |
| 8 | A **sample of the FOMC/CPI/NFP calendar CSV** as R1a will deliver it | assertion A2 reconciles the surprise series against the calendar per type and per year — that is what catches a parse silently losing a year | A2 |

## What is NOT owed, and must not be pasted

- Any **CPI/NFP consensus** figure. The consensus source is an open NEED_HUMAN
  (`frozen_config: surprise.consensus_source: null`). Until it is licensed and
  registered, those rows carry `S_raw` null and `S_std` NULL — which the contract
  explicitly permits and the manifest counts. FOMC-only does not block Gate-0.
- Any number "from memory" about the database's coverage or structure. If item 1
  or 2 cannot be produced from the file itself, the correct output is
  `NEED_HUMAN`, not a best recollection.

## What happens once these arrive

1. Write the adapter: pasted column names → the seven contract columns. No other
   code changes; the transform and assertions are done and tested.
2. Run the acceptance assertions. A1 (no duplicate keys), A3 (no non-finite
   `S_std`), A4 (release times match the registered ones), A5 (inside the
   registered sample window) are hard. A2 (calendar reconciliation) reports
   separately, because the calendar is an independent R1a deliverable.
3. Validate against the two contracts, emit the manifest with the null-`S_std`
   counts, and R1b is done.
