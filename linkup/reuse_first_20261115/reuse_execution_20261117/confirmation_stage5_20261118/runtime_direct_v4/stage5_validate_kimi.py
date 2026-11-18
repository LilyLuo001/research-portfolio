"""Azure-side offline field validation of locally transported visible Kimi output."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from stage5_common import (BoundaryError, encoded, immutable, load_inputs, parse_json, read,
                          sha, validate_output, verify_output_frame)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--transport-outputs", required=True)
    parser.add_argument("--validated-outputs", required=True)
    parser.add_argument("--field-validator", required=True)
    parser.add_argument("--frozen-validator", required=True)
    args = parser.parse_args()
    directory = Path(args.directory)
    items, pins = load_inputs(directory, "Kimi")
    if read(directory / "KIMI_FINAL_PUBLIC.json")["output_sha256"] != sha(args.transport_outputs):
        raise BoundaryError("transport_final_receipt_sha_mismatch")
    for name, path in (("field_validator", args.field_validator), ("frozen_validator", args.frozen_validator)):
        if pins["runtime_sha256"][name] != sha(path):
            raise BoundaryError("frozen_validator_pin_mismatch")
    rows = [parse_json(x) for x in Path(args.transport_outputs).read_text().splitlines() if x.strip()]
    output_roster = verify_output_frame(items, rows, pins["roster_sha256"])
    final = read(directory / "KIMI_FINAL_PUBLIC.json")
    if final.get("roster_sha256") != pins["roster_sha256"] or final.get("output_roster_sha256") != output_roster:
        raise BoundaryError("transport_final_frame_roster_mismatch")
    lookup = {(x["record_id"], x["context_sha256"]): x for x in rows}
    expected = {(x["row"]["record_id"], x["row"]["context_sha256"]) for x in items}
    if len(lookup) != len(rows) or set(lookup) != expected:
        raise BoundaryError("transport_output_identity_or_coverage_mismatch")
    output = []
    for item in items:
        carrier = dict(lookup[item["row"]["record_id"], item["row"]["context_sha256"]])
        carrier["payload"] = carrier["field_validation"] = None
        if carrier["status"] == "response_saved" and carrier.get("response_text") is not None:
            try:
                review, result = validate_output(directory, item, carrier["response_text"], args.field_validator, args.frozen_validator, "Kimi")
                carrier.update(payload=review, field_validation=result, status="field_local_validation_complete")
            except Exception as exc:
                carrier.update(status="invalid_output_preserved", error_type=type(exc).__name__)
        carrier.pop("response_text", None)
        output.append(carrier)
    immutable(args.validated_outputs, b"".join(encoded(x) + b"\n" for x in output))
    print(json.dumps(dict(status="offline_field_validation_complete", outputs_accounted=len(output),
        field_validation_complete=sum(x["status"] == "field_local_validation_complete" for x in output),
        new_model_calls=0, validated_output_sha256=sha(args.validated_outputs))))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"fatal_error_type": type(exc).__name__, "raw_exception_not_logged": True}))
        raise SystemExit(2)
