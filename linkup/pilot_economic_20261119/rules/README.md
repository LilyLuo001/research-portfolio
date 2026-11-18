# Bounded CPU candidate pilot

This package reuses the existing LinkUp rulefirst-v1.2 and frozen V5 vocabulary.
It makes no network or model calls. It emits **candidates**, never accepted
semantic values, absence claims, posting minima, or latent seniority labels.
The package does not read or change the old accepted corpus outputs.

## Reuse and versions

`REUSE_MANIFEST.json` lists exact source files, SHA-256 hashes, and copied
assignments. The assignments in `frozen_vocabulary.py` were copied from:

* `rule_engine.py`, version `rulefirst-20261008-v1.2`, SHA-256
  `e429463ddfe947587c5d1afaea2aa87ab287bf91144496e09c7819bb53f71526`.
* `legacy_v5_frozen.py`, normalizer family `recruitment-html-text-v5`, SHA-256
  `336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd`.

The candidate wrapper reuses the four experience families, technology
categories, exact term vocabularies, degree levels, waiver phrases, strength
cues, and heading vocabulary. It does not execute the old normalizer, old
semantic flags, or any D67/corpus-production rerun. Degree spellings without a
following "degree", range syntax, strict upper bounds, and C++/C# word
boundaries are explicit candidate-layer changes. Regexes are compiled once.

`VERSION`/`CACHE_VERSION` is `linkup-cpu-candidates-20261119-v1`.
`ENGINE_SHA256` hashes the exact bytes of `cpu_candidates.py` and
`frozen_vocabulary.py` with fixed filenames and separators. Code changes
therefore invalidate the cache even if the human-readable version is unchanged.

## Python interface

```python
from rules import extract, cache_key, CACHE_VERSION, ENGINE_SHA256

result = extract(full_document, ["experience.general_work.years", "technology"])
```

`text` must be a string. `missing_fields` must be an explicit iterable of
nonempty strings; an empty iterable is a no-op. Non-string input or malformed
field selection raises `TypeError`. Fields are sorted and deduplicated.
There is no input mutation, filesystem write, or source-body persistence in
`extract`. The result is JSON-serializable.

Supported routing families:

| Requested field | Candidate kinds |
| --- | --- |
| `experience`, or one of `experience.general_work`, `experience.occupation_task`, `experience.industry_domain`, `experience.tool_specific` and its subfields | Duration, experience mention, explicit waiver |
| `education`, `education.*`, `degree`, `degrees` | Degree mention, using frozen degree levels |
| `technology`, `technology.*`, `tool`, `tools`, `ai` | Exact keyword hits using frozen `genai`, `predictive_ai`, `ai_unspecified`, `software` categories |
| `entry.explicit_no_experience` and its subfields | Explicit waiver phrase |

Other fields are `unsupported_unknown`, including junior/entry status,
responsibility, and mentoring. "Mentor junior engineers" is not converted into
an entry-level claim about the advertised worker.

Top-level return fields:

* `status`: `processed`, `empty_input`, `no_fields_requested`,
  `input_limit_exceeded`, or `candidate_limit_exceeded`.
* `candidate_only: true`, `resolved_fields: []`, `field_updates: {}` always.
* `version`, `cache_version`, `engine_sha256`, `source_text_sha256`, `cache_key`.
* `requested_fields`, `unsupported_fields`, `field_status`. A supported field
  has `candidates_present_unknown` or `no_rule_hit_unknown`, with candidate
  counts. **No hit never means no requirement.**
* `candidates`, `candidate_count_before_limit`, `candidates_truncated`.
* `excluded_spans`, `excluded_span_count`, `excluded_spans_truncated`, and
  `document_flags`.

Every candidate carries `kind`, `target_fields`, `match`, `clause`, `sentence`,
`section`, `strength_cue`, `scope_cues`, `subject_cues`, `actor_cue`,
`subject_assignment: "unresolved"`, `semantic_status: "unknown"`, and
`review_reasons`. Span dictionaries have `start`, `end`, `quote` such that
`text[start:end] == quote`. Coordinates are half-open Python Unicode codepoint
indices into **the exact supplied string**, including Unicode and CRLF. HTML is
not normalized; markup is flagged. The caller must retain the pinned full text
and its normalization provenance.

`target_fields` routes review candidates to requested missing fields; it is
**not** a claim that the duration belongs to each routed experience family.
`subject_cues` records co-occurring frozen vocabulary only. Bare "5 years of
experience" has no inferred general/industry/occupation/tool subject. A phrase
with both general and industry cues remains unresolved.

A duration candidate adds `duration` with `kind`, `stated_value`,
`lower_years`, `upper_years`, strictness flags, original units and modifiers,
and `is_posting_minimum: false`. Bounds describe the literal span, not an
unconditional admission threshold. `stated_unspecified` is distinct from
`minimum`, `maximum`, `exact`, and `range`. Months divide by 12; part-time
duration is flagged and is not converted into full-time-equivalent years.
Inconsistent parenthetical numbers and reversed ranges keep unresolved bounds.
At most the nearest two lexical experience anchors are retained alongside the
total anchor count; association is not inferred from proximity.

OR, substitution, negation, mixed required/preferred, multiple durations,
equivalence ratios, and nearby standalone multiline OR retain review flags and
original supporting context. Explicit age/contract/degree-program/company
history durations are excluded with a reason. Other ambiguous numbers remain
candidates; no semantic guarantee is made. Questionnaire and nonqualification
sections are retained with scope warnings rather than classified as requirements.

Bounds: 500,000 input characters, 1,024 retained candidates, 1,024 retained
excluded spans, and 8,192 characters per clause/sentence quote. Oversized input
is not silently sampled. Longer contexts have `truncated: true`, exact excerpt
coordinates, and `full_start`/`full_end` for recovery from retained full text.
Candidate limits are explicit and never establish completed semantic coverage.
The number grammar retains the existing one/two-digit and selected spelled-out
number coverage, with added 13–19. This and the frozen keyword vocabulary are
known recall limits. Tests do not prove corpus recall or semantic accuracy.

## Cloud batch entry point

Run only where private source data already resides. The local package contains
code and synthetic fixtures, not advertisement bodies. Example cloud command:

```sh
python3 /home/linkup/migration/pilot_economic_20261119/run01/rules/run_cpu_batch.py \
  --input /home/linkup/migration/pilot_economic_20261119/run01/preparation/batch0001/INPUTS_PRIVATE.jsonl \
  --output /home/linkup/migration/pilot_economic_20261119/run01/preparation/batch0001/CPU_RULE_RESULTS_PRIVATE.jsonl \
  --receipt /home/linkup/migration/pilot_economic_20261119/run01/preparation/batch0001/CPU_RULE_RECEIPT_PUBLIC.json \
  --cache /home/linkup/migration/pilot_economic_20261119/run01/cache/cpu_rules.sqlite \
  --max-records 10000
```

Each input is `{case, row:{record_id,context_sha256,full_document}, ...}`.
The SHA must equal the exact UTF-8 `full_document` hash. Missing fields are
selected from `row.missing_fields`, then envelope `missing_fields`, then the
declared default (the four experience families, education, technology, and
explicit no-experience). The default is authorized for newly prepared inputs;
when attaching candidates to existing accepted records, supply the actual
missing-field list, including an empty list for fully accepted records.

Every physical JSONL input line gets a private output keyed by context SHA,
including no-hit rows and input failures. Input order and row hash are retained.
No original record ID, case label, or source body is copied into public receipts.
The private SQLite cache is keyed by exact text hash, code hash/version, and
sorted missing-field set. Cache payload SHA and evidence offsets are verified.
Invalid cache entries are counted and recomputed; accepted corpus values are
never loaded or replaced. Different missing-field sets do not share cache keys.

Output is written through a private `.partial` file. An identical completed
input/code/output/field-default receipt is verified and reused. Other existing
outputs are not overwritten. Failed/limited rows make the run `incomplete` and
return exit 2. Input limit failure keeps the partial file explicitly unpublished.
Receipts include actual timing, counts, SHA provenance, cache activity, and
zero model/network calls; they are not a full-target completion claim.

## Existing-citation literal coverage

`literal_coverage.py` can compare existing model citations without inference.
Provide source inputs in the same JSONL shape and a provenance-preserving
reference projection:

```json
{"context_sha256":"<exact source SHA>","evidence":[{"quote":"3 years of experience","start":100,"end":121}]}
```

Use `--inputs`, `--references`, `--receipt`, `--private-detail`, and optionally
`--rule-results`. If rules are absent, the comparator makes bounded in-memory
CPU candidates. Quote-only citations are admitted only if unique in the exact
source. Ambiguous locations, invalid offsets, missing sources, and duplicates
have distinct counts. The denominator is unique duration spans identified by
the **frozen** YEARS grammar in exactly verified citations; the numerator is
spans fully contained in a CPU experience-duration candidate. This measures
literal citation coverage only. It is not precision, population recall,
semantic accuracy, or approval of the old model's interpretation.

## Synthetic verification

```sh
python3 -m unittest -v test_cpu_candidates test_run_cpu_batch test_literal_coverage
```

Fixtures cover OR degrees/experience, multiline alternatives, ranges,
required/preferred, part-time months, no experience, age/history exclusions,
advertised worker versus mentees, exact lexical offsets, unknown/no-hit,
missing-field preservation, cache identity/corruption, bounded outputs, and
literal-citation bookkeeping. `SYNTHETIC_QA_PUBLIC.json` records the actual local
synthetic test run; it is not charged model usage or a real-corpus validation.
