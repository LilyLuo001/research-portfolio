# Public-standard evidence for the I/B/E/S actuals clock

## Adjudicated questions

| Question | Public evidence | Adjudication |
|---|---|---|
| Nominal timezone | The November 2013 Thomson Reuters Detail History Guide, printed p.15, states that Detail History timestamps use EST or daylight-saving time according to season. | `SUPPORTED_STANDARD_CONVENTION`: interpret nominal U.S. history clocks with historical `America/New_York`, not UTC or year-round UTC-05. |
| Applicability to actuals | The same guide, printed p.20, says the post-April-2013 Actuals file is the standard file shared by Detail and Summary packages. Its layout uses unadjusted `act<measure>u.<reg>` naming. The companion Summary Guide, printed p.26, gives that Actuals layout with separate announcement and activation date/time fields. | `SUPPORTED_PRODUCT_CHAIN`: the convention and layout are relevant to the unadjusted U.S. EPS actuals family underlying the WRDS table. |
| WRDS bridge and field role | A 2025 LSEG Academy presentation specifically titled “LSEG I/B/E/S via WRDS” defines `ANNDATS` as when a forecast/actual was reported and `ACTDATS` as when it was recorded by LSEG; it also lists `actu_epsus` among WRDS I/B/E/S tables. | `SUPPORTED_NOMINAL_ROLE`: announcement/report metadata is distinct from vendor activation. |
| First-public guarantee | The guides say “reported” and distinguish activation, but do not guarantee earliest public dissemination across issuer, wire and filing channels. | `NOT_SUPPORTED`: do not label `ANNTIMS` a certified earliest-public timestamp. |
| Precision/error bound | The actuals layout is `HH:MM:SS`, while the frozen projection has minute-aligned values. The guides do not state rounding, truncation, imputation or an accuracy bound. Published work reports I/B/E/S timestamp errors and sometimes checks newswires/other event sources. | `NOT_SUPPORTED`: nominal session classification is possible; five-minute or true-time classification is not certified. |
| Revision/correction | Actuals and restated-actuals products are separately described, but no public source found here says whether an announcement timestamp is overwritten after a correction. | `UNKNOWN`: retain versioning and do not infer correction stability. |

## Source chain

1. Thomson Reuters, *I/B/E/S Detail History User Guide*, November 2013:
   [manufacturer guide](https://www.unisg.ch/fileadmin/user_upload/HSG_ROOT/_Kernauftritt_HSG/Universitaet/Bibliothek/Suchen_und_Nutzen/Datenbanken/Datenbankseiten/A-Z/IBES_Detail_History_User_Guide.pdf).
   Relevant printed pages: 15 (seasonal EST/DST), 20 (shared Actuals
   product), 27 (unadjusted file naming/layout pointer), and 57 (announcement
   versus activation glossary).
2. Thomson Reuters, *I/B/E/S Summary History User Guide*, November 2013:
   [manufacturer guide](https://www.unisg.ch/fileadmin/user_upload/HSG_ROOT/_Kernauftritt_HSG/Universitaet/Bibliothek/Suchen_und_Nutzen/Datenbanken/Datenbankseiten/A-Z/IBES_Summary_History_User_Guide.pdf).
   Printed p.26 supplies the shared Actuals file layout.
3. LSEG Academy, *LSEG I/B/E/S via WRDS*, 2025:
   [training deck](https://www.lib.nccu.edu.tw/var/file/0/1000/img/101/WRDS_IBES_202511.pdf).
   PDF p.12 (“Terms of Estimates”) defines report versus activation dates;
   PDF p.22 shows the WRDS available-table output that includes `actu_epsus`.
4. LSEG, *I/B/E/S Actuals*:
   [product page](https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/actuals).
   It describes actual announcement and activation dates as distinct fields and
   lists restated actuals separately.
5. Michaely, Rubin and Vedrashko, *Further evidence on the strategic timing of
   earnings news*, Journal of Accounting and Economics (2016):
   [article page](https://www.sciencedirect.com/science/article/pii/S0165410116300052).
   The study uses newswire timestamps to avoid documented systematic errors in
   I/B/E/S timestamps. This is accuracy evidence, not a competing timezone
   definition.

## Interpretation rule

For the frozen **nominal database-clock diagnostic**, localize populated
`ANNDATS` + `ANNTIMS` with the historical `America/New_York` calendar and keep
activation fields separate. Label the result `NOMINAL_IBES_REPORTED_TIME`, not
`VERIFIED_FIRST_PUBLIC_TIME`.

For the scientific object requiring true earliest-public release time, retain
`UNKNOWN` unless an event-specific source or an events/news vendor supplies a
timestamp with provenance and a usable uncertainty interval. Never choose UTC
because it yields a larger sample, and never infer a clock correction from
prices or returns.
