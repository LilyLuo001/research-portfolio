#!/usr/bin/env python3
"""Allowlisted artifact snapshot; never uploads data or executes research scripts.

Excluded files are inventoried by location/size only, not opened or hashed.
Run explicitly after new work, inspect the receipt, then stage exact destinations.
"""
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
SOURCES = {
    "feasibility_20260913": REPO / "p1/feasibility_adjudication/20260913",
    "pilot_workspace": Path("/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot"),
}
TEXT = {".py", ".md", ".yaml", ".yml", ".sql", ".sh", ".toml"}
SECRET = re.compile(
    r"github_pat_[A-Za-z0-9_]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"\bdb-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|"
    r"https?://[^\s/@:]+:[^\s/@]+@",
    re.I,
)
LITERAL_SECRET = re.compile(
    r'''(?im)^\s*(?:export\s+)?(?:password|passwd|api_key|access_token|github_token|databento_api_key)\s*[:=]\s*["']([^"'\n]{8,})["']'''
)
IDENTITY_KEYS = {"permno", "cusip", "ncusip", "ticker", "anndats", "anntims", "analys", "association_id", "event_key", "candidate_id"}
VALUE_KEYS = {"eps", "forecast_value", "actual_value", "sue", "car", "bid_px", "ask_px", "bid_px_00", "ask_px_00", "ret", "retx", "price", "p_value", "coefficient"}
AGG_CSV = {
    "candidate_coverage_status.csv", "candidate_link_path_status_aggregate.csv",
    "nominal_both_pre_post_stocks.csv", "old_cap_vs_uncapped.csv",
    "support_by_wave_tier_regime_mapping_analyst.csv", "nominal_support_before_vs_cached_min2.csv",
    "coverage_by_wave_tier_side.csv", "candidate_both_side_summary.csv", "observed_count_distribution.csv",
}

def precheck(rel, path):
    parts = set(rel.parts)
    if path.is_symlink(): return "SYMLINK_NOT_FOLLOWED"
    if parts & {"__pycache__", ".git", ".venv", "node_modules", "databento_runtime"}: return "RUNTIME_OR_CACHE"
    if path.name == ".DS_Store": return "OS_METADATA"
    low = str(rel).lower()
    if "evaluation_20260914/measurement/" in low and path.suffix != ".py": return "HISTORICAL_VALUE_BEARING_OUTPUT_NOT_OPENED"
    if path.name == "IDENTIFICATION_POWER_ASSESSMENT.md": return "HISTORICAL_VALUE_BEARING_OUTPUT_NOT_OPENED"
    if any(x in parts for x in ("raw", "logs", "credentials", "cache")): return "RAW_LOG_OR_PRIVATE_DIRECTORY"
    if path.name.lower().startswith((".env", "credential", "secret")): return "CREDENTIAL_FILENAME"
    if path.stat().st_size > 1_000_000: return "LARGE_PAYLOAD_NOT_OPENED"
    if path.suffix in TEXT: return None
    if path.suffix == ".json":
        if path.name == "logical_sources.json": return None
        if re.search(r"receipt|manifest|summary|config|pass|results|status|budget|condition|hash|verification|gate|source_comparison", path.name, re.I): return None
        return "JSON_NOT_ALLOWLISTED"
    if path.suffix == ".csv" and path.name in AGG_CSV and any(x in low for x in ("corrected_v2/scc/", "targeted_analyst_coverage_20260915/outputs/")): return None
    return "ROW_LEVEL_OR_UNREVIEWED_DATA_NOT_OPENED"

def json_row_risk(value):
    if isinstance(value, dict):
        keys = {str(k).lower() for k in value}
        # Projection field-name lists are safe; actual keyed observations are not.
        if keys & (IDENTITY_KEYS | VALUE_KEYS): return True
        return any(json_row_risk(v) for v in value.values())
    if isinstance(value, list): return any(json_row_risk(v) for v in value)
    return False

def secret_hit(text):
    if SECRET.search(text): return True
    for m in LITERAL_SECRET.finditer(text):
        v = m.group(1)
        if not any(x in v.lower() for x in ("redacted", "placeholder", "example", "your_", "dummy", "test", "${")):
            return True
    return False

def main():
    inventory = []
    for label, root in SOURCES.items():
        if not root.exists():
            inventory.append({"source_root": label, "status": "SOURCE_ROOT_UNAVAILABLE", "source_path": str(root)})
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file(): continue
            rel = path.relative_to(root)
            entry = {"source_root": label, "source_path": str(path), "relative_path": str(rel), "size_bytes": path.stat().st_size}
            reason = precheck(rel, path)
            if reason:
                inventory.append({**entry, "status": "EXCLUDED", "reason": reason})
                continue
            content = path.read_text(encoding="utf-8")
            if secret_hit(content): reason = "POSSIBLE_SECRET_NOT_PUBLISHED"
            elif path.suffix == ".json" and json_row_risk(json.loads(content)): reason = "JSON_POSSIBLE_ROW_LEVEL_OR_VALUE_FIELDS"
            elif path.suffix == ".csv":
                fields = next(csv.reader(io.StringIO(content)), [])
                if set(f.lower() for f in fields) & (IDENTITY_KEYS | VALUE_KEYS): reason = "CSV_NOT_AGGREGATE_SCHEMA"
            if reason:
                inventory.append({**entry, "status": "EXCLUDED", "reason": reason})
                continue
            destination = BASE / "artifacts" / label / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Exact bytes preserve code hashes; no silent path rewriting or redaction.
            payload = content.encode("utf-8")
            if destination.exists() and destination.read_bytes() != payload:
                tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(destination.relative_to(REPO))], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
                if tracked:
                    raise RuntimeError(f"Preserve committed snapshot; changed source needs a new snapshot: {rel}")
            destination.write_bytes(payload)
            inventory.append({**entry, "status": "PUBLISHED", "repository_path": str(destination.relative_to(REPO)), "sha256": hashlib.sha256(payload).hexdigest()})
    out = BASE / "ARTIFACT_INDEX.json"
    out.write_text(json.dumps({"scope": "TWO_KNOWN_WORKSPACE_ROOTS_NOT_COMPLETE_CHAT_TRANSCRIPT", "files": inventory}, ensure_ascii=False, indent=2) + "\n")
    counts = dict(Counter(x["status"] for x in inventory))
    reasons = dict(Counter(x.get("reason") for x in inventory if x["status"] == "EXCLUDED"))
    receipt = {"status": "SNAPSHOT_PREPARED_NOT_YET_PUSHED", "source_roots": {k:str(v) for k,v in SOURCES.items()}, "counts": counts, "exclusion_reasons": reasons, "index_sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "secret_matches_printed": False, "raw_inputs_modified": False, "excluded_raw_payloads_opened_or_hashed": False, "note": "Some textual candidates are inspected then rejected by content checks; excluded raw/unreviewed data are not opened. Historical documents remain historical, not current authority."}
    (BASE / "PUBLICATION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"counts": counts, "exclusion_reasons": reasons}))

if __name__ == "__main__": main()
