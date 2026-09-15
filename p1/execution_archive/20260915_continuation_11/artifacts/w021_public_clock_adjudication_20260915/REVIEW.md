# Checkpoint 11 independent bounded review

Date: 2026-09-15. Verdict: **PASS**.

Scientific state: **HOLD_DESIGN for the nominal database-time branch; HOLD_DATA for the intended true earliest-public-time branch.** No quote purchase, realized rank, PRE calibration, power or treatment-effect work is supported by this checkpoint.

Routing: separate `p1_final_scientific_referee` agent. Actual backend model ID and reasoning-effort telemetry: **NOT_OBSERVED**. No delegation.

## Verified findings

1. **Source convention and accuracy are separated.** The public-evidence ledger reasonably adopts seasonal ET/DST as the supported standard nominal convention through the manufacturer Actuals product chain and WRDS-specific field context. It does not claim a delivery-specific timestamp audit, earliest-public guarantee, rounding/imputation bound or stable revision history. Announcement/report fields remain distinct from activation fields. UTC is not selected because it yields more observations.
2. **Citation correction is right.** The shared post-April-2013 Actuals description is on **printed p.20** of the Detail History guide; printed p.15 gives seasonal EST/DST and p.27 gives unadjusted Actuals naming. The evidence ledger now uses p.20 consistently. The [Detail History guide](https://www.unisg.ch/fileadmin/user_upload/HSG_ROOT/_Kernauftritt_HSG/Universitaet/Bibliothek/Suchen_und_Nutzen/Datenbanken/Datenbankseiten/A-Z/IBES_Detail_History_User_Guide.pdf) supports those statements. The Summary-layout and glossary references preserve their previously reviewed, limited documentary roles.
3. **Accuracy evidence is bounded.** The [LSEG Actuals product page](https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/actuals) distinguishes announcement and activation dates and describes restated actuals; it does not guarantee precise first-public timestamps. The cited [2016 article](https://www.sciencedirect.com/science/article/pii/S0165410116300052) explicitly explains its use of newswire timestamps to avoid systematic I/B/E/S timestamp errors. That supports caution about accuracy, not a competing timezone convention or a measured error distribution for W021.
4. **Copied results are unchanged and correctly interpreted.** Byte comparisons confirm that the support table and sensitivity receipt exactly match checkpoint 09. Their SHA-256 values also match the original reviewed artifacts and the receipt's support binding. Under `DISPLAY_AS_AMERICA_NEW_YORK`, the table gives **0 high / 0 low stocks** meeting both PRE and POST RTH-60 support with the primary analyst filter; both illustrative 8-PRE/4-POST counts are also zero. No new protected-row computation was performed or implied.
5. **The branch verdict follows.** Zero support is a valid necessary-support failure of the implementation defined on the nominal database report timestamp. `DECISION.md` and `STATUS.md` explicitly refuse to extrapolate that zero to a repaired earliest-public calendar. The illustrative 0–60-minute interval is not promoted to an error bound. The nominal branch can therefore be closed as HOLD_DESIGN while the true-time branch stays HOLD_DATA. Retaining the true-time object would require a specified timestamp-repair source/workflow; changing session/estimand would require an explicit scientific amendment. Neither choice is silently implemented here.
6. **Scope is clean.** Reviewed checkpoint files contain public documentary references, prose, aggregate support counts and hashes. No licensed observation rows, market records, financial values, research outcomes or credentials were observed. No SCC/raw/sealed-data access, provider message, purchase or publication operation was performed. Public-source access was confined to cited documentary/academic sources.

## Verification limits

The Academy deck is a relevant LSEG-authored WRDS training source. The final memo now correctly cites **PDF p.12** (zero-based page 11, “Terms of Estimates”) for report versus activation definitions and **PDF p.22** (zero-based page 21) for the WRDS available-table output. The coordinator reported visual verification of both pages from the downloaded PDF and extraction of `actu_epsus` from the table list. This reviewer verified the corrected memo locators and hash; intermittent screenshot retrieval prevented a fresh independent visual reproduction here. The locator correction does not change PASS and does not turn field-role evidence into an explicit timezone or accuracy certification. The new execution receipt listed in the index was not yet present at the original review and was not reviewed. Protected input hashes were not recomputed.

## Reviewed hashes

| Artifact | SHA-256 |
|---|---|
| STATUS.md | `0019b1032d48126190555b1a4a2873528ef56affc1285d2b38fc90fee2550fd7` |
| ARTIFACT_INDEX.md | `fc89340a9c61ed4942f88176627025f587e006a052e4933e45a98120f06b9a93` |
| DECISION.md | `79e0cdb98560b807411ea9356bb86fb1a64f4fb2364b74b061fe535eb9fb7b6e` |
| PUBLIC_STANDARD_CLOCK_EVIDENCE.md | `95613bb78d7fdfd41597cf57f4df2634a5d413e8ffc06a78e2abf306323ae842` |
| CLOCK_SENSITIVITY_RECEIPT.json | `c26ec07c5aac517c9409730dc445dcfd4b10cfd921c4d71067f2a8a22acf2ea6` |
| necessary_support_by_clock_scenario.csv | `9b3b91a6ed58cc5fe9b52b3954bd2a86bc1be7c9c3372f9155895fc9da1cebb9` |

No scientific or arithmetic correction is required to these supplied checkpoint artifacts.
