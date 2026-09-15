# Checks actually run

- Built the 32-event and fixed 16-event manifests.
- Verified all event dates are XNYS sessions and all requested dates are regular-close sessions.
- Verified exclusive UTC bounds and New York round-trip timestamps, including the November 2021 DST change.
- Verified no duplicate physical requests within each manifest.
- Verified every logical event leg maps to exactly one containing physical request.
- Ran six synthetic cost-selection fixtures (normal order, balanced reduction, overbudget, missing credit, nonfinite quote, smaller credit balance). These are code tests, NOT vendor price estimates.
- Python syntax checks passed.

Not run: Databento SDK/API calls, actual costs, actual downloads, venue/quote quality, official-account entitlements, independent agent review, P1 statistical calibration.
