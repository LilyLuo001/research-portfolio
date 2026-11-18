"""Generate resolved existing-Azure-path config; no cloud or source reads."""
import argparse
import json
from pathlib import Path

from prepare_physical import NORMALIZER_SHA256, PROTOCOL_VERSION, digest, sha


def configuration(schema_sha256, extractor_sha256):
    root = Path("/home/linkup/migration")
    c5 = root / "confirmation_stage5_20261118"
    def pin(relative, expected):
        return {"path": str(c5 / relative), "sha256": expected}
    return {
        "migration_root": str(root),
        "run_root": str(root / "pilot_economic_20261119/run01"),
        "legacy_code": pin("preparation_code_v1/cloud_prepare_fresh_inputs.py", "b1eeceea00b49820134dbd2eb6f695c158631f6c9ae92fd24f802f8ee8837e58"),
        "normalizer": pin("preparation_code_v1/legacy_v5_frozen.py", NORMALIZER_SHA256),
        "parquet_libraries": str(root / "scope_continuation_20261117/run001/parquet_runtime_20261118_run001/libraries"),
        "original_window": pin("frame_probe_v1/FINITE_SOURCE_WINDOW_PRIVATE.json", "3fe7e77c7577c57ebd0b6306720500621f31673910974c0324d02734464f4c65"),
        "confirmation_preparation": pin("fresh_inputs_v1/FRESH_INPUT_PREPARATION_PUBLIC.json", "3584d93d8c49d7dcc9eee91b5dad2df99fb9896cd969e768f0de62269c6638db"),
        "original_exclusions": pin("fresh_inputs_v1/EXCLUSIONS_PRIVATE.json", "3ac3218d1e7f2e20a96daeb7ab235b7b42b8f7fd3f6f70fbc2e66dd87f8a2681"),
        "stage5_frame": pin("execution_v1/FRAME_PRIVATE.jsonl", "bdf3279fff1d121a073b87368aa62d7bd1b39213f9896ab45337de313e55fe11"),
        "stage5_final_exclusions": [
            pin("execution_v1/luna/EXCLUSIONS_EXPORT_PRIVATE.json", "c8fb5509155c315465d69d0e7c676a74c12a8270348a01d027d9680e9c59f1ca"),
            pin("execution_v1/kimi_direct_v4/EXCLUSIONS_EXPORT_PRIVATE.json", "5254355f9d8d089eb3d0c19bc41c650d4426e3eac4f64d213fc2043e0ef6b7e7"),
            pin("execution_v1/astra_diagnostic_v1/EXCLUSIONS_EXPORT_PRIVATE.json", "5254355f9d8d089eb3d0c19bc41c650d4426e3eac4f64d213fc2043e0ef6b7e7")],
        "versions": {"protocol_version": PROTOCOL_VERSION, "schema_sha256": sha(schema_sha256),
                     "extractor_sha256": sha(extractor_sha256), "normalizer_sha256": NORMALIZER_SHA256},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-sha256", required=True)
    parser.add_argument("--extractor-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = (json.dumps(configuration(args.schema_sha256, args.extractor_sha256), indent=2, sort_keys=True) + "\n").encode()
    with args.out.open("xb") as stream:
        stream.write(data)
    print(json.dumps({"path": str(args.out), "sha256": digest(data)}))


if __name__ == "__main__":
    main()
