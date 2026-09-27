"""Run bounded integrity checks on the fixed 2,926-ad development fixture."""
import hashlib
import json
import time
from pathlib import Path

import pyarrow.parquet as pq

from requirement_candidates import MODULES, NORMALIZATION_VERSION, extract


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "reports" / "stage_c_pilot_review" / "sample_ads.parquet"
OUT = Path(__file__).with_name("validation_report.json")
PARSER = Path(__file__).with_name("requirement_candidates.py")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started = time.time()
    rows = pq.read_table(FIXTURE, columns=["DESCRIPTION"]).to_pylist()
    errors = {"parse": 0, "offset": 0, "scope_offset": 0, "fingerprint": 0, "json": 0}
    counts = {m: {"evidence": 0, "requirements": 0, "qualifications": 0, "qualification_unspecified": 0} for m in MODULES}
    for row in rows:
        source = row["DESCRIPTION"]
        result = extract(source)
        errors["parse"] += bool(result["errors"])
        errors["fingerprint"] += result["source_fingerprint_sha256"] != hashlib.sha256(source.encode("utf-8")).hexdigest()
        normalized = result["normalized_text"]
        for item in result["evidence"]:
            module = item["module"]
            counts[module]["evidence"] += 1
            counts[module]["requirements"] += bool(item.get("is_applicant_requirement"))
            counts[module]["qualifications"] += bool(item.get("is_applicant_qualification_candidate"))
            counts[module]["qualification_unspecified"] += item.get("context") == "qualification_unspecified"
            errors["offset"] += normalized[item["start"]:item["end"]] != item["matched_text"]
            errors["offset"] += normalized[item["snippet_start"]:item["snippet_end"]] != item["snippet"]
            if "qualification_scope_start" in item:
                errors["scope_offset"] += normalized[item["qualification_scope_start"]:item["qualification_scope_end"]] != item["qualification_scope_text"]
        try:
            json.dumps(result, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            errors["json"] += 1
    report = {
        "validation_kind": "bounded_v5_development_integrity_check",
        "development_set_notice": "The frozen 24-ad model-consensus diagnostic informed V5 and is DEVELOPMENT, not V5 validation.",
        "sample_rows": len(rows),
        "fixture_sha256": sha256(FIXTURE),
        "parser_sha256": sha256(PARSER),
        "normalization_version": NORMALIZATION_VERSION,
        "errors": errors,
        "status": "PASS" if not any(errors.values()) and len(rows) == 2926 else "FAIL",
        "module_counts": counts,
        "counter_semantics": {
            "requirements": "is_applicant_requirement: explicit required/preferred strength and unconditional local path only",
            "qualifications": "is_applicant_qualification_candidate: applicant qualification presence; does not imply mandatory, preferred, or unconditional",
            "qualification_unspecified": "presence established by explicit qualification/position/education/experience scope while strength remains unspecified",
        },
        "changed_regression_assertions": [
            "V3LocalQualificationPathTests.test_comma_does_not_spread_equivalence_or_preferred_qualifier: generic Qualifications context changed from unknown to qualification_unspecified; required remains false.",
            "RealPilotRegressionTests case 2db189c8cc9eec033f1201d315f41c0f: assert qualification presence instead of requirement strength.",
            "RealPilotRegressionTests case d3468a064263a0c0635b83b34a50a70d: assert qualification presence instead of requirement strength.",
            "RealPilotRegressionTests case 6237aadd5d45f9709a95f4a0bd5b75e1: assert qualification presence instead of requirement strength.",
        ],
        "known_limits": [
            "Development integrity checks are not independent semantic validation or population accuracy estimates.",
            "The parser does not construct a complete qualification or grade-specific relationship graph.",
            "Cross-line OR handling is bounded to adjacent list paths; longer or flattened alternatives can remain unresolved.",
            "Background detection uses a bounded domain vocabulary and omits unlisted occupations.",
            "Generic headings establish presence only; they do not establish mandatory or preferred strength.",
        ],
        "elapsed_seconds": round(time.time() - started, 3),
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
