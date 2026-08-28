"""Prepare, but never submit, the five-month basic-CPS March patch request."""

from __future__ import annotations

import argparse
import json
import pathlib


PATCH_SAMPLES = {f"cps{year}_03b": {} for year in range(2017, 2022)}


def build(source: dict[str, object]) -> dict[str, object]:
    result = {
        "description": (
            "PREPARED NOT SUBMITTED: corrective basic-month CPS request for "
            "March 2017-2021. Do not submit automatically. Uses the exact extract-9 "
            "variables, age restriction, format, and rectangular person structure."
        ),
        "dataStructure": source["dataStructure"],
        "dataFormat": source["dataFormat"],
        "caseSelectWho": source["caseSelectWho"],
        "samples": PATCH_SAMPLES,
        "variables": source["variables"],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    result = build(source)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PREPARED_NOT_SUBMITTED",
        "samples": list(result["samples"]),
        "variable_count": len(result["variables"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
