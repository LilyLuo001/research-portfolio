"""Single-normalization adapter for frozen V6 plus frozen enrichment."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Optional, Sequence

from prefilter import AI_BIT, SOFTWARE_BIT, cpu_masks, enrich_with_mask, gpu_masks


def _base_payload(text: str, normalized: str, format_flags: dict, v6, mask: int) -> dict:
    """Frozen V5 orchestration with only two sound empty-module shortcuts."""
    base = v6._base
    try:
        lines = list(base._line_records(normalized))
        by_module = {
            "software": base._extract_software(normalized, lines) if mask & (1 << SOFTWARE_BIT) else [],
            "ai": base._extract_ai(normalized, lines) if mask & (1 << AI_BIT) else [],
            "experience": base._extract_experience(normalized, lines),
            "education": base._extract_education(normalized, lines),
            "tasks": base._extract_tasks(normalized, lines),
        }
        for module in base.MODULES:
            by_module[module] = base._deduplicate(by_module[module])
        all_evidence = base._deduplicate(
            [item for module in base.MODULES for item in by_module[module]]
        )
        returned = all_evidence[:base.EVIDENCE_LIMIT]
        returned_counts = defaultdict(int)
        for item in returned:
            returned_counts[item["module"]] += 1
        return {
            "record_kind": "CANDIDATES", "candidate_only": True,
            "normalization_version": base.NORMALIZATION_VERSION,
            "offset_coordinate_system": "normalized_text_python_codepoint_half_open",
            "normalized_text": normalized,
            "source_fingerprint_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "normalized_text_fingerprint_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "format_flags": format_flags, "normalization_flags": format_flags,
            "summary": {module: base._summary(module, by_module[module]) for module in base.MODULES},
            "evidence": returned, "evidence_limit": base.EVIDENCE_LIMIT,
            "evidence_truncated": len(all_evidence) > base.EVIDENCE_LIMIT,
            "evidence_total_before_truncation": len(all_evidence),
            "module_evidence_truncated": {
                module: returned_counts[module] < len(by_module[module]) for module in base.MODULES
            },
            "errors": [],
        }
    except Exception as exc:
        return base._error_result("%s: %s" % (type(exc).__name__, exc))


def _apply_v6(payload: dict, text, v6) -> dict:
    if payload.get("errors") or not isinstance(text, str):
        payload["normalization_version"] = v6.NORMALIZATION_VERSION
        return payload
    if payload.get("evidence_truncated"):
        payload["normalization_version"] = v6.NORMALIZATION_VERSION
        payload["v6_candidate_incomplete"] = True
        payload["v6_candidate_incomplete_reason"] = "base_evidence_truncated_before_v6_postprocessing"
        return payload
    v6._add_current_enrollment(payload)
    v6._promote_compound_qualification_lines(payload)
    v6._drop_compensation_eligibility_experience(payload)
    return v6._refresh(payload)


def extract_enrich_batch(texts: Sequence[str], v6, enrichment,
                         gpu_executable: Optional[object] = None):
    """Normalize once, prefilter once on a batch, then retain CPU authority."""
    normalized, flags, valid = [], [], []
    for text in texts:
        if not isinstance(text, str):
            normalized.append(""); flags.append({}); valid.append(False)
            continue
        try:
            value, value_flags = v6._base._normalize_with_flags(text)
            normalized.append(value); flags.append(value_flags); valid.append(True)
        except Exception:
            # Preserve the authoritative row-level error wording through V6.
            normalized.append(""); flags.append({}); valid.append(False)
    masks = gpu_masks(normalized, gpu_executable) if gpu_executable else cpu_masks(normalized)
    return extract_enrich_prepared_batch(
        texts, normalized, flags, valid, masks, v6, enrichment
    )


def extract_enrich_prepared_batch(texts: Sequence[str], normalized: Sequence[str],
                                  flags: Sequence[dict], valid: Sequence[bool],
                                  masks: Sequence[int], v6, enrichment):
    """Use coordinator-normalized text and masks without another GPU context."""
    lengths = {len(texts), len(normalized), len(flags), len(valid), len(masks)}
    if len(lengths) != 1:
        raise ValueError("prepared batch lengths differ")
    payloads = []
    for text, value, value_flags, is_valid, mask in zip(texts, normalized, flags, valid, masks):
        if not isinstance(text, str):
            payload = v6._base._error_result("text must be str")
        elif not is_valid:
            # Rare normalization errors use the untouched reference path rather
            # than hiding an exception behind the accelerator.
            payload = v6.extract(text)
            payloads.append(payload)
            continue
        else:
            payload = _base_payload(text, value, value_flags, v6, mask)
        payloads.append(_apply_v6(payload, text, v6))
    results = [enrich_with_mask(enrichment, payload, mask)
               for payload, mask in zip(payloads, masks)]
    return payloads, results, list(masks)
