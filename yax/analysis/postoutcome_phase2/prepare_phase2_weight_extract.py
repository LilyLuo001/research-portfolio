#!/usr/bin/env python3
"""Build, submit, monitor, and privately download the YAX Phase-2 weight patch.

The API key is read only from ``IPUMS_API_KEY``. Licensed microdata must be
downloaded outside the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
from datetime import datetime, timezone

import requests


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
API = "https://api.ipums.org"
COLLECTION = "cps"
VERSION = 2
VARIABLES = (
    "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV",
    "MISH", "AGE", "LNKFW1MWT",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def key() -> str:
    value = os.environ.get("IPUMS_API_KEY")
    if not value:
        raise RuntimeError("IPUMS_API_KEY is not set")
    return value


def headers() -> dict[str, str]:
    return {"Authorization": key(), "Content-Type": "application/json"}


def endpoint(number: int | None = None) -> str:
    suffix = "" if number is None else f"/{number}"
    return f"{API}/extracts{suffix}?collection={COLLECTION}&version={VERSION}"


def api(method: str, url: str, **kwargs) -> dict:
    response = requests.request(method, url, headers=headers(), timeout=120, **kwargs)
    if not response.ok:
        raise RuntimeError(f"IPUMS API {response.status_code}: {' '.join(response.text.split())[:500]}")
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError("IPUMS API returned a non-object response")
    return result


def build(base_path: pathlib.Path, output_path: pathlib.Path) -> dict:
    base = json.loads(base_path.read_text(encoding="utf-8"))
    samples = base["samples"]
    if len(samples) != 114 or "cps2025_10s" in samples:
        raise RuntimeError("base sample set differs from authenticated extract 9")
    ages = [str(value) for value in range(16, 76)]
    spec = {
        "description": (
            "YAX Phase 2 minimal longitudinal-weight patch for extract 9; same 114 "
            "samples, ages 16-75, merge identifiers plus LNKFW1MWT only."
        ),
        "dataStructure": {"rectangular": {"on": "P"}},
        "dataFormat": "csv",
        "caseSelectWho": "individuals",
        "samples": samples,
        "variables": {
            variable: (
                {"caseSelections": {"general": ages}} if variable == "AGE" else {}
            )
            for variable in VARIABLES
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return spec


def sanitized(response: dict, spec_path: pathlib.Path) -> dict:
    definition = response.get("extractDefinition") or {}
    return {
        "record": "YAX Phase 2 minimal LNKFW1MWT extract request",
        "analysis_status": LABEL,
        "collection": COLLECTION,
        "api_version": VERSION,
        "extract_number": response.get("number"),
        "extract_status": response.get("status"),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "spec_path": str(spec_path),
        "spec_sha256": sha256(spec_path),
        "extract_definition_sha256": hashlib.sha256(
            json.dumps(definition, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "errors": response.get("errors") or {},
        "files": {
            name: {"bytes": item.get("bytes"), "sha256": item.get("sha256")}
            for name, item in (response.get("downloadLinks") or {}).items()
            if isinstance(item, dict)
        },
    }


def write_receipt(path: pathlib.Path, receipt: dict) -> None:
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def submit(spec_path: pathlib.Path, receipt_path: pathlib.Path) -> dict:
    response = api("POST", endpoint(), json=json.loads(spec_path.read_text()))
    receipt = sanitized(response, spec_path)
    if not isinstance(receipt["extract_number"], int):
        raise RuntimeError("IPUMS did not return an extract number")
    write_receipt(receipt_path, receipt)
    return receipt


def refresh(receipt_path: pathlib.Path) -> tuple[dict, dict]:
    old = json.loads(receipt_path.read_text())
    response = api("GET", endpoint(int(old["extract_number"])))
    receipt = sanitized(response, pathlib.Path(old["spec_path"]))
    write_receipt(receipt_path, receipt)
    return receipt, response


def download(receipt_path: pathlib.Path, private_dir: pathlib.Path) -> dict:
    receipt, response = refresh(receipt_path)
    if receipt["extract_status"] != "completed":
        raise RuntimeError(f"extract is not completed: {receipt['extract_status']}")
    private_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"extract_number": receipt["extract_number"], "files": {}}
    for name, metadata in (response.get("downloadLinks") or {}).items():
        if name not in {"data", "ddiCodebook", "basicCodebook"}:
            continue
        url = metadata["url"]
        destination = private_dir / pathlib.Path(url).name
        partial = destination.with_suffix(destination.suffix + ".part")
        with requests.get(url, headers={"Authorization": key()}, timeout=120, stream=True) as remote:
            remote.raise_for_status()
            with partial.open("wb") as handle:
                for block in remote.iter_content(1 << 20):
                    if block:
                        handle.write(block)
        actual = sha256(partial)
        expected = metadata.get("sha256")
        if expected and actual != expected:
            raise RuntimeError(f"checksum mismatch for {destination.name}")
        partial.replace(destination)
        manifest["files"][name] = {
            "path": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": actual,
        }
    manifest_path = private_dir / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--base", type=pathlib.Path, required=True)
    build_parser.add_argument("--output", type=pathlib.Path, required=True)
    submit_parser = sub.add_parser("submit")
    submit_parser.add_argument("--spec", type=pathlib.Path, required=True)
    submit_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    download_parser = sub.add_parser("download")
    download_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    download_parser.add_argument("--private-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        result = build(args.base, args.output)
        output = {"status": "BUILT", "samples": len(result["samples"]), "variables": list(result["variables"])}
    elif args.command == "submit":
        output = submit(args.spec, args.receipt)
    elif args.command == "status":
        output, _ = refresh(args.receipt)
    else:
        output = download(args.receipt, args.private_dir)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
