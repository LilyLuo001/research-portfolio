#!/usr/bin/env python3
"""Seal all disposition sidecars, then finalize the regional runner plan."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import prepare_release_dispositions as prep

INTERMEDIATE_CAP_BYTES = 17_000_000_000


def tree_bytes(*roots: Path) -> int:
    total = 0
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = prep.load_config(args.config)
    cfg["_config_sha256"] = prep.sha256(args.config)
    cfg["_script_sha256"] = prep.sha256(Path(prep.__file__).resolve())
    root = Path(cfg["output_root"])

    # Validate the complete prefix set before deleting any generated fragment.
    for prefix in prep.PREFIXES:
        receipt = root / "prefix_receipts" / ("prefix_%s.json" % prefix)
        if not receipt.exists():
            raise FileNotFoundError("missing prefix receipt: " + prefix)
        document = json.loads(receipt.read_text())
        if (document.get("status") != "complete"
                or document.get("config_sha256") != cfg["_config_sha256"]
                or document.get("script_sha256") != cfg["_script_sha256"]
                or not document.get("row_conservation")):
            raise RuntimeError("invalid prefix receipt: " + prefix)

    sources, _ = prep.load_inventory(cfg["source_inventories"])
    cfg["delete_fragments_after_sidecar_seal"] = True
    progress_path = root / "CONSOLIDATION_PROGRESS.json"
    completed = 0
    for region, source_file in sorted(sources):
        intermediate = tree_bytes(root / "prefix_fragments", root / "prefix_attempts",
                                  Path(cfg["sidecar_root"]))
        if intermediate > INTERMEDIATE_CAP_BYTES:
            raise RuntimeError("17GB intermediate cap reached before next sidecar")
        if shutil.disk_usage(root).free < int(cfg.get("free_reserve_bytes", 8_000_000_000)):
            raise RuntimeError("free-space reserve reached before next sidecar")
        prep.consolidate_shard(cfg, region, source_file)
        intermediate = tree_bytes(root / "prefix_fragments", root / "prefix_attempts",
                                  Path(cfg["sidecar_root"]))
        if intermediate > INTERMEDIATE_CAP_BYTES:
            raise RuntimeError("17GB intermediate cap exceeded after sidecar seal")
        completed += 1
        if completed == 1 or completed % 25 == 0 or completed == len(sources):
            prep.atomic_json(progress_path, {
                "status": "running" if completed < len(sources) else "sidecars_complete",
                "completed_shards": completed,
                "planned_shards": len(sources),
                "intermediate_bytes": intermediate,
                "intermediate_cap_bytes": INTERMEDIATE_CAP_BYTES,
            })
    result = prep.finalize(cfg)
    prep.atomic_json(root / "CONSOLIDATION_COMPLETE.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
