# Clock evidence update — 2026-09-15

This document adds new evidence; it does not overwrite the earlier UNKNOWN receipts or certify measurement Gate 1.

## Newly located manufacturer documentation

The **Thomson Reuters I/B/E/S Detail History User Guide, November 2013**, hosted by the University of St Gallen, states on printed page 15 that Detail History timestamps use Eastern Standard Time or daylight-saving time according to season. Printed page 57 distinguishes activation (database recording) from announcement (reporting) time for forecasts/actuals. Printed page 5 limits the guide's intended scope to direct Thomson Reuters deliveries, not third-party platforms. [Manufacturer manual](https://www.unisg.ch/fileadmin/user_upload/HSG_ROOT/_Kernauftritt_HSG/Universitaet/Bibliothek/Suchen_und_Nutzen/Datenbanken/Datenbankseiten/A-Z/IBES_Detail_History_User_Guide.pdf)

The companion **Summary History User Guide, November 2013**, printed pages 19 and 26, identifies the post-April-2013 actuals file shared by Summary and Detail and lists separate announcement and activation date/time fields. The actuals layout is therefore relevant, rather than a forecast-only analogy. No Eastern-time statement was found in that companion document. [Manufacturer manual](https://www.unisg.ch/fileadmin/user_upload/HSG_ROOT/_Kernauftritt_HSG/Universitaet/Bibliothek/Suchen_und_Nutzen/Datenbanken/Datenbankseiten/A-Z/IBES_Summary_History_User_Guide.pdf)

## What changes, and what does not

- Change the documentary finding from **no manufacturer timezone evidence located** to **manufacturer Detail History Eastern/DST convention documented**. A season-invariant UTC−05 conversion would contradict that convention. No data conversion has been performed here.
- Applicability to the exact WRDS `actu_epsus` 2019–2024 delivery remains a bridge to verify: the guide is from 2013 and explicitly written for direct deliveries. The matching actuals field layout and the preserved source strings support further investigation, not an assertion that every third-party historical timestamp is unchanged.
- Neither guide establishes a guaranteed first-public-release clock, a seconds-level accuracy bound, or the rounding/imputation rule needed for the five-minute endpoint. The previously measured 852 minute-aligned strings cannot supply that guarantee.
- Do not replace `anntims` with activation time, or infer a timezone from price movements. No RTH, RTH-60, common-mask or power result is issued.

## External timestamp check actually attempted

Intersected the pre-existing fixed-order public-source register with the current 852-association universe, retaining only current PRE observations. Only **two existing locators** overlap: Oracle 2021-09-13 and 2021-12-09. Both issuer pages returned HTTP 200, but neither supplied a parseable publication timestamp in the checked HTML meta/time/JSON-LD fields. This is a limitation of this extractor/source representation, not proof that the page or another original wire has no publication time. It does not establish event-clock agreement.

The script exported only date/timestamp candidates and HTTP status, not article text, earnings values or prices. It did not expand to arbitrary new events or open POST response data. `public_metadata_receipt.json` records execution; `public_metadata_candidates.json` records the two outcomes.

## Precise remaining documentary request

Ask WRDS/LSEG to confirm whether the current `ibes.actu_epsus.anndats/anntims` fields preserve the manufacturer's Eastern/DST convention for 2019–2024, and specify actual-release semantics, minute rounding/imputation and correction rules. Cite the two manual pages above rather than asking a generic timezone question from scratch. Alternatively obtain event-specific original-publication timestamps for the fixed manifest. This request is prepared, not externally sent.

The next measurement run must use a versioned clock policy with explicit uncertainty and a small golden validation before a broad endpoint census. A documented source timezone is meaningful progress, but it is not the same as verified release accuracy.
