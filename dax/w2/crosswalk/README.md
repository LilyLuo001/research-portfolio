# OCC2010 to O*NET crosswalk

`build_occ2010_crosswalk.py` is the authoritative production builder for the
DAX CPS OCC2010-to-O*NET mapping. It preserves unresolved route components at
their original Census/OEWS weight rather than discarding an entire occupation
or renormalizing around unavailable children.

## Production order

1. Build the private legacy fallback with
   `build_legacy_onet_fallback.py` from the official O*NET 25.0 archive and the
   official 2010-to-2019 taxonomy crosswalk.
2. Run `build_occ2010_crosswalk.py` with the current O*NET time shares, the
   private legacy fallback, official Census/OEWS crosswalk inputs, and the
   preperiod CPS cells.
3. Require both gates: mapped component mass at least 90% and no single
   unresolved occupation contributing more than 1% of preperiod CPS weight.

The detailed fallback, detailed crosswalk, occupation gap audit, raw O*NET
archive, and respondent-level CPS data are private artifacts and must not be
committed. Only sanitized receipts and aggregate audit reports belong in Git.

## Interpretation

Only `resolved_employment_weighted` CPS codes are point-identified for direct
downstream use. Every provisional component must retain min/max bounds across
its officially linked SOC/O*NET children or legacy sources. Equal shares are a
diagnostic center, not a measured employment or task allocation.

`build_crosswalk.py` predates this component-preserving production path and is
not the canonical DAX builder.
