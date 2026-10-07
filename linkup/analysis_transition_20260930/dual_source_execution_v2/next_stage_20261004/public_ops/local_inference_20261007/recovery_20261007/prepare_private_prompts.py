#!/usr/bin/env python3
"""Build private per-record prompts without reading any reference labels."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    prompt = args.prompt.read_text(encoding="utf-8")
    schema = args.schema.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in args.source.read_text(encoding="utf-8").splitlines() if line.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, row in enumerate(rows, 1):
        record_id = str(row["record_id"])
        text = row["original_text"]
        text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        rendered = (
            prompt.rstrip() + "\n\n"
            "The exact JSON Schema referenced above follows.\n"
            + schema.rstrip() + "\n\n"
            + f"Caller-supplied record_id: {record_id}\n"
            + f"Caller-computed source_text_sha256: {text_sha}\n"
            + "Copy both values exactly into the JSON object.\n\n"
            + "BEGIN ADVERTISEMENT TEXT\n"
            + text
            + "\nEND ADVERTISEMENT TEXT\n"
        )
        target = args.output_dir / f"record_{index:02d}.prompt.txt"
        target.write_text(rendered, encoding="utf-8")
        manifest.append({
            "index": index,
            "record_id": record_id,
            "source_text_sha256": text_sha,
            "source_characters": len(text),
            "prompt_bytes": target.stat().st_size,
            "prompt_sha256": sha256_bytes(target.read_bytes()),
        })
    (args.output_dir / "prompt_manifest.json").write_text(
        json.dumps({
            "source_records": len(rows),
            "prompt_contract_sha256": sha256_bytes(args.prompt.read_bytes()),
            "schema_sha256": sha256_bytes(args.schema.read_bytes()),
            "records": manifest,
            "reference_labels_read": False,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
