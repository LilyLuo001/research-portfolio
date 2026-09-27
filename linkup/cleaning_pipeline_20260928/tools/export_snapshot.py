#!/usr/bin/env python3
"""Export the explicit public allowlist and record content-addressed provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_DIR / "source_manifest.txt"
DESTINATION = PROJECT_DIR / "source_snapshot"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_paths() -> list[Path]:
    entries = []
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if value and not value.startswith("#"):
            rel = Path(value)
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError(f"unsafe manifest entry: {value}")
            entries.append(rel)
    if len(entries) != len(set(entries)):
        raise ValueError("manifest contains duplicate entries")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.expanduser().resolve()
    selected = selected_paths()
    selected_destinations = {(DESTINATION / rel).resolve() for rel in selected}
    if DESTINATION.exists():
        for existing in sorted(DESTINATION.rglob("*"), reverse=True):
            if existing.is_file() and existing.resolve() not in selected_destinations:
                existing.unlink()
            elif existing.is_dir() and not any(existing.iterdir()):
                existing.rmdir()
    records = []
    for rel in selected:
        source = (source_root / rel).resolve()
        try:
            source.relative_to(source_root)
        except ValueError as exc:
            raise ValueError(f"source escapes source root: {rel}") from exc
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(f"required regular file missing: {rel}")
        if source.suffix.lower() in {".parquet", ".gz", ".zip", ".tar"}:
            raise ValueError(f"bulk-data extension forbidden: {rel}")
        destination = DESTINATION / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        records.append(
            {
                "path": rel.as_posix(),
                "source_sha256": sha256(source),
                "snapshot_sha256": sha256(destination),
                "size_bytes": destination.stat().st_size,
            }
        )
    provenance = {
        "snapshot_created_utc": datetime.now(timezone.utc).isoformat(),
        "source": "local private working tree; paths are relative and content-addressed",
        "file_count": len(records),
        "files": records,
    }
    serialized = json.dumps(provenance, indent=2, ensure_ascii=False) + "\n"
    (PROJECT_DIR / "BUILD_MANIFEST.json").write_text(serialized, encoding="utf-8")
    (PROJECT_DIR / "provenance.json").write_text(serialized, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
