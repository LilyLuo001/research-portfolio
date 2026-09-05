# R3 input and replication-boundary provenance receipt

Recorded: 2026-09-05T21:56:18Z
Scope: documentation reconciliation and read-only hash verification
Row-level outcomes opened or analyzed in this reconciliation: **none**

## Baseline implementation reconciliation

The initial inventory predated BASE-03 and incorrectly continued to say that a
fully rebuilt corrected-treatment baseline had not been implemented. The
following existing objects establish completion:

| Object | SHA-256 | Verified fact |
|---|---|---|
| `rebuilt_baseline/run_rebuilt_corrected_baseline.py` | `4c38abcd43d177819d683a0f8774d9e50e02179bde13f9eaae418c6a1aec1704` | executable BASE-03 implementation |
| `rebuilt_baseline/run_scc.sh` | `4243a94c6d49ae9dd334315390701d59ef52d4b307c4c2d024d7af37666e26f3` | successful-run scheduler interface |
| `rebuilt_baseline/results/EXECUTION_RECEIPT.json` | `e3379ea442fa36d92fbc652f7a4a28b66fdef12c3e6c21a2462d1a7765574d21` | authenticated inputs, calendar, construction, and output hashes |
| `rebuilt_baseline/results/SELF_CHECK.json` | `3c1f6ee3b86499cb573cab829efefc6cea48fbfc04a32479e4b28fb75abaa26b` | `PASS_BASE_03_SELF_CHECK`; 21 checks true |

The receipt records a fully rebuilt coefficient of
`-0.13210945079219036`, 468 occupations, a 71-month treatment-construction
window, and a 113-month static outcome calendar. Those values were read from
the stored aggregate receipt/results, not recomputed during this documentation
pass.

## IPUMS extract provenance

### Extract 9: wide stock-analysis file

Versioned evidence:

- request specification:
  `dax/memo/power_calcs/ipums_ai_telework_extract_v2.json`, SHA-256
  `bd798b9dfe11d00153856be3e05a7c52865a149dcc7405a5cbfd812eb3ca6c3a`;
- submission receipt SHA-256
  `d63879c84c1b8ce5c4b61fa90c1d0bd709bdaa8043d328a6c7b8c7dd4bf9cfa7`;
- download receipt SHA-256
  `3a5eef306d791ef608577b5ad07435cda9ce2c3ee1b2bf69b501aace88c89f9e`;
- IPUMS extract number 9; submitted
  `2026-08-25T13:38:31.382050+00:00`; completed-file receipt recorded
  `2026-08-25T13:42:35.789292+00:00`;
- data SHA-256
  `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9`;
- DDI SHA-256
  `5933bc48ed736a00fa70547ef503f571c6f1f9c03aef7d24ce511af3550fb319`;
- basic codebook SHA-256
  `1bf294152576efad9601491860f8238ee72d8291f939fb4ed467edff42815d45`.

### Extract 10: longitudinal-weight patch

Versioned evidence:

- request receipt:
  `yax/analysis/postoutcome_phase2/YAX_PHASE2_LNKFW1MWT_EXTRACT_REQUEST.json`,
  SHA-256
  `1c4ace7510ea80f6d6b5275c16557e6e502de6329ab12dcbb84ab9131b50a9b6`;
- request specification SHA-256
  `258826167f508dc150c39718701e933d13ddc8e9f31c63831d75e97ac8260037`;
- returned extract-definition SHA-256
  `316513a02ef04c032b5ce7b31e84a24a55dd80b96bc6ffe6466521dae10a0b64`;
- IPUMS extract number 10, recorded complete when checked at
  `2026-08-31T10:14:52.354521+00:00`;
- data SHA-256
  `841e13798c34f74a8cd8e0ac1d913742aad5f24fce2c6876793ecf1dd8bd55a8`;
- DDI SHA-256
  `636f1564650d267824e4feef7cc58756e972b66f8546585b052163ddc633753e`;
- basic codebook SHA-256
  `5eb504f219d15d9f6e65e9487815da2557ce6256bac7acd81e9a1d95bf6346e9`.

The checked-at time is not represented as an API completion time.

### Extract 11: March Basic Monthly repair

The public functional-replacement receipt already authenticates the data,
request, and DDI. A read-only SCC metadata check additionally authenticated the
API response and basic codebook without copying their contents into the public
tree:

- IPUMS extract number 11;
- actual request SHA-256
  `2ceeabc416f875c07bbfe9ae327310b9f4b5c3bc474473f459f26a503e7a7d26`;
- API submission-response SHA-256
  `5180c7e3e81723a4e8ec39a61c1fac245aa4300f4666894e2b1b6a4bd317c6e5`;
- data SHA-256
  `a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911`;
- DDI SHA-256
  `e29c6c30a397357b927692af371b3fa77176f3d020f513343237d651bf3d3b03`;
- basic codebook SHA-256
  `30881235904580367d7939923c9ae1834a43d6a0a9d939bc25dbe4b21456c8a1`.

The actual request differs from the earlier prepared template, whose SHA-256 is
`7b99e452a8007c38279f82b489229e432ac1a568749e6a820ca7120cfe2d0abd`.
The actual request is therefore the binding provenance object. No verified API
submission or completion timestamp is present in the response/public receipt,
so those fields remain blank. Filesystem modification times are not promoted
to API timestamps.

## Ordered restricted-data rerun

`run_restricted_full_rerun.sh` is the master restricted-data orchestration
command. It requires external paths via environment variables, refuses an
existing output root, authenticates all licensed inputs before estimation,
runs BASE-03 before dependent modules, and requires each module self-check.
It also invokes the pinned official HonestDiD implementation. The script's
SHA-256 at this receipt is
`25a8d279d479e377a2a4bd6672bbed6419aa18ad720cd7ecf7486c2b0d07f034`.

This documentation pass validated shell syntax and interfaces but did not run
the restricted pipeline. Existing module-specific execution receipts, rather
than this receipt, document completed empirical runs.

## Positive public-package allowlist and scan contract

`PUBLIC_REPLICATION_MANIFEST.csv` (SHA-256
`71d69ad516e2fa984895468b7f9b3aad71f9d530e4d55727f7848a3e67a67cf4`)
is a positive allowlist. A release candidate must be built into a new empty
directory from tracked files only. Every staged path must match an `exact` row,
or a `prefix` row and one of that row's suffixes. Symlinks and any file not
positively matched are forbidden; there is no implicit “rest of repository.”

Before release, the staged directory must pass all of these checks:

1. no literal private absolute root matching
   `^/(?:projectnb|project/econdept|usr3|Users)/`;
2. no token matching `ghp_` plus 30 or more alphanumeric characters,
   `github_pat_` plus 20 or more token characters, or a non-placeholder API-key
   assignment;
3. no `.csv.gz`, `.dta`, `.sav`, `.sas7bdat`, `.rds`, `.fst`, `.feather`, or
   `.parquet` file;
4. no tabular header containing `SERIAL`, `CPSID`, `CPSIDP`, or `CPSIDV`;
5. no unallowlisted path, untracked file, symlink, build log, cache, or
   `.DS_Store`; and
6. manual review of aggregate tables for disclosure/licensing limits and of
   PDFs for embedded metadata.

The direct-identifier names may appear in code or documentation explaining why
they are restricted; the scan forbids them as released table columns. Hashes
are permitted and are not treated as secrets. Angle-bracket placeholders such
as `<YAX_PRIVATE_ROOT>` are permitted.

The source repository has not been declared a sanitized release artifact. Only
a separately staged candidate that matches the positive manifest and passes
the automated and manual checks may be described as the public replication
package. Restricted microdata, the historical first-access receipt, account
metadata, download links, credentials, and operational path history remain
outside it.
