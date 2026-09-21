# Field and version evidence

Checked 2026-09-21. Source identities must ultimately be bound to the archived extraction query, not inferred from a filename. This is a short evidence matrix, not a reproduction of copyrighted manuals. No source example financial values are reproduced. Findings apply at the stated level, not automatically to every archived row.

## Primary references actually checked

**D13 — Thomson Reuters, Detail History User Guide, November 2013**, [manufacturer-authored document hosted by University of St Gallen](https://www.unisg.ch/fileadmin/user_upload/HSG_ROOT/_Kernauftritt_HSG/Universitaet/Bibliothek/Suchen_und_Nutzen/Datenbanken/Datenbankseiten/A-Z/IBES_Detail_History_User_Guide.pdf).

Relevant printed pages: 15, 20, 23–24, 44–45, 57. Announcement describes reporting; activation describes vendor recording. Nominal timestamps follow seasonal Eastern time. Quarterly FPI codes include 6–9, N–T, L and Y, not just 6. Forecast history can retain same-day analyst revisions. Reporting currency and received-estimate currency are different concepts; exclusion/stop information is separate. The manual addresses direct-delivery history, so WRDS mapping and extraction omissions still matter. None of these definitions guarantees earliest public dissemination or an immutable, complete history of vendor corrections.

**S13 — Thomson Reuters, Summary History User Guide, November 2013**, [manufacturer-authored document hosted by University of St Gallen](https://www.unisg.ch/fileadmin/user_upload/HSG_ROOT/_Kernauftritt_HSG/Universitaet/Bibliothek/Suchen_und_Nutzen/Datenbanken/Datenbankseiten/A-Z/IBES_Summary_History_User_Guide.pdf).

Printed pp.19–20 and 26 describe the shared actuals product and its 2013 format transition. Product variants differ in split adjustment and currency normalization. The actuals layout includes currency and statistical-period information as well as announcement/activation. Comparable actuals are distinct from restated actuals. That separation does not prove that the local reduced projection preserves the first vendor vintage or every subsequent correction.

**W06 — Robinson and Glushkov, WRDS, A Note on IBES Unadjusted Data, November 2006**, [official WRDS document](https://wrds-www.wharton.upenn.edu/documents/5/A_Note_on_IBES_Unadjusted_Data_pdf.pdf).

Printed pp.1–3 identify detu/actu as unadjusted families. Even unadjusted estimates and actuals can use different share bases when a split intervenes. Ticker-period matching alone is insufficient. The note also distinguishes vendor-effective split dates from true split dates. It supports a known comparability hazard, not a statement that any particular P1 row is incorrect or that a 2006 transformation is valid unchanged in 2023.

**L — LSEG, I/B/E/S Actuals**, [current official product description](https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/actuals).

The product supplies comparable, restatement and go-forward actuals with timing, currency and normalization metadata. Comparable actuals align with analyst reporting conventions, not necessarily unmodified GAAP EPS. Current product capabilities do not certify which tables/columns were included in this archived WRDS export.

**Historical local bridge**, [20260915 continuation 11 public clock adjudication](../../execution_archive/20260915_continuation_11/artifacts/w021_public_clock_adjudication_20260915/PUBLIC_STANDARD_CLOCK_EVIDENCE.md).

The local record cites a 2025 LSEG Academy “I/B/E/S via WRDS” presentation for the WRDS field bridge. The presentation URL failed retrieval in this turn, so that bridge is explicitly reused archival evidence, not a freshly read primary page. The later continuation-11 finding supersedes the earlier continuation-10 blanket statement that nominal timezone was unknown. Neither established earliest-public accuracy or preserved value vintages.

**W09 — Denys Glushkov, WRDS E-Learning, Overview of IBES on WRDS: Research and Data Issues, 2009-12-04**, [WRDS-authored slides hosted by Tilburg University](https://www.tilburguniversity.edu/sites/default/files/download/IBESonWRDS_2.pdf), PDF pp.27–31.

This provides a freshly checked WRDS-specific distinction between analyst release and database entry. It also discusses historical broker-series removal, estimate review updates, and originally reported versus restated/Street earnings. The historical examples demonstrate that download vintage matters; they do not establish the incidence or existence of a particular error in the 2023 P1 files. Recommendation-history changes cited in these slides must not be relabelled as measured EPS revisions in this project.

**LQ — LSEG, Data for Quant Research**, [official brochure](https://www.lseg.com/content/dam/data-analytics/en_us/documents/brochures/data-for-quant-research.pdf), printed p.7.

The product table distinguishes a daily-snapshot Point-in-Time package from Historical data distributed via WRDS with monthly full-history delivery. This establishes a product distinction, not that all ordinary historical research is invalid, or that SCC lacks every possible snapshot. The direct WRDS export requires its own provenance before being called a PIT snapshot series. Do not purchase the PIT product under this task.

The 2017 Thomson Reuters PIT launch URL was also attempted, but the fetched page did not expose the release text; it is not used as substantive evidence.

## Source-specific adjudication framework

| Question | Supported definition / required evidence | What must not be inferred |
| --- | --- | --- |
| ANNDATS/ANNTIMS vs ACTDATS/ACTTIMS | D13 reports versus vendor recording; identify exact extracted columns | Announcement alone proves investor/vendor availability |
| Candidate vendor information set | Activation is relevant to a vendor-information design; document feed delivery and correction limitations | max(announcement,activation) automatically repairs all leakage |
| Earliest public clock | No certification found in checked sources | Nominal timestamp equals first wire/issuer publication |
| Fiscal period | Use FPEDATS/PENDS plus documented periodicity/FPI and measure | Close dates or current tickers are interchangeable |
| Split basis | W06 establishes possible mismatch even within unadjusted families | Same unadjusted label means pairwise equal share units |
| Currency | Establish company/reporting currency and field role, not merely a populated CURR | USFIRM=1 or blank received currency proves every pair is USD |
| Revisions | Preserve separate activation/announcement keys, query projection and source-version provenance | Unique current keys prove absence of revisions or historical overwrites |
| First actual target | Comparable actuals have an economic definition; first-vintage recovery needs its own evidence | Separate restatement product proves current local value is the original release |

## Testable without financial values

File provenance, metadata key multiplicity, date ordering, parse rates, category frequencies and period/identity match counts. These checks can refute naive assembly rules or reveal missing columns. They cannot verify split-adjusted numerical equality, unchanged historical values, or forecast-error correctness. Such numeric checks remain NOT_RUN.

The exact local-source mapping and observed omissions are supplied separately in SOURCE_PROVENANCE.md and METADATA_RESULTS.json. No UNRESOLVED entry should be promoted to SUPPORTED merely because this metadata query completes.
