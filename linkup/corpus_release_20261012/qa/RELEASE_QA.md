# Corpus release engineering QA

Date: 2026-10-12  
Decision: **PASS** for the documented reuse release. This is an engineering and provenance acceptance, not semantic certification.

## Accepted execution

Kunshan job `124293534` completed on `kshctest02` with exit `0:0` in 8 seconds (1 CPU, 3 GiB requested, 30-minute limit). The deployed builder and launcher hashes match the repository copies. The release receipt SHA-256 is `75e3afd8720ff8b174d0fe3a3b52fb7f8367c45305edecbcef78cc115181c921`.

The final receipt establishes:

- exactly 2,464 old-version ad shards and 2,464 duration sidecars;
- 204,774,035 canonical US ads, 204,768,752 engineering-usable ads, and 131,286,035 duration-evidence rows;
- one common ad schema and one common duration schema from Parquet footers;
- candidate metadata kept in a separate 6,010,975-row view, with 6,010,975 one-to-one Records matches, 6,008,133 one-to-one O*NET matches, 2,842 O*NET misses, and no O*NET multiplicity;
- zero new row-level data bytes and explicit private catalog/view hashes; and
- copied T1--T4 public artifacts whose local SHA-256 values match every hash in the release receipt.

The builder fails closed on receipt/marker count and binding, footer row counts, schema drift, frozen batch/aggregate/T1 identity, canonical and usable denominators, T4 production identity, candidate cardinalities, and output hashes. Static checks (`python3 -m py_compile` and `bash -n`) passed.

## Required interpretation retained

The public schema and receipt correctly state that `usable` is an engineering parse state; old experience and technology fields are candidate measures; candidate false/non-detection is not semantic absence; occupation/task experience is unavailable and remains `NA`; predictive-AI is frozen all-zero/unmeasurable under the old vocabulary; and observation dates do not prove historical text versions. The 6,010,975-row candidate join is not the 204.8-million-ad denominator, and no full row-level Records/O*NET join is claimed.

Base and candidate Parquet data files were not freshly SHA-rehashed. The job freshly hashed small receipts and copied aggregates, verified receipt-to-marker recorded-hash bindings, and checked file metadata, footer rows, and schemas. The receipt describes that scope accurately. This is sufficient for this reuse registration and must not be restated as a new bytewise audit of all retained data.

## Execution history and companion weight check

The execution record preserves two superseded failures: `124293240` failed before verification because of the Python environment, and `124293285` failed closed during packaging because the retained T1 public copies were absent from the documented Kunshan path. Neither produced a final release receipt.

The companion metadata-only weight audit was independently tightened before its final run. Wuzhen job `46396281` completed with exit `0:0`; receipt SHA-256 `0ba9f498227ce6c57334505f73d862a1b5a294b3d305f59ce23a60f16b65a0bb`. It binds the accepted freeze to the exact 10,000-row frame, verifies non-null unique keys, 207 allocation cells, probability/weight reciprocity, and every 800-record arm linkage. It supports correcting the C-arm wording from missing weights to structurally null legacy A/B fields with complete dedicated fields. It does not justify parent-frame inference: the 718 exclusions and 9,282 eligible count remain attributed to the bound freeze receipt, and excluded weight mass was not reconstructed.

No material engineering issue remains open.
