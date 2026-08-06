"""Submit, monitor, and privately download the frozen W1 IPUMS-CPS extract."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re

import requests


API = "https://api.ipums.org"
COLLECTION = "cps"
VERSION = 2
EARLIEST_EVENT = (2023, 3)
SAMPLE_RE = re.compile(r"^cps(\d{4})_(\d{2})([bs])$")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def key() -> str:
    value = os.getenv("IPUMS_API_KEY")
    if not value:
        raise RuntimeError("IPUMS_API_KEY is not set")
    return value


def validate_spec(spec: dict[str, object]) -> None:
    samples = spec.get("samples")
    if not isinstance(samples, dict) or not samples:
        raise ValueError("extract spec has no samples")
    months = []
    for sample in samples:
        match = SAMPLE_RE.fullmatch(sample)
        if not match:
            raise ValueError(f"invalid CPS sample ID: {sample}")
        year, month, suffix = int(match.group(1)), int(match.group(2)), match.group(3)
        if suffix == "s" and month == 3:
            raise ValueError(f"ASEC sample prohibited in W1 monthly extract: {sample}")
        if (year, month) >= EARLIEST_EVENT:
            raise ValueError(f"post-event sample prohibited: {sample}")
        months.append((year, month))
    expected_months = [
        (year, month)
        for year in (2021, 2022, 2023)
        for month in range(1, 13)
        if (2021, 11) <= (year, month) <= (2023, 2)
    ]
    if sorted(months) != expected_months:
        raise ValueError("W1 extract must contain exactly 2021-11 through 2023-02")
    variables = spec.get("variables")
    required = {"CPSIDP", "MISH", "AGE", "EMPSTAT", "OCC2010", "IND1990", "EDUC", "WTFINL", "UHRSWORKT"}
    if not isinstance(variables, dict):
        raise ValueError("extract spec variables must be an object")
    missing = required - set(variables)
    if missing:
        raise ValueError(f"extract spec missing variables {sorted(missing)}")
    age_selection = variables["AGE"].get("caseSelections", {}).get("general", [])
    if age_selection != ["22", "23", "24", "25"]:
        raise ValueError("AGE case selection must be exactly 22 through 25")
    if spec.get("dataFormat") != "csv":
        raise ValueError("W1 extract must request CSV")


def read_spec(path: pathlib.Path) -> dict[str, object]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    validate_spec(spec)
    return spec


def headers() -> dict[str, str]:
    return {"Authorization": key(), "Content-Type": "application/json"}


def extract_url(number: int | None = None) -> str:
    suffix = "" if number is None else f"/{number}"
    return f"{API}/extracts{suffix}?collection={COLLECTION}&version={VERSION}"


def api_json(method: str, url: str, **kwargs) -> dict[str, object]:
    response = requests.request(method, url, headers=headers(), timeout=60, **kwargs)
    if not response.ok:
        body = " ".join(response.text.split())[:500]
        raise RuntimeError(f"IPUMS API {response.status_code}: {body}")
    value = response.json()
    if not isinstance(value, dict):
        raise RuntimeError("IPUMS API returned a non-object response")
    return value


def sanitized_receipt(response: dict[str, object], spec_path: pathlib.Path) -> dict[str, object]:
    definition = response.get("extractDefinition") or {}
    return {
        "status": "IPUMS_PRE_EVENT_EXTRACT_REQUEST",
        "collection": COLLECTION,
        "api_version": VERSION,
        "extract_number": response.get("number"),
        "extract_status": response.get("status"),
        "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "spec_path": str(spec_path),
        "spec_sha256": sha256(spec_path),
        "extract_definition_sha256": hashlib.sha256(
            json.dumps(definition, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "errors": response.get("errors") or {},
        "files": {
            name: {
                "bytes": metadata.get("bytes"),
                "sha256": metadata.get("sha256"),
            }
            for name, metadata in (response.get("downloadLinks") or {}).items()
            if isinstance(metadata, dict)
        },
    }


def write_receipt(path: pathlib.Path, receipt: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def submit(spec_path: pathlib.Path, receipt_path: pathlib.Path) -> dict[str, object]:
    spec = read_spec(spec_path)
    response = api_json("POST", extract_url(), json=spec)
    receipt = sanitized_receipt(response, spec_path)
    if not isinstance(receipt["extract_number"], int):
        raise RuntimeError("IPUMS did not return an extract number")
    write_receipt(receipt_path, receipt)
    return receipt


def refresh(receipt_path: pathlib.Path) -> tuple[dict[str, object], dict[str, object]]:
    old = json.loads(receipt_path.read_text(encoding="utf-8"))
    number = int(old["extract_number"])
    response = api_json("GET", extract_url(number))
    spec_path = pathlib.Path(old["spec_path"])
    receipt = sanitized_receipt(response, spec_path)
    write_receipt(receipt_path, receipt)
    return receipt, response


def download(receipt_path: pathlib.Path, private_dir: pathlib.Path) -> dict[str, object]:
    receipt, response = refresh(receipt_path)
    if receipt["extract_status"] != "completed":
        raise RuntimeError(f"extract is not completed: {receipt['extract_status']}")
    private_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"extract_number": receipt["extract_number"], "files": {}}
    for name, metadata in (response.get("downloadLinks") or {}).items():
        if name not in {"data", "ddiCodebook", "basicCodebook"}:
            continue
        url = metadata["url"]
        filename = pathlib.Path(url).name
        destination = private_dir / filename
        partial = destination.with_suffix(destination.suffix + ".part")
        with requests.get(url, headers={"Authorization": key()}, timeout=120, stream=True) as response_file:
            response_file.raise_for_status()
            with partial.open("wb") as handle:
                for block in response_file.iter_content(1024 * 1024):
                    if block:
                        handle.write(block)
        actual = sha256(partial)
        expected = metadata.get("sha256")
        if expected and actual != expected:
            raise RuntimeError(f"checksum mismatch for {filename}")
        partial.replace(destination)
        manifest["files"][name] = {
            "path": str(destination), "bytes": destination.stat().st_size,
            "sha256": actual,
        }
    manifest_path = private_dir / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    submit_parser = subparsers.add_parser("submit")
    submit_parser.add_argument("--spec", type=pathlib.Path, required=True)
    submit_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    download_parser = subparsers.add_parser("download")
    download_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    download_parser.add_argument("--private-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.command == "submit":
        result = submit(args.spec, args.receipt)
    elif args.command == "status":
        result, _ = refresh(args.receipt)
    else:
        result = download(args.receipt, args.private_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
