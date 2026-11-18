#!/usr/bin/env python3
"""Audit literal duration-span coverage in existing cited evidence, without models.

Reference JSONL contract: {context_sha256, evidence:[{quote,start?,end?}, ...]}.
Offsets must address the exact retained full_document. Quote-only references
are admitted only when they match the source exactly once. Caller adapters must
preserve the existing citation provenance; this script does not invent evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

try:
    from . import cpu_candidates as engine
    from . import frozen_vocabulary as frozen
    from .run_cpu_batch import atomic_json, canonical, digest
except ImportError:
    import cpu_candidates as engine
    import frozen_vocabulary as frozen
    from run_cpu_batch import atomic_json, canonical, digest


def compare(documents, references, rule_results=None):
    """Return public counters and private details; no semantic correctness score."""
    counts = Counter()
    details = []
    seen_spans = set()
    candidates_by_sha = {}
    for reference in references:
        counts["reference_records"] += 1
        sha = reference.get("context_sha256")
        if sha not in documents:
            counts["reference_records_without_exact_source"] += 1
            continue
        text = documents[sha]
        if sha not in candidates_by_sha:
            result = (rule_results or {}).get(sha)
            if result is None:
                result = engine.extract(text, ("experience",))
                counts["contexts_cpu_extracted_in_this_audit"] += 1
            elif result.get("source_text_sha256") != sha or result.get("engine_sha256") != engine.ENGINE_SHA256:
                raise ValueError("rule_result_identity_mismatch")
            candidates_by_sha[sha] = [item["match"] for item in result["candidates"] if item["kind"] == "experience_duration"]
            if result.get("candidates_truncated"):
                counts["contexts_with_candidate_limit"] += 1
        evidence = reference.get("evidence", [])
        if not isinstance(evidence, list):
            counts["records_with_invalid_evidence_container"] += 1
            continue
        for citation in evidence:
            counts["citations_seen"] += 1
            if not isinstance(citation, dict) or not isinstance(citation.get("quote"), str) or not citation["quote"]:
                counts["invalid_citations"] += 1
                continue
            quote = citation["quote"]
            start, end = citation.get("start"), citation.get("end")
            if start is None and end is None:
                start = text.find(quote)
                if start < 0:
                    counts["citations_without_exact_source_match"] += 1
                    continue
                if text.find(quote, start + 1) >= 0:
                    counts["citations_with_ambiguous_quote_location"] += 1
                    continue
                end = start + len(quote)
            if (not isinstance(start, int) or not isinstance(end, int)
                    or not 0 <= start <= end <= len(text) or text[start:end] != quote):
                counts["citations_with_invalid_offsets"] += 1
                continue
            counts["citations_exactly_verified"] += 1
            matches = list(frozen.YEARS.finditer(quote))
            if not matches:
                counts["verified_citations_without_frozen_duration_grammar_hit"] += 1
            for match in matches:
                left, right = start + match.start(), start + match.end()
                key = (sha, left, right)
                if key in seen_spans:
                    counts["duplicate_cited_duration_spans"] += 1
                    continue
                seen_spans.add(key)
                covered = any(item["start"] <= left and item["end"] >= right for item in candidates_by_sha[sha])
                counts["unique_verified_cited_duration_spans"] += 1
                counts["covered_cited_duration_spans" if covered else "uncovered_cited_duration_spans"] += 1
                details.append({"context_sha256": sha, "start": left, "end": right,
                                "quote": text[left:right], "covered_by_cpu_duration_candidate": covered})
    denominator = counts["unique_verified_cited_duration_spans"]
    result = {"kind": "literal_cited_duration_coverage_only", "counts": dict(sorted(counts.items())),
              "exact_contexts_compared": len(candidates_by_sha),
              "covered_fraction": counts["covered_cited_duration_spans"] / denominator if denominator else None,
              "engine_version": engine.VERSION, "engine_sha256": engine.ENGINE_SHA256,
              "reference_duration_grammar": frozen.VERSION + ".YEARS",
              "network_calls": 0, "model_calls": 0,
              "interpretation": "Coverage of unique literal spans detected by the frozen YEARS grammar in exactly verified existing citations. Neither semantic accuracy nor population recall; reference citations are not gold labels. Ambiguous/unverified citations are separate, not successes."}
    return result, details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--references", required=True, type=Path)
    parser.add_argument("--rule-results", type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--private-detail", required=True, type=Path)
    parser.add_argument("--max-records", type=int, default=10000)
    args = parser.parse_args()
    if not 1 <= args.max_records <= 10000:
        parser.error("max-records must be between 1 and 10000")
    if args.receipt.exists() or args.private_detail.exists():
        raise FileExistsError("existing_coverage_output_not_overwritten")
    documents = {}
    with args.inputs.open() as handle:
        for number, line in enumerate(handle, 1):
            if number > args.max_records:
                raise ValueError("source_record_limit_exceeded")
            row = json.loads(line)
            row = row.get("row", row)
            text, sha = row["full_document"], row["context_sha256"]
            if engine._source_sha(text) != sha:
                raise ValueError("source_context_sha256_mismatch")
            documents[sha] = text
    references = []
    with args.references.open() as handle:
        for number, line in enumerate(handle, 1):
            if number > args.max_records:
                raise ValueError("reference_record_limit_exceeded")
            references.append(json.loads(line))
    rules = {}
    if args.rule_results:
        with args.rule_results.open() as handle:
            for number, line in enumerate(handle, 1):
                if number > args.max_records:
                    raise ValueError("rule_record_limit_exceeded")
                row = json.loads(line)
                rules[row["context_sha256"]] = row["result"]
    receipt, details = compare(documents, references, rules)
    args.private_detail.parent.mkdir(parents=True, exist_ok=True)
    with args.private_detail.open("x") as handle:
        for detail in details:
            handle.write(canonical(detail) + "\n")
    args.private_detail.chmod(0o600)
    receipt.update(input_sha256=digest(args.inputs), references_sha256=digest(args.references),
                   rule_results_sha256=digest(args.rule_results) if args.rule_results else None,
                   private_detail_sha256=digest(args.private_detail), comparator_sha256=digest(__file__))
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(args.receipt, receipt)
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
