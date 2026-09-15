# W021 pre-announcement holdings source locator

Scope: read-only metadata/path discovery for `S000032550` (JPMorgan Equity Focus Fund), bounded at the 2022-12-15 public conversion-announcement date. No holdings rows or outcome values are reproduced.

## Located canonical identity

- Series: `S000032550`, JPMorgan Equity Focus Fund; W021.
- Existing local filing source: `/Users/lilyluo/research-portfolio/p1/t2_free/cache/nport/1217286_000175272423045114.xml`.
- Existing local report date: `2022-12-31`.
- SEC accession/report metadata: accession `0001752724-23-045114`; public filing date `2023-02-07`; SEC N-14 source URL recorded in `missing_data_round_20260914/strict_preannouncement_filing_manifest.csv`.
- This 2022-12-31 report is post-announcement and is therefore not a valid pre-announcement holdings source.

## Earlier public SEC report located

The SEC submissions metadata identifies the exact earlier N-PORT-P filing for the already-identified series: report date **2022-09-30**, filing date **2022-11-23**, accession **0001752724-22-263385**. The SEC filing index is:

`https://www.sec.gov/Archives/edgar/data/1217286/000175272422263385/0001752724-22-263385-index.html`

The index explicitly lists series `S000032550`. This is before the 2022-12-15 public conversion announcement and is the appropriate predecessor holdings source locator. Holdings bodies were not retrieved or reproduced here.

## Bounded acquisition

The free public XML was acquired to SCC at:
`/projectnb/econdept/qluo/P1_Refraction_WRDS/w021_preannouncement_repair_20260915/raw/primary_doc.xml`

The narrow source-side parser verified only series `S000032550` and report date `2022-09-30`; XML body/holdings were not exposed. See `ACQUISITION_RECEIPT.json` and `acquire_sec_nport_metadata.sh`.

## Evidence files

- `/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot/missing_data_round_20260914/SELECTED_PREANNOUNCEMENT_FILINGS.csv`
- `/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot/missing_data_round_20260914/strict_preannouncement_filing_manifest.csv`
- `/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot/fund_package_clock_facts_20260915/fund_package_clock_facts.csv`
- `/Users/lilyluo/Documents/P1_Refraction_WRDS_Data_Usage_Manual_UPDATED_20260903.md`

Backend telemetry: `NOT_OBSERVED`.
