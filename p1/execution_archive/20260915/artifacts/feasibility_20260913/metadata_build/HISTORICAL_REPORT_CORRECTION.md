# Historical report preservation and correction

The initial `SOURCE_SELECTION.md`, `SUPPORT_CENSUS.csv`, and `RECEIPT.json` are retained as the execution record of the first SCC inspection.  Their statement that no reconstructed exposure CSV was available referred only to the named SCC checkout and was incomplete.  Evidence manifest `E007` identifies the actual earlier reconstructed CSV at `/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_stock_wave_all.csv`, and `E011` identifies its lineage file.

This repair does not erase the historical crosswalk observation: the SCC crosswalk remains a crosswalk, not an exposure CSV.  It corrects the consequent erroneous authority inference.  The corrected inventory files are `advanced_source_inventory.csv`, `free_source_inventory.csv`, `source_comparison_by_effective_date.csv`, and `chronology_uncertainty.csv`.  The sources remain non-pooled and no sole authority is selected.

The earlier categorical zero for new-clock verification has been replaced by `UNKNOWN`.  A date-only announcement permits strict date ordering when a holdings/report date is outside the announcement date; it cannot classify intraday ordering.  No intraday rule was invented here.
