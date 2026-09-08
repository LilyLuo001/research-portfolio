# B02 public code and membership access audit

Verified: 2026-09-09 Asia/Shanghai. This is an access finding, not an inference
from an unsuccessful search.

## Author statement and publication page

The official August 12, 2026 paper was downloaded from the Stanford Digital
Economy Lab publication page. Its SHA-256 is
`c8d2e5c4ccc0de7ef977c191c144726d6073e164b33f30397fcb0090165d2bdf`
(3,390,516 bytes). The data-availability statement says that ADP microdata are
covered by a data-use agreement and cannot be public, that derived
occupation-level results can be downloaded from the Canaries Dashboard, and
that code for all analyses is available from the authors **upon request**.

The publication page itself provides the current PDF and an email address for
requesting previous versions; it does not provide a code repository or a
replication archive. Searches of the named authors, paper title, and Stanford
page did not locate an author-provided public code repository. This audit does
not treat search-engine absence as proof; the affirmative paper statement
controls the disposition.

No author was contacted. The V3 instruction requires user authorization before
contacting authors, and none has been granted for that external action.

## What is publicly downloadable

The official Canaries Dashboard exposes three relevant zip archives. Their
fixed Google Cloud Storage object generations, response metadata, archive
hashes, member inventories, and member hashes are recorded in
`BCC_PUBLIC_DASHBOARD_MANIFEST.json`. The companion downloader verifies all of
them before extraction.

The archives contain:

- monthly indexed employment by exposure quintile;
- monthly indexed employment by exposure quintile and six age groups;
- annualized and year-over-year transformations of those series;
- a November 2022 age-by-exposure composition snapshot; and
- data dictionaries identifying the August 12, 2026 vintage and November 2022
  normalization.

The dashboard methodology states that occupations are grouped using equal
occupation weights. The downloadable files contain exposure-group labels and
aggregated results, but no occupation or SOC field, no occupation-to-quintile
membership table, and no code. Thus they authenticate the published aggregate
ADP series but cannot recover the exact occupational membership used to build
it.

## Binding disposition

`B02` remains `BLOCKED_INPUT` for **exact code/membership replication** because
the necessary code must be requested and the exact occupation membership is
not in the public downloads. This does not block transparent public-data
benchmarking. The YAX benchmark must label its tie-preserving equal-occupation
quintiles as an independently reconstructed approximation, compare observable
aggregate definitions and endpoints directly, and never claim exact BCC
membership concordance.

Primary locators:

- paper page: `https://digitaleconomy.stanford.edu/publication/canaries-in-the-coal-mine-six-facts-about-the-recent-employment-effects-of-artificial-intelligence/`
- dashboard: `https://digitaleconomy.stanford.edu/project/indicators/canaries-dashboard/`
- August 2026 PDF: `https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf`

