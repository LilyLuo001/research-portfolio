#!/usr/bin/env python3
"""Check the Git snapshot for likely secrets or excluded raw formats."""

from __future__ import annotations

import re
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".sh", ".sbatch", ".txt"}
FORBIDDEN_SUFFIXES = {".parquet", ".gz", ".zip", ".tar", ".env", ".pem", ".key"}
RULES = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential-assignment": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{12,}"
    ),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "dewey-token": re.compile(r"\bakv1_[A-Za-z0-9_-]{12,}\b"),
    "signed-url-query": re.compile(
        r"(?i)https?://[^\s\"'<>]{0,2048}"
        r"(?:X-Amz-(?:Signature|Credential)|access_token|token)="
    ),
    "proxy-url": re.compile(r"(?i)https?://[^\s/:]+:[^\s/@]+@[^\s]+"),
}


def main() -> int:
    findings: list[tuple[str, str]] = []
    for path in sorted(PROJECT_DIR.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(PROJECT_DIR).as_posix()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append((rel, "forbidden-extension"))
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in RULES.items():
            if pattern.search(text):
                findings.append((rel, label))
    for rel, label in findings:
        print(f"{label}: {rel}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
