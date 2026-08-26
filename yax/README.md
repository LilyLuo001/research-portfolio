# YAX — Young-worker AI Exposure

Third dissertation chapter. Independently authored. Not the job-market paper.

**Does young employment deteriorate in AI-exposed occupations after the ChatGPT
release — tested on nationally representative CPS data, under a specification
and coverage rule frozen before any post-period outcome was opened, and
reported against a measured minimum detectable effect?**

Start with **[`RESEARCH_PLAN_v2.md`](RESEARCH_PLAN_v2.md)**.

## Status

| | |
|---|---|
| Wide CPS extract | built, 9,262,480 rows |
| Pre-period file | built **outcome-blind**, 6,188,956 rows |
| Post-period outcomes | **SEALED — never opened** |
| Power engine | built, 999 reps on the real panel |
| Empirical MDE80 | **3.44%** normal theory; bootstrap outstanding |
| Design freeze | **not tagged** — see plan §10 |

## Layout

| path | what |
|---|---|
| `RESEARCH_PLAN_v2.md` | the plan. Read first |
| `RESEARCH_PLAN_v1.md` | superseded; kept for revision history |
| `COVERAGE_RULE_PRESPEC_v1.md` | the three coverage rules, primary named in advance |
| `CORRECTION_2026-08-25_vintage_gloss.md` | a corrected claim and the rule it produced |
| `CHAPTER_SCOPE_v1.md` | superseded by the plan; kept for revision history |
| `measurement/` | the exposure audit — common support, SOC vintage, residual concentration |
| `briefs/` | cold-start execution prompts, C0–C4 |
| `tests/` | regression tests for `measurement/` |

## The one rule that matters most

**No post-period outcome is opened until `v1.0-preregistered` is tagged.** The
pre-registration is this chapter's contribution and cannot be reconstructed
after the fact. Plan §9 lists the six steps that precede the tag.

## Relationship to `../dax/`

DAX is archived — it failed its own feasibility condition when 0 of 22 model
vintages were captured before fixed withdrawal dates. See
[`../dax/memo/DAX_ARCHIVE_2026-08-25.md`](../dax/memo/DAX_ARCHIVE_2026-08-25.md).
It is paused, not refuted, and its estimand and price panel stand as computed.

YAX reads one archived artifact: `../dax/data_built/oews_wages.parquet` (OEWS
2021 employment). The path deliberately points at the archived project rather
than duplicating the file, so the dependency and its lineage stay visible.

## Running the measurement audit

```
python yax/measurement/audit_common_support.py     # from the repository root
pytest -q yax/tests
```

Needs `openpyxl` for the AIOE workbook and, optionally, `matplotlib` for
figures; both degrade to a clear message rather than a crash when absent.

## Note on governance

`ops/accounts.yaml` partitions five seats and assigns `dax/` to seat A. `yax/`
was created on owner instruction and does not appear in that partition. The
apparatus is oversized for a solo chapter in any case — see the archive
record's closing recommendation. Retained here: lineage receipts, the
no-specification-search rule, and the microdata guard. Not retained: lease
claims, dual-vendor requirements, counter-signature workflow.
