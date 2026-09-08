#!/usr/bin/env python3
"""Download and authenticate the fixed-generation public Canaries archives."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import ssl
import urllib.request
import zipfile


HERE = Path(__file__).resolve().parent


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def safe_member(name: str) -> bool:
    path = Path(name)
    return not path.is_absolute() and ".." not in path.parts and len(path.parts) == 1


def download(output_dir: Path) -> None:
    manifest = json.loads((HERE / "BCC_PUBLIC_DASHBOARD_MANIFEST.json").read_text())
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("output directory must be absent or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        import certifi  # type: ignore
        tls_context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        tls_context = ssl.create_default_context()
    for archive in manifest["archives"]:
        request = urllib.request.Request(
            archive["url"], headers={"User-Agent": "YAX-source-audit/1.0"})
        with urllib.request.urlopen(request, timeout=60, context=tls_context) as response:
            payload = response.read()
        if len(payload) != archive["content_length"]:
            raise RuntimeError(f"content length differs for {archive['name']}")
        if sha256_bytes(payload) != archive["sha256"]:
            raise RuntimeError(f"archive hash differs for {archive['name']}")
        archive_path = output_dir / archive["name"]
        archive_path.write_bytes(payload)
        with zipfile.ZipFile(archive_path) as bundle:
            names = bundle.namelist()
            if set(names) != set(archive["members"]):
                raise RuntimeError(f"archive inventory differs for {archive['name']}")
            for name in names:
                if not safe_member(name):
                    raise RuntimeError(f"unsafe archive member {name}")
                member = bundle.read(name)
                if sha256_bytes(member) != archive["members"][name]:
                    raise RuntimeError(f"member hash differs for {name}")
                (output_dir / name).write_bytes(member)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    download(arguments.output_dir)
