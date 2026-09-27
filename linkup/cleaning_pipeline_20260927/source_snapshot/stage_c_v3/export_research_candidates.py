#!/usr/bin/env python3
"""Export narrow, auditable research-candidate tables from parser output.

The outputs remain candidates for validation.  In particular, ``no_candidate``
does not mean that an advertisement has no requirement, and qualification
relation rows do not claim a complete AND/OR path graph.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pyarrow as pa
import pyarrow.parquet as pq


EXPORTER_VERSION = "research-candidate-export-v1"
MAX_ADS = 30_000
MODULES = ("software", "ai", "experience", "education", "tasks")
OUTPUT_FILES = (
    "ad_candidate_status.parquet",
    "requirement_evidence.parquet",
    "qualification_relation_candidates.parquet",
)
SOURCE_KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_id(prefix: str, values: Iterable[Any]) -> str:
    encoded = json.dumps(list(values), ensure_ascii=False, separators=(",", ":"), default=str)
    return "%s_%s" % (prefix, hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24])


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _optional_text(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _optional_float(value: Any) -> Optional[float]:
    return None if value is None else float(value)


def _optional_int(value: Any) -> Optional[int]:
    return None if value is None else int(value)


def _source_tuple(row: Mapping[str, Any]) -> Tuple[str, str, int]:
    return (str(row["JOB_HASH"]), str(row["SOURCE_FILE"]), int(row["SOURCE_ROW"]))


def _schema_names(path: Path) -> set:
    return set(pq.ParquetFile(path).schema_arrow.names)


def _read_inputs(sample_path: Path, candidate_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    sample_names = _schema_names(sample_path)
    candidate_names = _schema_names(candidate_path)
    required_sample = set(SOURCE_KEY)
    required_candidate = set(SOURCE_KEY) | {"CANDIDATE_JSON", "STATUS"}
    if not required_sample.issubset(sample_names):
        raise ValueError("sample missing columns: %s" % sorted(required_sample - sample_names))
    if not required_candidate.issubset(candidate_names):
        raise ValueError("candidate features missing columns: %s" % sorted(required_candidate - candidate_names))

    sample_columns = [
        name for name in (
            "JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW",
            "COUNTRY", "COUNTRY_GROUP", "STATE", "COHORT", "CREATED",
            "LAST_UPDATED", "LAST_CHECKED", "DELETE_DATE", "BOUNDARY_STATUS",
            "JAN01_STATUS", "SAMPLE_HASH",
        ) if name in sample_names
    ]
    candidate_columns = [
        name for name in (
            "JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "COUNTRY_GROUP", "COHORT",
            "RAW_SHA256", "NORMALIZED_SHA256", "STATUS", "CANDIDATE_JSON",
        ) if name in candidate_names
    ]
    samples = pq.read_table(sample_path, columns=sample_columns).to_pylist()
    candidates = pq.read_table(candidate_path, columns=candidate_columns).to_pylist()
    return samples, candidates


def _validate_source_rows(samples: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]]) -> None:
    if not samples or len(samples) > MAX_ADS:
        raise ValueError("sample row count must be between 1 and %d; got %d" % (MAX_ADS, len(samples)))
    if len(candidates) != len(samples):
        raise ValueError("source row count invariant failed: sample=%d candidates=%d" % (len(samples), len(candidates)))
    sample_keys = [_source_tuple(row) for row in samples]
    candidate_keys = [_source_tuple(row) for row in candidates]
    if len(set(sample_keys)) != len(sample_keys):
        raise ValueError("sample source key is not unique")
    if len(set(candidate_keys)) != len(candidate_keys):
        raise ValueError("candidate source key is not unique")
    if set(sample_keys) != set(candidate_keys):
        missing = sorted(set(sample_keys) - set(candidate_keys))[:3]
        extra = sorted(set(candidate_keys) - set(sample_keys))[:3]
        raise ValueError("source keys differ; missing=%r extra=%r" % (missing, extra))


def _parse_payload(row: Mapping[str, Any]) -> Dict[str, Any]:
    try:
        payload = json.loads(row["CANDIDATE_JSON"])
    except Exception as exc:
        raise ValueError("invalid CANDIDATE_JSON for %r: %s" % (_source_tuple(row), exc))
    if not isinstance(payload, dict) or not isinstance(payload.get("summary"), dict) or not isinstance(payload.get("evidence"), list):
        raise ValueError("malformed candidate payload for %r" % (_source_tuple(row),))
    return payload


def _common_source(sample: Mapping[str, Any], candidate: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "JOB_HASH": str(sample["JOB_HASH"]),
        "SOURCE_FILE": str(sample["SOURCE_FILE"]),
        "SOURCE_ROW": int(sample["SOURCE_ROW"]),
        "RECORD_SOURCE_ROW": _optional_int(sample.get("RECORD_SOURCE_ROW")),
        "COUNTRY": _optional_text(sample.get("COUNTRY")),
        "COUNTRY_GROUP": _optional_text(sample.get("COUNTRY_GROUP", candidate.get("COUNTRY_GROUP"))),
        "STATE": _optional_text(sample.get("STATE")),
        "COHORT": _optional_text(sample.get("COHORT", candidate.get("COHORT"))),
        "CREATED": sample.get("CREATED"),
        "LAST_UPDATED": sample.get("LAST_UPDATED"),
        "LAST_CHECKED": sample.get("LAST_CHECKED"),
        "DELETE_DATE": sample.get("DELETE_DATE"),
        "BOUNDARY_STATUS": _optional_text(sample.get("BOUNDARY_STATUS")),
        "JAN01_STATUS": _optional_text(sample.get("JAN01_STATUS")),
        "SAMPLE_HASH": _optional_text(sample.get("SAMPLE_HASH")),
        "EVIDENCE_TIME_STATUS": "unknown",
    }


def _build_tables(
    samples: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    parser_sha256: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    candidate_by_key = {_source_tuple(row): row for row in candidates}
    ads: List[Dict[str, Any]] = []
    evidence_rows: List[Dict[str, Any]] = []
    relation_rows: List[Dict[str, Any]] = []

    for sample in samples:
        candidate = candidate_by_key[_source_tuple(sample)]
        payload = _parse_payload(candidate)
        common = _common_source(sample, candidate)
        summaries = payload["summary"]
        truncation = payload.get("module_evidence_truncated") or {}
        ad_id = _stable_id("ad", _source_tuple(sample))
        ad: Dict[str, Any] = dict(common)
        ad.update({
            "AD_CANDIDATE_ID": ad_id,
            "RAW_SHA256": _optional_text(candidate.get("RAW_SHA256", payload.get("source_fingerprint_sha256"))),
            "NORMALIZED_SHA256": _optional_text(candidate.get("NORMALIZED_SHA256", payload.get("normalized_text_fingerprint_sha256"))),
            "INPUT_STATUS": _optional_text(candidate.get("STATUS")),
            "PARSER_VERSION": _optional_text(payload.get("normalization_version")),
            "PARSER_SHA256": parser_sha256,
            "OFFSET_COORDINATE_SYSTEM": _optional_text(payload.get("offset_coordinate_system")),
            "CANDIDATE_ONLY": bool(payload.get("candidate_only", True)),
            "PARSE_ERROR_COUNT": len(payload.get("errors") or []),
            "PARSE_ERRORS_JSON": _canonical_json(payload.get("errors") or []),
            "EVIDENCE_LIMIT": _optional_int(payload.get("evidence_limit")),
            "EVIDENCE_RETURNED_COUNT": len(payload["evidence"]),
            "EVIDENCE_TOTAL_BEFORE_TRUNCATION": _optional_int(payload.get("evidence_total_before_truncation")),
            "EVIDENCE_TRUNCATED": bool(payload.get("evidence_truncated", False)),
        })
        for module in MODULES:
            summary = summaries.get(module) or {}
            upper = module.upper()
            ad[upper + "_STATUS"] = _optional_text(summary.get("status", "parse_error"))
            ad[upper + "_CANDIDATE_COUNT"] = _optional_int(summary.get("candidate_count"))
            ad[upper + "_REQUIREMENT_CANDIDATE_COUNT"] = _optional_int(summary.get("requirement_candidate_count"))
            ad[upper + "_EVIDENCE_TRUNCATED"] = bool(truncation.get(module, False))
        ads.append(ad)

        normalized_text = payload.get("normalized_text")
        for ordinal, item in enumerate(payload["evidence"]):
            if not isinstance(item, dict):
                raise ValueError("non-object evidence for %r" % (_source_tuple(sample),))
            start, end = _optional_int(item.get("start")), _optional_int(item.get("end"))
            if start is None or end is None or start < 0 or end < start:
                raise ValueError("invalid evidence span for %r" % (_source_tuple(sample),))
            matched = _optional_text(item.get("matched_text"))
            if isinstance(normalized_text, str) and normalized_text[start:end] != (matched or ""):
                raise ValueError("evidence offset mismatch for %r at %d:%d" % (_source_tuple(sample), start, end))
            module = _optional_text(item.get("module"))
            candidate_type = _optional_text(item.get("candidate_type"))
            evidence_id = _stable_id(
                "ev", (*_source_tuple(sample), module, candidate_type, start, end, item.get("value"))
            )
            detail = {key: value for key, value in item.items() if key not in {
                "module", "candidate_type", "value", "start", "end", "snippet",
                "snippet_start", "snippet_end", "context", "requirement_strength",
                "candidate_only", "is_applicant_requirement", "scope", "matched_text",
                "min_years", "max_years", "min_duration", "max_duration",
                "duration_unit", "has_explicit_duration", "bound_type", "negated",
                "negated_or_optional", "no_experience_explicit",
            }}
            ev = dict(common)
            ev.update({
                "AD_CANDIDATE_ID": ad_id,
                "EVIDENCE_ID": evidence_id,
                "EVIDENCE_ORDINAL": ordinal,
                "MODULE": module,
                "CANDIDATE_TYPE": candidate_type,
                "VALUE": _optional_text(item.get("value")),
                "MATCHED_TEXT": matched,
                "EVIDENCE_START": start,
                "EVIDENCE_END": end,
                "SNIPPET": _optional_text(item.get("snippet")),
                "SNIPPET_START": _optional_int(item.get("snippet_start")),
                "SNIPPET_END": _optional_int(item.get("snippet_end")),
                "CONTEXT": _optional_text(item.get("context")),
                "REQUIREMENT_STRENGTH": _optional_text(item.get("requirement_strength")),
                "IS_APPLICANT_REQUIREMENT_CANDIDATE": bool(item.get("is_applicant_requirement", False)),
                "CANDIDATE_ONLY": bool(item.get("candidate_only", True)),
                "NEGATED": bool(item.get("negated", False)),
                "NEGATED_OR_OPTIONAL": bool(item.get("negated_or_optional", False)),
                "NO_EXPERIENCE_EXPLICIT": bool(item.get("no_experience_explicit", False)),
                "EXPERIENCE_SCOPE": _optional_text(item.get("scope")) if module == "experience" else None,
                "MIN_YEARS": _optional_float(item.get("min_years")),
                "MAX_YEARS": _optional_float(item.get("max_years")),
                "MIN_DURATION": _optional_float(item.get("min_duration")),
                "MAX_DURATION": _optional_float(item.get("max_duration")),
                "DURATION_UNIT": _optional_text(item.get("duration_unit")),
                "HAS_EXPLICIT_DURATION": item.get("has_explicit_duration"),
                "BOUND_TYPE": _optional_text(item.get("bound_type")),
                "PARSER_VERSION": _optional_text(payload.get("normalization_version")),
                "PARSER_SHA256": parser_sha256,
                "OFFSET_COORDINATE_SYSTEM": _optional_text(payload.get("offset_coordinate_system")),
                "AD_EVIDENCE_TRUNCATED": bool(payload.get("evidence_truncated", False)),
                "MODULE_EVIDENCE_TRUNCATED": bool(truncation.get(module or "", False)),
                "DETAIL_JSON": _canonical_json(detail),
            })
            evidence_rows.append(ev)

            relation_kind: Optional[str] = None
            if item.get("equivalence_type") == "credential_equivalent" or item.get("equivalent_credential"):
                relation_kind = "EQUIVALENT_CREDENTIAL_CANDIDATE"
            elif (
                item.get("equivalence_type") == "experience_alternative"
                or item.get("alternative_training_or_experience")
                or item.get("alternative_training_or_education")
                or item.get("equivalent_experience")
            ):
                relation_kind = "ALTERNATIVE_PATH_CANDIDATE"
            if relation_kind:
                parser_scope_start = _optional_int(item.get("qualification_scope_start"))
                parser_scope_end = _optional_int(item.get("qualification_scope_end"))
                parser_scope_text = _optional_text(item.get("qualification_scope_text"))
                scope_start = parser_scope_start
                scope_end = parser_scope_end
                scope_whitespace_trimmed = False
                scope_left_trim = 0
                scope_right_trim = 0
                if scope_start is None or scope_end is None:
                    # Some candidate flags provide broader alternative text but
                    # no coordinates for it.  Cite only the reliably located
                    # evidence span and retain the broader text in DETAIL_JSON.
                    scope_start, scope_end = start, end
                    scope_text = matched
                else:
                    scope_text = parser_scope_text
                    if isinstance(normalized_text, str):
                        actual_scope = normalized_text[scope_start:scope_end]
                        if actual_scope != (scope_text or ""):
                            if actual_scope.strip() != (scope_text or ""):
                                raise ValueError("qualification scope offset mismatch for %r" % (_source_tuple(sample),))
                            scope_left_trim = len(actual_scope) - len(actual_scope.lstrip())
                            scope_right_trim = len(actual_scope) - len(actual_scope.rstrip())
                            scope_start += scope_left_trim
                            scope_end -= scope_right_trim
                            scope_whitespace_trimmed = True
                relation_rows.append({
                    **common,
                    "AD_CANDIDATE_ID": ad_id,
                    "RELATION_CANDIDATE_ID": _stable_id("rel", (evidence_id, relation_kind, scope_start, scope_end)),
                    "SOURCE_EVIDENCE_ID": evidence_id,
                    "RELATION_TYPE_CANDIDATE": relation_kind,
                    "RELATION_RESOLUTION_STATUS": "unresolved_candidate",
                    "COMPLETE_PATH_GRAPH": False,
                    "PATH_ID": None,
                    "RELATED_EVIDENCE_IDS_JSON": "[]",
                    "SCOPE_TEXT": scope_text,
                    "SCOPE_START": scope_start,
                    "SCOPE_END": scope_end,
                    "SCOPE_RULE": _optional_text(item.get("qualification_scope_rule")),
                    "EVIDENCE_START": start,
                    "EVIDENCE_END": end,
                    "PARSER_VERSION": _optional_text(payload.get("normalization_version")),
                    "PARSER_SHA256": parser_sha256,
                    "AD_EVIDENCE_TRUNCATED": bool(payload.get("evidence_truncated", False)),
                    "MODULE_EVIDENCE_TRUNCATED": bool(truncation.get(module or "", False)),
                    "DETAIL_JSON": _canonical_json({
                        **{
                            key: item.get(key) for key in (
                            "equivalence_type", "equivalent_credential", "equivalent_experience",
                            "alternative_training_or_experience", "alternative_training_or_education",
                            "alternative_path_text", "local_path_scope_applied",
                            ) if key in item
                        },
                        "parser_qualification_scope_text": parser_scope_text,
                        "parser_qualification_scope_start": parser_scope_start,
                        "parser_qualification_scope_end": parser_scope_end,
                        "exporter_scope_whitespace_trimmed": scope_whitespace_trimmed,
                        "exporter_scope_left_trim_codepoints": scope_left_trim,
                        "exporter_scope_right_trim_codepoints": scope_right_trim,
                    }),
                })
    return ads, evidence_rows, relation_rows


def _table(rows: Sequence[Mapping[str, Any]], empty_schema: pa.Schema) -> pa.Table:
    return pa.Table.from_pylist(list(rows), schema=empty_schema)


SOURCE_FIELDS = [
    pa.field("JOB_HASH", pa.string()),
    pa.field("SOURCE_FILE", pa.string()),
    pa.field("SOURCE_ROW", pa.int64()),
    pa.field("RECORD_SOURCE_ROW", pa.int64()),
    pa.field("COUNTRY", pa.string()),
    pa.field("COUNTRY_GROUP", pa.string()),
    pa.field("STATE", pa.string()),
    pa.field("COHORT", pa.string()),
    pa.field("CREATED", pa.timestamp("us")),
    pa.field("LAST_UPDATED", pa.timestamp("us")),
    pa.field("LAST_CHECKED", pa.timestamp("us")),
    pa.field("DELETE_DATE", pa.timestamp("us")),
    pa.field("BOUNDARY_STATUS", pa.string()),
    pa.field("JAN01_STATUS", pa.string()),
    pa.field("SAMPLE_HASH", pa.string()),
    pa.field("EVIDENCE_TIME_STATUS", pa.string()),
]

AD_SCHEMA = pa.schema(SOURCE_FIELDS + [
    pa.field("AD_CANDIDATE_ID", pa.string()),
    pa.field("RAW_SHA256", pa.string()),
    pa.field("NORMALIZED_SHA256", pa.string()),
    pa.field("INPUT_STATUS", pa.string()),
    pa.field("PARSER_VERSION", pa.string()),
    pa.field("PARSER_SHA256", pa.string()),
    pa.field("OFFSET_COORDINATE_SYSTEM", pa.string()),
    pa.field("CANDIDATE_ONLY", pa.bool_()),
    pa.field("PARSE_ERROR_COUNT", pa.int64()),
    pa.field("PARSE_ERRORS_JSON", pa.string()),
    pa.field("EVIDENCE_LIMIT", pa.int64()),
    pa.field("EVIDENCE_RETURNED_COUNT", pa.int64()),
    pa.field("EVIDENCE_TOTAL_BEFORE_TRUNCATION", pa.int64()),
    pa.field("EVIDENCE_TRUNCATED", pa.bool_()),
] + [
    pa.field(module.upper() + suffix, kind)
    for module in MODULES
    for suffix, kind in (
        ("_STATUS", pa.string()),
        ("_CANDIDATE_COUNT", pa.int64()),
        ("_REQUIREMENT_CANDIDATE_COUNT", pa.int64()),
        ("_EVIDENCE_TRUNCATED", pa.bool_()),
    )
])

EVIDENCE_SCHEMA = pa.schema(SOURCE_FIELDS + [
    pa.field("AD_CANDIDATE_ID", pa.string()),
    pa.field("EVIDENCE_ID", pa.string()),
    pa.field("EVIDENCE_ORDINAL", pa.int64()),
    pa.field("MODULE", pa.string()),
    pa.field("CANDIDATE_TYPE", pa.string()),
    pa.field("VALUE", pa.string()),
    pa.field("MATCHED_TEXT", pa.string()),
    pa.field("EVIDENCE_START", pa.int64()),
    pa.field("EVIDENCE_END", pa.int64()),
    pa.field("SNIPPET", pa.string()),
    pa.field("SNIPPET_START", pa.int64()),
    pa.field("SNIPPET_END", pa.int64()),
    pa.field("CONTEXT", pa.string()),
    pa.field("REQUIREMENT_STRENGTH", pa.string()),
    pa.field("IS_APPLICANT_REQUIREMENT_CANDIDATE", pa.bool_()),
    pa.field("CANDIDATE_ONLY", pa.bool_()),
    pa.field("NEGATED", pa.bool_()),
    pa.field("NEGATED_OR_OPTIONAL", pa.bool_()),
    pa.field("NO_EXPERIENCE_EXPLICIT", pa.bool_()),
    pa.field("EXPERIENCE_SCOPE", pa.string()),
    pa.field("MIN_YEARS", pa.float64()),
    pa.field("MAX_YEARS", pa.float64()),
    pa.field("MIN_DURATION", pa.float64()),
    pa.field("MAX_DURATION", pa.float64()),
    pa.field("DURATION_UNIT", pa.string()),
    pa.field("HAS_EXPLICIT_DURATION", pa.bool_()),
    pa.field("BOUND_TYPE", pa.string()),
    pa.field("PARSER_VERSION", pa.string()),
    pa.field("PARSER_SHA256", pa.string()),
    pa.field("OFFSET_COORDINATE_SYSTEM", pa.string()),
    pa.field("AD_EVIDENCE_TRUNCATED", pa.bool_()),
    pa.field("MODULE_EVIDENCE_TRUNCATED", pa.bool_()),
    pa.field("DETAIL_JSON", pa.string()),
])

RELATION_SCHEMA = pa.schema(SOURCE_FIELDS + [
    pa.field("AD_CANDIDATE_ID", pa.string()),
    pa.field("RELATION_CANDIDATE_ID", pa.string()),
    pa.field("SOURCE_EVIDENCE_ID", pa.string()),
    pa.field("RELATION_TYPE_CANDIDATE", pa.string()),
    pa.field("RELATION_RESOLUTION_STATUS", pa.string()),
    pa.field("COMPLETE_PATH_GRAPH", pa.bool_()),
    pa.field("PATH_ID", pa.string()),
    pa.field("RELATED_EVIDENCE_IDS_JSON", pa.string()),
    pa.field("SCOPE_TEXT", pa.string()),
    pa.field("SCOPE_START", pa.int64()),
    pa.field("SCOPE_END", pa.int64()),
    pa.field("SCOPE_RULE", pa.string()),
    pa.field("EVIDENCE_START", pa.int64()),
    pa.field("EVIDENCE_END", pa.int64()),
    pa.field("PARSER_VERSION", pa.string()),
    pa.field("PARSER_SHA256", pa.string()),
    pa.field("AD_EVIDENCE_TRUNCATED", pa.bool_()),
    pa.field("MODULE_EVIDENCE_TRUNCATED", pa.bool_()),
    pa.field("DETAIL_JSON", pa.string()),
])


def _validate_outputs(
    ads: Sequence[Mapping[str, Any]], evidence: Sequence[Mapping[str, Any]], relations: Sequence[Mapping[str, Any]], source_count: int
) -> None:
    if len(ads) != source_count:
        raise AssertionError("ad output row count invariant failed")
    if len({row["AD_CANDIDATE_ID"] for row in ads}) != len(ads):
        raise AssertionError("AD_CANDIDATE_ID is not unique")
    if len({row["EVIDENCE_ID"] for row in evidence}) != len(evidence):
        raise AssertionError("EVIDENCE_ID is not unique")
    if len({row["RELATION_CANDIDATE_ID"] for row in relations}) != len(relations):
        raise AssertionError("RELATION_CANDIDATE_ID is not unique")
    ad_ids = {row["AD_CANDIDATE_ID"] for row in ads}
    evidence_ids = {row["EVIDENCE_ID"] for row in evidence}
    if any(row["AD_CANDIDATE_ID"] not in ad_ids for row in evidence):
        raise AssertionError("orphan evidence row")
    if any(row["SOURCE_EVIDENCE_ID"] not in evidence_ids for row in relations):
        raise AssertionError("orphan relation candidate row")
    if any(row["COMPLETE_PATH_GRAPH"] or row["RELATION_RESOLUTION_STATUS"] != "unresolved_candidate" for row in relations):
        raise AssertionError("relation candidates must remain unresolved")


def _identity(sample: Path, candidates: Path, parser_source: Path) -> Dict[str, Any]:
    return {
        "exporter_version": EXPORTER_VERSION,
        "exporter_sha256": _sha256_file(Path(__file__).resolve()),
        "sample_path": str(sample.resolve()),
        "sample_sha256": _sha256_file(sample),
        "candidate_path": str(candidates.resolve()),
        "candidate_sha256": _sha256_file(candidates),
        "parser_source_path": str(parser_source.resolve()),
        "parser_sha256": _sha256_file(parser_source),
        "max_ads": MAX_ADS,
    }


def _existing_exact(out_dir: Path, identity: Mapping[str, Any]) -> bool:
    receipt_path = out_dir / "COMPLETE.json"
    if not receipt_path.is_file():
        return False
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if receipt.get("identity") != identity:
        return False
    output_hashes = receipt.get("output_sha256") or {}
    return all(
        (out_dir / name).is_file() and output_hashes.get(name) == _sha256_file(out_dir / name)
        for name in OUTPUT_FILES
    )


def export(sample: Path, candidates: Path, out_dir: Path, parser_source: Path) -> Dict[str, Any]:
    sample, candidates, out_dir, parser_source = map(Path, (sample, candidates, out_dir, parser_source))
    for path in (sample, candidates, parser_source):
        if not path.is_file():
            raise FileNotFoundError(path)
    identity = _identity(sample, candidates, parser_source)
    if out_dir.exists():
        if _existing_exact(out_dir, identity):
            return json.loads((out_dir / "COMPLETE.json").read_text(encoding="utf-8"))
        raise FileExistsError("immutable output exists without an exact valid receipt: %s" % out_dir)

    sample_rows, candidate_rows = _read_inputs(sample, candidates)
    _validate_source_rows(sample_rows, candidate_rows)
    ads, evidence, relations = _build_tables(sample_rows, candidate_rows, identity["parser_sha256"])
    _validate_outputs(ads, evidence, relations, len(sample_rows))

    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=out_dir.name + ".tmp.", dir=str(out_dir.parent)))
    try:
        tables = {
            "ad_candidate_status.parquet": _table(ads, AD_SCHEMA),
            "requirement_evidence.parquet": _table(evidence, EVIDENCE_SCHEMA),
            "qualification_relation_candidates.parquet": _table(relations, RELATION_SCHEMA),
        }
        for name, table in tables.items():
            pq.write_table(table, tmp_dir / name, compression="zstd")
        disk_counts = {name: pq.ParquetFile(tmp_dir / name).metadata.num_rows for name in OUTPUT_FILES}
        expected_counts = {
            "ad_candidate_status.parquet": len(ads),
            "requirement_evidence.parquet": len(evidence),
            "qualification_relation_candidates.parquet": len(relations),
        }
        if disk_counts != expected_counts:
            raise AssertionError("written row counts differ: %r != %r" % (disk_counts, expected_counts))
        receipt = {
            "status": "complete",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "identity": identity,
            "source_row_count": len(sample_rows),
            "output_row_counts": disk_counts,
            "output_sha256": {name: _sha256_file(tmp_dir / name) for name in OUTPUT_FILES},
            "candidate_only": True,
            "no_candidate_is_no_requirement": False,
            "relations_are_complete_path_graphs": False,
            "evidence_time_status": "unknown",
            "known_limitations": [
                "Parser applicant/unconditional booleans are unvalidated candidate attributes; this exporter does not convert them to validated labels.",
                "Compound credential-and-experience alternatives may be only partially flagged, so relation rows cite local evidence and remain unresolved rather than forming an AND/OR graph.",
                "The parser can miss cross-line forms such as an Experience heading followed by a duration plus trailing domain text; no_candidate therefore does not mean no requirement.",
                "Evidence is bounded by the parser evidence limit; ad-level and module-level truncation flags must accompany downstream use.",
            ],
        }
        receipt_tmp = tmp_dir / "COMPLETE.json.tmp"
        receipt_tmp.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(receipt_tmp, tmp_dir / "COMPLETE.json")
        os.replace(tmp_dir, out_dir)
        return receipt
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--parser-source", type=Path, default=Path(__file__).with_name("requirement_candidates.py"),
        help="exact parser source used to create candidate features (default: v3 sibling)",
    )
    args = parser.parse_args(argv)
    try:
        receipt = export(args.sample, args.candidates, args.out, args.parser_source)
    except Exception as exc:
        print("ERROR: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
