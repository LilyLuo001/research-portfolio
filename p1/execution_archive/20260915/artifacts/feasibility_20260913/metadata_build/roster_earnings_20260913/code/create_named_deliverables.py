"""Write the prompt-specified roster aliases without altering source rosters."""
import hashlib
import json
import shutil
import argparse
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="delivery", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "out_v3"
    destination = root / args.out_dir
    for source_name, target_name in [
        ("seed_stock_wave.csv", "RETRIEVAL_SEED_STOCK_WAVE.csv"),
        ("seed_security.csv", "RETRIEVAL_SEED_SECURITIES.csv"),
    ]:
        target = destination / target_name
        if target.exists():
            raise FileExistsError(target)
        shutil.copyfile(source / source_name, target)
    roster = json.loads((source / "ROSTER_RECEIPT.json").read_text())
    manifest = {
        "status": "SEED_BUILT_AND_METADATA_PROJECTED",
        "purpose": "EARNINGS_METADATA_RETRIEVAL_SEED_ONLY",
        "analysis_eligible": "NOT_ASSESSED",
        "new_clock_completeness": "UNKNOWN",
        "source_version": "E007_exposure_stock_wave_all.csv",
        "source_sha256": roster["E007_sha256"],
        "lineage_sha256": roster["E011_sha256"],
        "filter": "primary_ready parsed as exact string True; exposure_ownership > 0",
        "row_counts": {"input": roster["input_rows"], "stock_wave_seed": roster["seed_stock_wave_rows"], "security_seed": roster["seed_security_rows"]},
        "named_outputs": {name: sha256(destination / name) for name in ["RETRIEVAL_SEED_STOCK_WAVE.csv", "RETRIEVAL_SEED_SECURITIES.csv"]},
        "old_free_parquet": "EXCLUDED_FROM_THIS_RETRIEVAL_SEED",
        "no_cross_version_pooling": True,
    }
    target = destination / "ROSTER_MANIFEST.json"
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
