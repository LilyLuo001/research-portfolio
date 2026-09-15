# Independent bounded Gate 1 review — 2026-09-15

Verdict: **the final evidence supports HOLD_DATA + HOLD_DESIGN for the interpreted post-download measurement gate.** No decisive-count error was found. The downloaded-file header census does not establish measurement-gate passage, body integrity, live quote coverage, identification or power. No legacy exposure Gate 0/1 is certified here.

Review routing: requested **gpt-6-astra / high**. Effective backend model/effort telemetry: **NOT_OBSERVED**. One bounded reviewer; no nested delegation.

## Scope and independent method

Read both audit scripts, their final receipts and support tables, the final decision and conditional plan, and the measurement/design gates in `evaluation_20260914/design/SUPPLEMENTAL_PULL_PLAN.md`. Independently reconstructed job IDs, requested job-symbol sets, core request-map joins, eight distinct role/leg combinations per association, pool-rule conjunctions, date comparisons and supporting denominators using separate local metadata calculations. This was not a rerun of either audited script.

This reviewer did not connect to SCC, inspect DBN bodies, open raw EPS/forecast/quote/return sources, purchase data, unseal responses or execute power simulations. Remote existence, byte size and decoded-header values are supported by the audit output and receipt, not by a second independent remote file audit. Local copies of all three acquisition-control inputs hash-identically to the header receipt. All eight readiness input hashes were checked against their local files. Full DBN hashing was disabled by the user and was neither required nor performed.

## Independently reproduced decisive results

| Quantity | Independent result |
|---|---:|
| Planned jobs / unique IDs | 5,548 / 5,548 |
| Manifest jobs / unique IDs | 5,544 / 5,544 |
| Header-audit unique job status | 5,544 HEADER_CONTRACT_MATCH; 4 NOT_DOWNLOADED |
| Expected / observed unique job-symbol pairs | 18,592 / 18,592; exact set equality |
| Mapping statuses | 18,387 DATE_VALID_UNIQUE; 191 NOT_FOUND; 14 UNKNOWN |
| Core atomic-request map | 4,648 rows, 4,648 unique atomic IDs |
| Core logical request legs | 6,816 across 852 associations |
| Distinct stock/SPY × request-leg combinations | Exactly eight per association |
| Associations with all eight header/mapping passes | 839 / 852 |
| Incomplete associations / logical legs | 13 / 50 |
| Selected stock-wave units / PRE / POST | 71 / 568 / 284 |
| Associations with analyst count at least two | 659 / 852 |
| Calendar and RDQ join universes | Each 852 unique IDs, exactly the selected event universe |
| Observed session dates / distribution flags | 851 / 10 |
| RDQ UNIQUE / MISSING / same-date | 828 / 24 / 809 |
| Unique PERMNO/release-date keys / release dates | 852 / 417 |

The four absent manifest jobs are `COREJOB_00366`, `ALTJOB_00186`, `ALTJOB_01420` and `ALTJOB_01748`. The 191 NOT_FOUND instances concern CRD. Core incompleteness consists of 48 CRD logical legs across its 12 associations plus the GDEN and SPY legs of one additional association in `COREJOB_00366`. The header evidence does not establish why a symbol failed or why transport/query requests failed; it cannot justify concluding that historical market data are absent.

The full-pool clean-and-analyst counts below were recomputed as the conjunction of `proposed_overlap_clean` and `all_12_events_min2`; all corresponding saved conjunction flags agree. The pool has 2,088 unique stock-wave rows.

| Wave | HIGH | LOW |
|---|---:|---:|
| W002 | 10 | 165 |
| W013 | 0 | 0 |
| W016 | 2 | 1 |
| W021 | 0 | 0 |
| W025 | 2 | 2 |

These are conditional on the proposed exclusion and analyst rule, not certified final eligibility. The selected 15-stock-wave subset must not replace this full-pool denominator. The final decision makes that distinction. W013/W021 emptiness and W016's single LOW unit support the stated design hold under that rule.

## Correctness, permission and interpretation findings

1. **Header decoding is bounded metadata work.** `audit_dbn_headers.py` reads the DBN prefix and declared metadata section and invokes `Metadata.decode`, with no record iterator or record decoder. A compressed stream may buffer compressed bytes beyond the metadata boundary internally; consequently “no records decoded or analyzed” is more precise than “no body bytes accessed.” Neither stat/size equality nor a decoded header certifies full body decoding, compressed-stream completion, checksums or valid endpoint states. The final decision and receipt retain these limitations.

2. **Start-date mapping is a narrower claim than interval identity.** The script checks each symbol's mapping at the request's UTC start date only. In fact, 2,744 of the 5,548 planned requests cross a UTC-date boundary. Future measurement must verify identity across the relevant interval. Header equality checks dataset, schema, start, end and the requested-symbol set; it does not compare `stype_in` or `stype_out`. All planned `stype_in` values are `raw_symbol`. These limitations do not invalidate the reproduced structural counts, but prevent interpreting HEADER_CONTRACT_MATCH as exhaustive validation of every contract field. The final decision now explicitly says start-date-only and no full-interval certification.

3. **Timestamp arithmetic has a latent precision issue, with no current mismatch.** Expected nanoseconds use `int(datetime.timestamp() * 1e9)`, which can round fractional timestamps. Independently comparing every planned start and end to integer timedelta arithmetic found **zero discrepancies**. Integer epoch arithmetic is preferable before reuse with finer timestamps. Parsed date comparisons separately confirm 71/71 holdings-report and denominator rows precede their recorded cutoff, all 568 PRE dates precede cutoff and all 284 POST dates meet their recorded threshold. This does not independently validate cutoff provenance or threshold-calendar construction.

4. **Metadata-container access is accurately disclosed after correction.** The readiness helper hashes complete input files and CSV-parses full rows before selecting columns. Some existing roster/pool containers include derived liquidity/ownership fields. A broad `financial_or_quote_values_read=false` claim would overstate the access boundary. The final receipt replaces it with separate declarations that raw response sources were not opened, complete metadata containers were hashed/parsed, and liquidity/ownership values were not analyzed or returned by the census. Code inspection supports those narrower declarations. Metadata examination of archive-only jobs is not authorization to decode POST responses; the conditional plan preserves that boundary.

5. **Structural joins agree for this input snapshot.** The readiness code lacks uniqueness checks for some intermediate dictionaries and calendar/RDQ joins, which could hide duplicate IDs on later inputs. Independent checks found no duplicates or missing/unexpected selected IDs in the current inputs, and verified eight distinct role/leg combinations rather than merely eight rows. This is a future robustness improvement, not a present count defect.

6. **Clock parseability is not certification.** All 852 clock strings have one parseable `HH:MM:SS` value, without a certified release timezone or precision source. Session/RTH-60 and common six-horizon eligibility remain UNKNOWN, not zero. No header-derived statistic fills that gap. This alone prevents passing the current measurement gate; the 839 structural passes cannot be promoted to 839 measured usable events.

## Decision and conditional-plan consistency

The final decision correctly separates data hold, conditional design failure and unassessed power. Its next action addresses clock and historical symbol verification before endpoint masks. The staged plan preserves the response seal, keeps four venues distinct, separates identification from precision, requires the actual design/rank/dependence evidence, and makes prospective power conditional on earlier gates. This review does not certify future source-side access permissions or the future estimator. No additional analysis launch follows from this review.

Also inspected `finalize_receipt.py` and the initial `run_manifest.json`. Independently verified selected-ID equality, three recovered jobs present, four excluded jobs absent, selection/recovery/grouping control hashes and archive-labeled manifest paths containing `/sealed_post/`. These are consistent with its eleven reported invariants and the earlier independent checks. A sealed path name verifies organization, not operating-system access control or proof against response unsealing. Static declarations about charged calls and remote execution remain coordinator run assertions, not independently observed billing or execution telemetry. The coordinator will regenerate the run manifest to include this review; its changing hash is intentionally not pinned here.

## Reviewed final artifact SHA-256

| File | SHA-256 |
|---|---|
| audit_dbn_headers.py | `d9312093836eee974205fdcbe64c8cb47332413e799bbfefe21c441f19d7e66d` |
| build_readiness_summary.py | `113a58bab0981499f0e41fba3b74b1989a147e3631fb26ab4f0c3aaa4e1b513b` |
| finalize_receipt.py | `bc0bc1aa06b23a6be35716122a05ed03da74b7effca02f1cc3e209e26ca83ba2` |
| header_audit_receipt.json | `d520e2b1ea43e3b3f71fd3ff56ae503fc75ee50321501c98e561a48b13eed63b` |
| readiness_receipt.json | `8fb35e11bb9fac3cd2ab6e47c525e18f543062b16dbb4bf6ffa566390fe97a91` |
| job_symbol_header_audit.csv | `87bb7e6e9e0b79afd75673cfcb9c9f7acfb53596ca39cdb7dd449e96cb48a0b1` |
| core_logical_leg_mapping_support.csv | `0b23c5ccbc56c8a5f7aad6fdcf186046f8037f8b04de73a75ffbe20267dd67b6` |
| core_mapping_gap_locators.csv | `270b2309df11292a9144fc80dde94927397159a74590ba5a51b4e6b27361092a` |
| feed_header_summary.csv | `da311c6c39b026ea18c32920561443bb9def198f75e057a3b51e434bd4c66b8a` |
| support_by_wave_tier.csv | `a437b6391d734badf4aa413de82a9fcafa8c14105561b0d40c688573e08a4ed2` |
| unresolved_symbol_summary.csv | `9617a23c0fd3ea0f9689ccac0a79603517e2276022b1b41976b1ddff9fa7eed8` |
| DECISION.md | `4e084b72a7abb5e604041f806b2fff05d0b0a6f3d40e0c4fb1dbed9873157b74` |
| CONDITIONAL_PILOT_PLAN.md | `a122df5d97be699053fb0790477f016bc629f44f10e343e848b5e931b7b7e185` |

These hashes identify reviewed code and small artifacts. They are not DBN content hashes or authenticity attestations for remote files.
