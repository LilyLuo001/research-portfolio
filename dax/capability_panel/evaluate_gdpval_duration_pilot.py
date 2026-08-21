#!/usr/bin/env python3
"""Evaluate private human pilot responses and emit aggregate metrics only."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib

from duration_pilot import evaluate_pilot


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def execute(args: argparse.Namespace) -> dict[str, object]:
    sample_path = args.frozen_sample.resolve()
    response_path = args.private_responses.resolve()
    output = args.receipt.resolve()
    if output.parent == response_path.parent or response_path.parent in output.parents:
        raise SystemExit("REFUSED: aggregate receipt must be outside private response storage")
    sample = read_rows(sample_path)
    if len(sample) != 40 or len({row["task_id"] for row in sample}) != 40:
        raise SystemExit("REFUSED: frozen pilot sample drift")
    result = evaluate_pilot(read_rows(response_path), expected_task_ids=[row["task_id"] for row in sample])
    safe = {
        **result,
        "evaluated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "frozen_sample_sha256": sha256(sample_path),
        "private_response_artifact_sha256": sha256(response_path),
        "row_level_responses_committed": False,
        "annotator_codes_committed": False,
        "annotator_PII_committed": False,
        "outcomes_opened": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return safe


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--frozen-sample", type=pathlib.Path, required=True)
    value.add_argument("--private-responses", type=pathlib.Path, required=True)
    value.add_argument("--receipt", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    print(json.dumps(execute(parser().parse_args()), indent=2, sort_keys=True))
