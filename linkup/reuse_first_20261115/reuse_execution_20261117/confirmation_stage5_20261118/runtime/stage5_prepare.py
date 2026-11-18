"""Freeze a new leg's inputs and run offline boundary preflight; no auth/model calls."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from stage5_common import (BoundaryError, MODELS, PREDECESSOR, RUNTIME_FILES, VERSION, encoded,
    blocked, canonical_roster, check_predecessor, immutable, import_path, load_inputs,
    merge_exclusions, metadata_only_block, packet_for_validation, parse_json, protected,
    read, roster_sha256, sha)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg", choices=tuple(MODELS), required=True)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--roster", required=True,
        help="Shared frozen record_id/context_sha256 roster: JSON array or JSONL scorer frame")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--instructions", required=True)
    parser.add_argument("--exclusions", required=True)
    parser.add_argument("--field-validator", required=True)
    parser.add_argument("--frozen-validator", required=True)
    parser.add_argument("--predecessor-receipt")
    parser.add_argument("--predecessor-exclusions")
    args = parser.parse_args()
    os.umask(0o077)
    directory = Path(args.directory)
    directory.mkdir(parents=True, exist_ok=True)
    raw_roster = Path(args.roster).read_text()
    roster = canonical_roster(parse_json(raw_roster) if raw_roster.lstrip().startswith("[")
                             else [parse_json(line) for line in raw_roster.splitlines() if line.strip()])
    immutable(directory / "FRAME_ROSTER_PRIVATE.json", encoded(roster))
    exclusions = read(args.exclusions)
    files = {"SCHEMA.json": args.schema, "INSTRUCTIONS.md": args.instructions}
    for name, source in files.items():
        immutable(directory / name, Path(source).read_bytes())
    if PREDECESSOR[args.leg] is not None:
        if not args.predecessor_receipt or not args.predecessor_exclusions:
            raise BoundaryError("serial_predecessor_required")
        name = PREDECESSOR[args.leg].upper() + "_FINAL_PUBLIC.json"
        immutable(directory / name, Path(args.predecessor_receipt).read_bytes())
        immutable(directory / "PREDECESSOR_EXCLUSIONS_PRIVATE.json", Path(args.predecessor_exclusions).read_bytes())
        files[name] = args.predecessor_receipt
        files["PREDECESSOR_EXCLUSIONS_PRIVATE.json"] = args.predecessor_exclusions
        exclusions = merge_exclusions(exclusions, read(args.predecessor_exclusions))
        provisional = {"roster_sha256": roster_sha256(roster),
                       "sha256": {key: sha(directory / key) for key in files}}
        check_predecessor(directory, args.leg, provisional, exclusions)
    source_items = [parse_json(line) for line in Path(args.inputs).read_text().splitlines() if line.strip()]
    items = []
    blocked_hashes = set(exclusions.get("context_sha256", []))
    for item in source_items:
        if protected(item, exclusions):
            blocked_hashes.add(item["row"]["context_sha256"])
            items.append(metadata_only_block(item))
        elif blocked(item):
            raise BoundaryError("unjustified_preblocked_slot")
        else:
            items.append(item)
    exclusions["context_sha256"] = sorted(blocked_hashes)
    immutable(directory / "INPUTS_PRIVATE.jsonl", b"".join(encoded(item) + b"\n" for item in items))
    immutable(directory / "EXCLUSIONS_PRIVATE.json", encoded(exclusions) + b"\n")
    for name in ("INPUTS_PRIVATE.jsonl", "FRAME_ROSTER_PRIVATE.json", "EXCLUSIONS_PRIVATE.json"):
        files[name] = str(directory / name)
    pins = dict(runtime_version=VERSION, roster_sha256=roster_sha256(roster),
                sha256={name: sha(directory / name) for name in files},
                code_sha256={name: sha(Path(__file__).parent / name) for name in RUNTIME_FILES},
                runtime_sha256={"field_validator": sha(args.field_validator), "frozen_validator": sha(args.frozen_validator)})
    immutable(directory / "INPUT_PINS_PUBLIC.json", encoded(pins) + b"\n")
    items, _ = load_inputs(directory, args.leg)
    frozen = import_path("stage5_prepare_frozen_validator", args.frozen_validator)
    packets = [packet_for_validation(item, args.leg) for item in items if not blocked(item)]
    if packets:
        frozen.validate_packet(packets)
    public = dict(runtime_version=VERSION, status="offline_preflight_pass_not_launched", leg=args.leg,
                  selected=len(items), metadata_only_blocked_slots=sum(blocked(item) for item in items),
                  policy=MODELS[args.leg], immutable_pins=pins,
                  new_model_calls=0, original_ledgers_modified=False,
                  new_subcap_sum_usd=50, historical_plus_new_max_usd=228.0651464,
                  unchanged_stage_cap_usd=250, unchanged_whole_phase_cap_usd=450)
    immutable(directory / "PREFLIGHT_PUBLIC.json", encoded(public) + b"\n")
    print(json.dumps(public))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"fatal_error_type": type(exc).__name__, "raw_exception_not_logged": True}))
        raise SystemExit(2)
