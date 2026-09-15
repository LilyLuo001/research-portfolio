# Independent event-calendar data review — 2026-09-13

**Verdict: PASS for final SCC `run_v2`, using the pinned v2 source-record metadata; session census remains NOT_RUN.** The verified result is 103,876 retained source records, of which 96,573 have a historical link valid at the announcement date to a seed PERMNO. This is neither a count of economic earnings events nor an approved analysis sample.

Reviewer: separate agent `/root/p1_census_data_reviewer`. Requested routing: `gpt-6-astra`, effort `high`. Actual model/effort and usage telemetry: **NOT_OBSERVED**. Review independence refers to a separate analytic reproduction, not statistically independent model errors.

## Independent reproduction and boundary

On SCC, the reviewer independently read seed PERMNOs, the five permitted historical-link columns `permno,ncusip,sdate,edate,score` with a seed-PERMNO filter, and eight source-record metadata columns `cusip,pends,pdicity,anndats,anntims,actdats,acttims,source_partition` from the existing v2 CSV. No new annual IBES extraction was run. No financial values were projected, inspected or exported. No licensed metadata rows were copied locally or printed to the conversation. SCC commands were read-only; the only reviewer write is this local report.

An independent vectorized date comparison reproduced the join without importing the implementation's `valid_at` function. PERMNO-filtered historical CUSIPs were normalized and matched to the existing v2 records, then retained if `sdate <= anndats <= edate` (with the implementation's missing-end allowance). The output source-record keys, each row's link count and each row's link-status label all match the delivered SCC envelope. No non-seed PERMNO survived the bridge filter. Existing source-record keys are unique in this pinned input.

| Quantity | Independently verified |
|---|---:|
| Seed PERMNOs | 3,440 |
| Seed-filtered historical-link rows | 5,065 |
| Historical CUSIPs in that seed envelope | 5,040 |
| Existing v2 candidate CUSIPs | 3,344 |
| New historical CUSIP delta | 1,696 |
| Retained v2 source records | 103,876 |
| Records with a date-valid seed link | 96,573 |
| Records without a date-valid seed link | 7,303 |
| Records with multiple date-valid seed links | 0 |
| Parseable announcement dates | 103,876 |
| Strictly parseable `%H:%M:%S` clock strings | 103,876 |
| `pdicity=QTR` source records | 82,300 |
| `pdicity=ANN` source records | 21,576 |

The 1,696-identifier delta was independently reconstructed and its CSV byte hash reproduced. The code does not send those identifiers to an IBES reader: it reads only the existing pinned v2 metadata file and retains its candidate set. They are unqueried additional historical identifiers, not additional observed earnings records.

All 96,573 retained date-valid links happen to have score 1 in this source. This is an independently measured descriptive result; the implementation does not impose a score threshold. Zero ambiguity applies within the **seed-filtered** historical-link universe and does not certify uniqueness against every non-seed security or economic-identity quality.

## Source semantics and session blocker

The reviewed historical-link schema labels `ncusip` Historical CUSIP and `sdate`/`edate` link effective-start/end fields. The interval comparison is an explicit operational convention. IBES schema documentation labels `anndats` an announcement date and `anntims` an announcement time, but supplies no verified timezone, precision or public-release provenance convention. The archived exchange-calendar schema supplies date/trading/holiday/weekend/status flags and exchange group; it does not supply open, close or early-close instants.

Accordingly, parseable announcement strings cannot identify RTH/non-RTH. `SESSION_WAVE_CENSUS.csv` correctly leaves session, wave-assignment and economic-event counts blank with NOT_RUN status. The implementation hardcodes timezone readiness false and does not invoke a classifier to invent a session label. The source-side clock-pattern diagnostic is weaker than time parsing; the reviewer separately verified all current strings with strict `%H:%M:%S` parsing. Neither establishes clock semantics.

`QTR` and `ANN` counts describe records in the full retained v2 population. They are not quarterly/annual economic-event counts, not necessarily counts within the 96,573 linked subset, and not a revision selection rule. Date-valid security linkage does not assign a source record to a conversion wave, prove strict pre-announcement treatment eligibility, or choose an earnings-event identity/collapse policy.

The final `SOURCE_PIN_MANIFEST.json` and `SESSION_CENSUS_SPEC.md` were rechecked after correction: they now state date linkage was executed and the session census was not run. The spec lists all four required pinned inputs and the actual aggregate receipt; stale SSH-blocked/prepare-only claims were removed. The remaining blocker is the absence, among the verified inputs, of documented clock semantics and source-pinned exchange-session intervals. This is not a claim that such documentation cannot exist elsewhere.

## Reproducibility limits

The final local and SCC source scripts have identical hashes listed below. The final `run_v2` aggregate receipt pins the four inputs and both executed-code hashes. The reviewer verified the final SCC envelope and identifier delta remain byte-identical to the independently reproduced outputs. The final receipt adds the two code hashes and leaves all measured counts unchanged. This resolves the earlier receipt's missing code-version binding; the earlier `run/` receipt remains historical.

The generic date helper is not a comprehensive parser for arbitrary future missing/malformed interval values, and event-key groupings would require reconsideration if future input keys were missing or duplicated. These do not change the verified counts for this pinned, parseable, unique-key input. A changed source version needs new validation rather than inheriting this PASS.

Still unresolved: economic-event/revision policy, verified timezone/provenance, exchange-specific historical intervals and session rules, wave/event assignment, eligibility relative to the relevant public announcement/anticipation clock, clean controls, outcome coverage, and scientific design. No treatment outcomes, estimates, power claim or scientific GO were produced.

## Exact SHA-256 binding

Local artifact paths below are relative to this review's directory. Final SCC run files are under `/projectnb/econdept/qluo/P1_Refraction_WRDS/p1_roster_earnings_20260913/event_calendar_v1/run_v2`. The linked schema files are under `/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/meta`.

| Input/source | SHA-256 |
|---|---|
| E007 seed stock-wave CSV | `0c5d9175d53e76d746777776c2ff3ee46cc038f7227120eb22e86077a6d05555` |
| Existing v2 source-record metadata CSV | `97a3c35c1f59013047924b89859df67ff361327a61b7bec0a28bdf3412c562cb` |
| Historical CRSP–IBES link parquet | `fd259ac817ab9ea64553e0cdacadc22fcd94de361d1f1851855f9e27ed87e326` |
| Existing v2 candidate CUSIP CSV | `68f39fbb19803dc2c63ecaf0754a1b9c900c27af1ec5ba3fd1b3d84764ce3d87` |
| `schema__wrdsapps_link_crsp_ibes__ibcrsphist.csv` | `2e54e0fca38aafb7a5701e17572dfe11212053d6665c1973cc91bb1dd9b3b92b` |
| `schema__ibes__actu_epsus.csv` | `699243e0905d1916452bfb05ee3937e9684f3830c1a2d546f2b2cefe38a43934` |
| `schema__crsp__metaexchangecalendar.csv` | `729adb0a99719eb4ced7637643e66dc904687d67f9226da2c0e93d94460930d6` |

| Reviewed code/output/document | SHA-256 |
|---|---|
| `code/source_side_event_envelope.py` (local and SCC) | `09865c9b451349669c910b605bc2e98ee17b5d7e35c162c0ed79d673702f9b9f` |
| `code/linkage_contract.py` (local and SCC) | `70c812ee9d649944abab7d41cc982767b6fdd5d811d88653db3cde758a3fbeca` |
| `receipts/event_calendar_aggregate_receipt_v2.json` (local); SCC `run_v2/event_calendar_aggregate_receipt.json` | `76d012ee560336f72555cbdf3d10532b5b94e522855efd730dbbcd0a9b3f31a4` |
| SCC-only `event_date_envelope.csv` | `e64db1e55fc3c15c775c1206dcbbbb9ace8878d369b2c66efeca4546e74cc99f` |
| SCC-only `new_historical_cusip_delta.csv` | `e244a0e402a732d60930242d0203da0456bd40be257df4268765372d48ef303f` |
| `EVENT_CALENDAR_CENSUS.csv` | `b1e0eb15f827006112a6e0a64ef047d8eb5b87feee8a11444fe6fc68ad37c040` |
| `SESSION_WAVE_CENSUS.csv` | `4d7f7c5e9ddb5e72fa6364b3b4c6d2219bb291316889481a742266fa58c958cb` |
| `EVENT_CLOCK_DICTIONARY.md` | `41d8f02d75bc84a3859e75fe719452e7cbe967e10674d32ce13e2e0bf9568af6` |
| `EVENT_CLOCK_POLICY.json` | `4e68ff7ed394d2df2921efba8ef724f537f831ea46decf29db08fbad403492f1` |
| `SOURCE_PIN_MANIFEST.json` | `a3a1a711d913d1310a169e020fc4b88b9ab6a31434b20d25da6846fbef85a50b` |
| `SESSION_CENSUS_SPEC.md` | `e9409073454594068e02377c1d4cf85b7d223cdf748d84b5db43b74d8ffd062d` |
| `EXECUTION_STATUS.md` | `d0b899d0fe4dcd5b2441c3d52bff87003b879e76076a54d526d5f360d6dd62d7` |
| `NEXT_DECISION.md` | `4be8c5b5b0749d4feeaef164354eace791e3a7ff881d1aaca6b45c0dc4b583f6` |

Administrative routing/review status may be updated separately after this review. Any change to measured code, inputs, outputs or reviewed semantic claims above requires a targeted recheck.
