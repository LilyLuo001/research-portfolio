# LinkUp vendor evidence on job identity and description timing

## Provenance

This note paraphrases user-provided supplier correspondence received on 2026-10-03. The correspondence's own email date was not supplied. Private greetings, addresses, and verbatim email text are omitted.

## Supplier-stated general rule

LinkUp states that `JOB_HASH` is the MD5 hash of the captured job URL. When the same URL is used again, including a repost across years such as 2020 to 2021, it retains the same `JOB_HASH`. When the description associated with that URL changes, the associated description is updated in the daily description file.

LinkUp also states that many jobs created before 2013 lack descriptions. Description coverage is not 100 percent even for current jobs, and coverage varies across companies, so unequal counts are expected.

These statements verify a general supplier rule about URL-based identity and updates. They do not by themselves establish which description version appears in the supplied Dewey files, whether earlier daily versions were retained in an archive, or which archived versions, if any, are available for this project.

## Distinctions required for analysis

- **URL identity:** `JOB_HASH` identifies the captured URL under the supplier's stated rule. Stable `JOB_HASH` therefore establishes continuity of URL identity, not continuity of posting content.
- **Posting episode:** Reuse of the same URL can cover distinct posting episodes. A single hash cannot by itself separate a 2020 episode from a 2021 repost.
- **Text version:** A description can change while the hash remains fixed. The current delivered description is not automatically the description observed at `CREATED`, at a repost date, or throughout a `CREATED`-to-`DELETED` interval.
- **Daily archives:** Daily description archives could support version reconstruction only if the relevant archives were retained and supplied, and only after their version-selection and coverage rules were verified. Their possible existence is not evidence that the current Dewey delivery contains historical versions.

No rule should automatically assign one observed text to the entire `CREATED`-to-`DELETED` interval.

## Consequences for the pre-Revelio analysis

1. A successful one-to-one Records/semantic join supports identity and row-conservation claims only. It remains separate from text-time validity.
2. An AI keyword in a description attached to an old `CREATED` value cannot be interpreted as historical AI language at that creation date without a verified contemporaneous text version.
3. Statistics based on ads whose observed dates cross an analysis boundary diagnose capture-window risk, but they do not measure the full version risk. They can miss within-window description updates and URL reuse across distinct posting episodes.

The existing first-observation-cohort language remains appropriate: delivered snapshot text may be grouped by Records timing for descriptive coverage, but it is not a historical requirements panel or an AI adoption timeline.

## Planning precedence

The main `PRE_REVELIO_EXECUTION_PLAN.md` overrides the two earlier agent recommendation JSON files. This evidence note does not authorize new agent spinups, remote actions, parser changes, or another cleaning cycle.
