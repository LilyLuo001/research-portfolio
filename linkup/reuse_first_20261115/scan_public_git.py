#!/usr/bin/env python3
"""Fail-closed, allowlist-only publication check; never stages or commits files.

This is a lightweight supplement to explicit file review, not a complete DLP
system. Findings contain rule names and line numbers, never matched values.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ALLOWLIST_NAME = "PUBLIC_GIT_ALLOWLIST.json"
RECEIPT_NAME = "PUBLIC_GIT_SCAN_RECEIPT.json"
ROOT_RELATIVE = "linkup/reuse_first_20261115"
MAX_BYTES = 500_000
EXEMPTIBLE_RULES = {"uuid_identifier", "machine_private_absolute_path"}
RULES = {
    "private_key_material": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "api_secret_shape": r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
    "jwt_shape": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
    "credential_assignment": r"(?i)\b(?:AccountKey|SharedAccessSignature|client_secret|api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[\"']?[^\"'\s,}{]{12,}",
    "signed_url_parameter": r"(?i)[?&](?:sig|se|sp|sv)=[^&\s]{8,}",
    "ipv4_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "uuid_identifier": r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b",
    "record_hash_shape": r"\b[0-9a-fA-F]{32}\b",
    "machine_private_absolute_path": r"/(?:Users|home|work/home|projectnb|mnt|tmp)/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+",
}
ROW_VALUE_KEYS = {
    "job_hash", "record_id", "ad_id", "canonical_id", "context_id", "source_id",
    "normalized_text", "raw_text", "description_text", "response_text",
    "model_output", "evidence_text", "source_text", "quote",
}


def scan_text(text: str) -> list[dict]:
    findings = []
    for rule, pattern in RULES.items():
        for match in re.finditer(pattern, text):
            finding={"rule": rule, "line": text.count("\n", 0, match.start()) + 1}
            if rule in EXEMPTIBLE_RULES:
                finding["literal_sha256"]=hashlib.sha256(match.group().encode()).hexdigest()
            findings.append(finding)
    return findings


def scan_json_values(value, at: str = "$", result: list | None = None) -> list:
    result = [] if result is None else result
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{at}.{key}"
            if key.lower() in ROW_VALUE_KEYS and item not in (None, "", [], {}):
                result.append({"rule": "row_level_or_raw_payload_key", "json_key": child})
            scan_json_values(item, child, result)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            scan_json_values(item, f"{at}[{index}]", result)
    return result


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL)


def self_tests() -> dict:
    """Use synthetic markers, never real credentials or private data."""
    cases = [
        ("private_key_material", "-----" + "BEGIN " + "PRIVATE KEY" + "-----"),
        ("api_secret_shape", "sk" + "-" + "x" * 24),
        ("record_hash_shape", "b" * 32),
        ("uuid_identifier", "-".join(["a" * 8, "a" * 4, "a" * 4, "a" * 4, "a" * 12])),
        ("ipv4_address", ".".join(["192", "0", "2", "1"])),
        ("signed_url_parameter", "?" + "sig=" + "x" * 24),
    ]
    outcomes = [any(item["rule"] == expected for item in scan_text(value)) for expected, value in cases]
    outcomes.append(not scan_text("artifact_sha256=" + "a" * 64))
    outcomes.append(bool(scan_json_values({"raw" + "_text": "synthetic fixture"})))
    return {"passed": sum(outcomes), "total": len(outcomes), "all_passed": all(outcomes)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-staged", action="store_true", help="Also reject staged paths outside this exact allowlist and inspect staged bytes.")
    args = parser.parse_args()
    base = Path(__file__).absolute().parent
    repo = Path(git(base, "rev-parse", "--show-toplevel").decode().strip())
    if base != repo / ROOT_RELATIVE or base.is_symlink():
        raise SystemExit("Refusing a publication directory outside the fixed repository scope")
    allow_path = base / ALLOWLIST_NAME
    if allow_path.is_symlink():
        raise SystemExit("Refusing a symlinked allowlist")
    config = json.loads(allow_path.read_text())
    names = config["allowed_files"]
    if config.get("root_repo_relative_path") != ROOT_RELATIVE:
        raise SystemExit("Allowlist scope does not match fixed publication directory")
    if not isinstance(names, list) or len(names) != len(set(names)):
        raise SystemExit("Invalid or duplicate allowlist names")
    for name in names:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or path.suffix not in {".md", ".json", ".py", ".mjs", ".csv", ".tsv", ".sh"}:
            raise SystemExit("Invalid allowlist entry")
    allowed = set(names)
    if not {ALLOWLIST_NAME, RECEIPT_NAME, Path(__file__).name} <= allowed:
        raise SystemExit("Allowlist omits required checker artifacts")
    exemptions=config.get("reviewed_literal_exemptions",[])
    for item in exemptions:
        if item.get("file") not in allowed or not item["file"].endswith(".py") or item.get("rule") not in EXEMPTIBLE_RULES:
            raise SystemExit("Only reviewed public-source UUID/operation-path literals may be exempted")
        if not all(re.fullmatch(r"[0-9a-f]{64}",item.get(key,"")) for key in ("file_sha256","literal_sha256")) or not item.get("review_reason"):
            raise SystemExit("Literal exemption must be bound to exact file and literal SHA digests with a review reason")
    findings, checked, exemptions_used = [], [], []
    def reviewed_findings(name,digest,items):
        retained=[]
        for item in items:
            matching=next((e for e in exemptions if e["file"]==name and e["file_sha256"]==digest and e["rule"]==item["rule"] and e["literal_sha256"]==item.get("literal_sha256") and e.get("line")==item.get("line")),None)
            if matching:
                exemptions_used.append({"file":name,"file_sha256":digest,**item,"review_reason":matching["review_reason"]})
            else:retained.append(item)
        return retained
    test_results = self_tests()
    if not test_results["all_passed"]:
        raise SystemExit("Publication checker self-tests failed")
    for path in sorted(base.rglob("*")):
        relative = path.relative_to(base).as_posix()
        if path.is_symlink():
            findings.append({"file": relative, "rule": "symlink_rejected"})
        elif path.is_file() and relative not in allowed:
            findings.append({"file": relative, "rule": "file_not_allowlisted"})
    for name in names:
        if name == RECEIPT_NAME:
            continue  # This derived receipt excludes its own bytes from the digest set.
        path = base / name
        if not path.is_file() or path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != repo):
            findings.append({"file": name, "rule": "missing_or_unsafe_file"})
            continue
        data = path.read_bytes()
        if len(data) > MAX_BYTES:
            findings.append({"file": name, "rule": "file_exceeds_public_size_cap"})
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append({"file": name, "rule": "binary_or_invalid_utf8"})
            continue
        if "\x00" in text:
            findings.append({"file": name, "rule": "nul_byte_rejected"})
        digest=hashlib.sha256(data).hexdigest()
        findings.extend({"file": name, **item} for item in reviewed_findings(name,digest,scan_text(text)))
        if path.suffix == ".json":
            try:
                payload = json.loads(text)
                findings.extend({"file": name, **item} for item in scan_json_values(payload))
            except json.JSONDecodeError:
                findings.append({"file": name, "rule": "invalid_json"})
        checked.append({"file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    staged_paths = [p.decode() for p in git(repo, "diff", "--cached", "--name-only", "-z").split(b"\0") if p]
    if args.check_staged:
        approved_staged = {f"{ROOT_RELATIVE}/{name}" for name in names}
        for path in staged_paths:
            if path not in approved_staged:
                # Do not print unrelated existing staged filenames or alter them.
                findings.append({"rule": "staged_path_outside_public_allowlist"})
                continue
            data = git(repo, "show", f":{path}")
            try:
                staged_text = data.decode("utf-8")
                findings.extend({"file": path[len(ROOT_RELATIVE) + 1:], "index": True, **item} for item in reviewed_findings(path[len(ROOT_RELATIVE) + 1:],hashlib.sha256(data).hexdigest(),scan_text(staged_text)))
                if path.endswith(".json"):
                    findings.extend({"file": path[len(ROOT_RELATIVE) + 1:], "index": True, **item} for item in scan_json_values(json.loads(staged_text)))
            except (UnicodeDecodeError, json.JSONDecodeError):
                findings.append({"file": path[len(ROOT_RELATIVE) + 1:], "rule": "invalid_staged_text_or_json"})
    receipt = {
        "schema_version": 1,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "root_repo_relative_path": ROOT_RELATIVE,
        "status": "pass" if not findings else "fail",
        "checked_files": checked,
        "checked_file_count_excluding_this_receipt": len(checked),
        "derived_receipt_excluded_from_own_content_hashes": True,
        "staged_check_requested": args.check_staged,
        "staged_file_count": len(staged_paths),
        "synthetic_detector_self_tests": test_results,
        "reviewed_literal_exemptions_used": exemptions_used,
        "credential_or_record_payload_exemptions_permitted": False,
        "findings": findings,
        "staging_committing_or_pushing_performed": False,
        "limitations": "Lightweight pattern/schema screen plus an explicitly reviewed allowlist; not a guarantee against arbitrary secrets or semantic errors.",
    }
    receipt_text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    receipt_findings = scan_text(receipt_text) + scan_json_values(receipt)
    if receipt_findings:
        print(json.dumps({"status": "fail", "reason": "derived_receipt_failed_own_scan", "findings": receipt_findings}))
        return 1
    receipt_path = base / RECEIPT_NAME
    if receipt_path.is_symlink():
        raise SystemExit("Refusing a symlinked receipt")
    receipt_path.write_text(receipt_text)
    print(json.dumps({"status": receipt["status"], "checked_file_count": len(checked), "staged_file_count": len(staged_paths), "findings": findings, "receipt": f"{ROOT_RELATIVE}/{RECEIPT_NAME}"}, ensure_ascii=False))
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
