# Replication package draft

This directory documents the reproducible path for *What Is AI Exposure? Measurement Architecture and Statement-Specific Robustness in Early-Career Employment*.

## Data access

- **Labor outcomes:** IPUMS CPS harmonized public-use CPS microdata. Redistribution is not included; replicators must register with IPUMS and create the documented extract.
- **Exposure measures:** the cited AIOE and GPT-exposure source files, vendored when licensing permits or identified by provider, version, and checksum.
- **Mappings:** official Census and BLS occupation crosswalks, with deterministic route-expansion and aggregation rules recorded in the code and receipts.

## Frozen provenance

- Design freeze (peeled commit): `22fbf7924809b7a535e31ae0ab68f5b113ce8078`
- Confirmatory results (peeled commit): `b16109482c3bf5ca176f6f08976e120b04769945`
- Final manuscript-production parent: `06670a147be351ea36871ce0fff21e39fc5c1792`

Confirmatory and exploratory outputs retain their original status labels. Seeds, hashes, support definitions, and implementation notes reside in the machine-readable receipts under `yax/analysis/`.

## Build

From `paper/`, run:

```sh
make clean
make all
```

This creates the ReStat submission, circulation paper, online appendix, and cover letter in `paper/build/`. A TeX Live installation with `latexmk`, BibTeX, `newtx`, `natbib`, `booktabs`, and `threeparttable` is required.

## Reproducing empirical results

The manuscript-production pass does not rerun empirical specifications. To reconstruct the sealed analysis from authorized raw data, follow the phase-specific receipts and command manifests in chronological Git order. Do not place API keys, account credentials, local absolute paths, or cluster hostnames in configuration committed to version control.

## Before public release

- [AUTHOR TO COMPLETE] archive the replication repository and enter its DOI.
- [AUTHOR TO COMPLETE] confirm the public repository URL and license.
- [AUTHOR TO COMPLETE] verify that every vendored source file permits redistribution.
