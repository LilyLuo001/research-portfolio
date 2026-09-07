"""Require every evidence path/hash pair in the working ledger to resolve."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_every_requirements_evidence_hash_matches_current_bytes():
    ledger = json.loads((ROOT / "requirements_status.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    for requirement in ledger["requirements"]:
        for row in requirement.get("evidence", []):
            relative = Path(row["path"])
            path = (ROOT / relative).resolve()
            try:
                path.relative_to(ROOT.resolve())
            except ValueError:
                failures.append(f"{requirement['id']}: path escapes root: {relative}")
                continue
            if not path.is_file() or path.is_symlink():
                failures.append(f"{requirement['id']}: missing/non-regular: {relative}")
                continue
            actual = digest(path)
            if actual != row["sha256"]:
                failures.append(
                    f"{requirement['id']}: {relative}: ledger={row['sha256']} actual={actual}"
                )
    assert not failures, "\n" + "\n".join(failures)
