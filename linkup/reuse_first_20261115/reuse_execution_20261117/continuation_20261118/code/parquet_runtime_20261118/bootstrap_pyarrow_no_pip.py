#!/usr/bin/env python3
"""Cloud-only, single-attempt, isolated PyArrow 19.0.1 bootstrap.

No pip, environment modification, Azure access, data input, or model calls.
Execute only after review, on CPython 3.12 Linux x86_64 with glibc, passing a
NEW absolute --output directory whose parent already exists. Never resumes an
existing directory: failed artifacts stay in place for investigation.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import signal
import ssl
import stat
import struct
import subprocess
import sys
import time
import traceback
import urllib.parse
import urllib.request
import zipfile

PACKAGE = "pyarrow"
VERSION = "19.0.1"
METADATA_URL = "https://pypi.org/pypi/pyarrow/19.0.1/json"
MAX_SECONDS = 180
MAX_METADATA = 2 * 1024 * 1024
MAX_WHEEL = 100 * 1024 * 1024
MAX_EXPANDED = 400 * 1024 * 1024
MAX_MEMBERS = 20_000
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


class BootstrapError(Exception):
    """Only the fixed code, never a raw exception message, is public."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def require(condition, code):
    if not condition:
        raise BootstrapError(code)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, sort_keys=True)
        stream.write("\n")


def verified_url(url, host):
    try:
        parsed = urllib.parse.urlsplit(url)
        safe = (parsed.scheme == "https" and parsed.hostname == host
                and parsed.port in (None, 443)
                and parsed.username is None and parsed.password is None
                and not parsed.query and not parsed.fragment
                and "\\" not in url and all(ord(c) > 32 for c in url))
    except (TypeError, ValueError):
        safe = False
    require(safe, "untrusted_URL")
    return url


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 1

    def __init__(self, host):
        self.host = host

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        verified_url(newurl, self.host)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def remaining(deadline):
    seconds = deadline - time.monotonic()
    require(seconds > 0, "overall_180_second_deadline")
    return seconds


def fetch(url, host, destination, cap, deadline):
    """One request sequence only; same-host redirects, but never retries."""
    verified_url(url, host)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),  # Do not read proxy credentials.
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        RestrictedRedirect(host),
    )
    request = urllib.request.Request(url, headers={
        "User-Agent": "LinkUp-isolated-metadata-runtime/1",
        "Accept-Encoding": "identity",
    })
    digest = hashlib.sha256()
    size = 0
    # Exclusive creation preserves partial downloads on failure.
    with Path(destination).open("xb") as target:
        with opener.open(request, timeout=min(20, remaining(deadline))) as response:
            verified_url(response.geturl(), host)
            require(response.status == 200, "download_not_HTTP_200")
            encoding = response.headers.get("Content-Encoding", "identity")
            require(encoding in ("identity", ""), "encoded_HTTP_body_rejected")
            length = response.headers.get("Content-Length")
            if length is not None:
                require(length.isdecimal() and int(length) <= cap,
                        "HTTP_content_length_exceeds_cap")
            while True:
                remaining(deadline)
                chunk = response.read(min(64 * 1024, cap - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                require(size <= cap, "download_exceeds_cap")
                digest.update(chunk)
                target.write(chunk)
            require(length is None or size == int(length), "HTTP_length_mismatch")
    return {"sha256": digest.hexdigest(), "bytes": size}


def host_compatibility():
    require(platform.python_implementation() == "CPython", "requires_CPython")
    require(sys.version_info[:2] == (3, 12), "requires_Python_3_12")
    require(sys.platform == "linux" and platform.machine() == "x86_64",
            "requires_Linux_x86_64")
    try:
        libc = os.confstr("CS_GNU_LIBC_VERSION")
    except (ValueError, OSError, AttributeError):
        libc = None
    match = re.fullmatch(r"glibc (\d+)\.(\d+)", libc or "")
    require(match is not None, "host_glibc_not_verified")
    return tuple(map(int, match.groups()))


def platform_floor(tag):
    known = {"manylinux1_x86_64": (2, 5), "manylinux2010_x86_64": (2, 12),
             "manylinux2014_x86_64": (2, 17)}
    if tag in known:
        return known[tag]
    match = re.fullmatch(r"manylinux_(\d+)_(\d+)_x86_64", tag)
    return tuple(map(int, match.groups())) if match else None


def select_wheel(metadata, glibc):
    require(metadata.get("info", {}).get("name") == PACKAGE
            and metadata.get("info", {}).get("version") == VERSION,
            "wrong_package_or_version_metadata")
    candidates = []
    for entry in metadata.get("urls", []):
        if entry.get("packagetype") != "bdist_wheel" or entry.get("yanked", False):
            continue
        name = entry.get("filename", "")
        match = re.fullmatch(r"pyarrow-19\.0\.1-cp312-cp312-(.+)\.whl", name)
        if not match:
            continue
        floors = [platform_floor(tag) for tag in match.group(1).split(".")]
        if not floors or any(floor is None for floor in floors):
            continue
        compatible = [floor for floor in floors if floor <= glibc]
        if not compatible:
            continue
        # A compound wheel platform tag is an OR of supported platforms.
        # Prefer the highest compatible glibc floor; ties are ambiguous.
        score = max(compatible)
        size = entry.get("size")
        require(type(size) is int and 0 < size <= MAX_WHEEL,
                "wheel_metadata_size_exceeds_cap")
        advertised_sha = entry.get("digests", {}).get("sha256", "")
        require(isinstance(advertised_sha, str) and SHA_RE.fullmatch(advertised_sha),
                "missing_official_SHA256")
        url = verified_url(entry.get("url", ""), "files.pythonhosted.org")
        require(urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1])
                == name, "wheel_URL_filename_mismatch")
        candidates.append((score, {"filename": name, "url": url,
            "advertised_sha256": advertised_sha, "advertised_bytes": size,
            "platform_tags": match.group(1).split("."),
            "selected_glibc_floor": list(score)}))
    require(candidates, "no_compatible_cp312_manylinux_wheel")
    best = max(score for score, _ in candidates)
    chosen = [entry for score, entry in candidates if score == best]
    require(len(chosen) == 1, "ambiguous_compatible_wheel")
    return chosen[0]


def verify_download(observed, selected):
    require(observed["bytes"] == selected["advertised_bytes"], "wheel_size_mismatch")
    require(observed["sha256"] == selected["advertised_sha256"],
            "wheel_SHA256_mismatch")


def inspect_members(archive):
    infos = archive.infolist()
    require(0 < len(infos) <= MAX_MEMBERS, "ZIP_member_count_exceeds_cap")
    names = {}
    total = 0
    approved = []
    for info in infos:
        name = info.filename
        original = getattr(info, "orig_filename", name)
        require("\x00" not in original and "\\" not in name and ":" not in name,
                "unsafe_ZIP_name")
        require(name and not name.startswith("/"), "unsafe_ZIP_name")
        is_dir = info.is_dir()
        clean = name[:-1] if is_dir else name
        parts = clean.split("/")
        require(all(part not in ("", ".", "..") for part in parts), "ZIP_traversal")
        require(not info.flag_bits & 1, "encrypted_ZIP_member")
        kind = stat.S_IFMT(info.external_attr >> 16)
        require(kind in ((0, stat.S_IFDIR) if is_dir else (0, stat.S_IFREG)),
                "ZIP_symlink_or_special_file")
        require(clean not in names, "duplicate_ZIP_member")
        names[clean] = is_dir
        require(info.file_size >= 0 and info.compress_size >= 0, "invalid_ZIP_size")
        require(not is_dir or info.file_size == 0, "ZIP_directory_with_data")
        total += info.file_size
        require(total <= MAX_EXPANDED, "ZIP_expanded_size_exceeds_cap")
        approved.append((info, clean, is_dir))
    for _, clean, _ in approved:
        for parent in PurePosixPath(clean).parents:
            if str(parent) != ".":
                require(names.get(str(parent), True), "ZIP_file_directory_conflict")
    return approved, total


def safe_extract(wheel, target, deadline):
    target = Path(target)
    require(not target.exists() and not target.is_symlink(), "library_directory_exists")
    require(Path(wheel).stat().st_size <= MAX_WHEEL, "wheel_file_exceeds_cap")
    with zipfile.ZipFile(wheel) as archive:
        approved, expected_total = inspect_members(archive)
        target.mkdir(mode=0o700)  # No overwriting, even if another process raced.
        manifest = []
        actual_total = 0
        for info, clean, is_dir in approved:
            remaining(deadline)
            path = target.joinpath(*clean.split("/"))
            if is_dir:
                path.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            digest = hashlib.sha256()
            copied = 0
            with archive.open(info) as source, path.open("xb") as out:
                while True:
                    remaining(deadline)
                    block = source.read(64 * 1024)
                    if not block:
                        break
                    copied += len(block)
                    actual_total += len(block)
                    require(copied <= info.file_size and actual_total <= MAX_EXPANDED,
                            "ZIP_actual_expanded_size_exceeds_cap")
                    digest.update(block)
                    out.write(block)
            require(copied == info.file_size, "ZIP_member_size_mismatch")
            manifest.append({"path": clean, "bytes": copied, "sha256": digest.hexdigest()})
        require(actual_total == expected_total, "ZIP_total_size_mismatch")
    return manifest, actual_total


IMPORT_TEST = r'''
import sys, pathlib, json, struct
root = pathlib.Path(sys.argv[1]).resolve(strict=True)
sys.dont_write_bytecode = True
sys.path.insert(0, str(root))
import pyarrow as pa
import pyarrow.parquet as pq
assert pa.__version__ == "19.0.1"
assert pathlib.Path(pa.__file__).resolve().is_relative_to(root)
assert pathlib.Path(pq.__file__).resolve().is_relative_to(root)
# Buffer construction avoids any automatic NumPy conversion or dependency.
array = pa.Array.from_buffers(pa.int64(), 2,
    [None, pa.py_buffer(struct.pack("<qq", 7, 11))])
table = pa.Table.from_arrays([array], names=["synthetic_id"])
sink = pa.BufferOutputStream()
pq.write_table(table, sink, compression="NONE", use_dictionary=False)
raw = sink.getvalue().to_pybytes()
assert raw[:4] == raw[-4:] == b"PAR1"
length = struct.unpack("<I", raw[-8:-4])[0]
metadata = pq.read_metadata(pa.BufferReader(b"PAR1" + raw[-length-8:]))
assert metadata.num_rows == 2 and metadata.num_columns == 1
assert metadata.num_row_groups == 1
assert metadata.schema.to_arrow_schema().field(0).name == "synthetic_id"
assert str(metadata.schema.to_arrow_schema().field(0).type) == "int64"
assert not any(name == "numpy" or name.startswith("numpy.") for name in sys.modules)
assert all(not name.startswith("pyarrow") or getattr(module, "__file__", None) is None
    or pathlib.Path(module.__file__).resolve().is_relative_to(root)
    for name, module in sys.modules.items())
print(json.dumps({"version": pa.__version__, "synthetic_rows": metadata.num_rows,
    "synthetic_columns": metadata.num_columns, "footer_only_read_metadata_passed": True,
    "numpy_loaded": False, "all_pyarrow_modules_isolated": True}))
'''


def run_import_test(libraries, output, deadline):
    child = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", IMPORT_TEST, str(libraries)],
        cwd=str(output), env={"PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, timeout=min(30, remaining(deadline)),
        check=False,
    )
    write_json_new(output / "IMPORT_TEST_PRIVATE.json", {
        "returncode": child.returncode, "stdout": child.stdout, "stderr": child.stderr})
    require(child.returncode == 0, "isolated_import_or_synthetic_footer_test_failed")
    result = json.loads(child.stdout)
    require(result == {"version": VERSION, "synthetic_rows": 2, "synthetic_columns": 1,
        "footer_only_read_metadata_passed": True, "numpy_loaded": False,
        "all_pyarrow_modules_isolated": True}, "unexpected_import_test_result")
    return result


def claim_new_output(output):
    output = Path(output)
    require(output.is_absolute(), "output_must_be_absolute")
    require(output.resolve(strict=False) == output, "output_ancestor_symlink_or_dot_path")
    require(output.parent.is_dir(), "output_parent_must_exist")
    require(not output.exists() and not output.is_symlink(), "output_already_exists_no_retry")
    output.mkdir(mode=0o700)
    return output


def main(argv=None):
    started = time.monotonic()
    # argparse exits with human-readable usage only for invalid CLI invocation;
    # the bootstrap execution path emits exactly one sanitized JSON document.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    deadline = started + MAX_SECONDS
    public = {"package": PACKAGE, "version": VERSION,
        "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "purpose": "isolated_CPU_Parquet_footer_metadata_only",
        "status": "not_ready", "new_model_calls": 0, "new_cloud_resources": 0,
        "global_python_environment_modified": False,
        "global_environment_policy": "no_pip_no_site_no_global_writes_process_local_sys_path",
        "automatic_retries": 0, "additional_dependencies_installed": [],
        "limits": {"setup_seconds": MAX_SECONDS, "wheel_bytes": MAX_WHEEL,
            "expanded_bytes": MAX_EXPANDED, "metadata_bytes": MAX_METADATA,
            "ZIP_members": MAX_MEMBERS, "import_test_seconds": 30},
        "bootstrap_sha256": sha256(Path(__file__).read_bytes()),
        "import_test_code_sha256": sha256(IMPORT_TEST.encode()),
        "metadata_url": METADATA_URL,
    }
    output = None
    def expired(signum, frame):
        raise BootstrapError("overall_180_second_deadline")
    previous_handler = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, remaining(deadline))
    try:
        glibc = host_compatibility()
        public.update(python=sys.version.split()[0], host_glibc=list(glibc))
        output = claim_new_output(args.output)
        public["isolated_directory"] = str(output / "libraries")
        metadata_path = output / "OFFICIAL_PYPI_METADATA.json"
        observed_metadata = fetch(METADATA_URL, "pypi.org", metadata_path, MAX_METADATA, deadline)
        public["metadata"] = observed_metadata
        metadata = json.loads(metadata_path.read_bytes())
        selected = select_wheel(metadata, glibc)
        public["selected_wheel"] = selected
        wheel = output / selected["filename"]
        observed_wheel = fetch(selected["url"], "files.pythonhosted.org", wheel, MAX_WHEEL, deadline)
        public["downloaded_wheel"] = observed_wheel
        verify_download(observed_wheel, selected)
        public["official_SHA256_verified"] = True
        manifest, expanded_bytes = safe_extract(wheel, output / "libraries", deadline)
        manifest_path = output / "EXTRACTED_FILES_PRIVATE.json"
        write_json_new(manifest_path, manifest)
        public.update(extracted_file_count=len(manifest), expanded_bytes=expanded_bytes,
            extracted_manifest_sha256=sha256(manifest_path.read_bytes()))
        public["import_test"] = run_import_test(output / "libraries", output, deadline)
        remaining(deadline)
        public["status"] = "isolated_pinned_runtime_ready"
    except Exception as exc:
        public["status"] = "isolated_runtime_setup_failed_no_automatic_retry"
        public["error_code"] = exc.code if isinstance(exc, BootstrapError) else "setup_exception"
        public["error_type"] = type(exc).__name__
        if output is not None:
            write_json_new(output / "SETUP_ERROR_PRIVATE.json", {
                "exception_type": type(exc).__name__, "traceback": traceback.format_exc()})
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    public["elapsed_seconds"] = round(time.monotonic() - started, 3)
    if output is not None:
        write_json_new(output / "BOOTSTRAP_PUBLIC.json", public)
    print(json.dumps(public, ensure_ascii=True, sort_keys=True))
    return 0 if public["status"] == "isolated_pinned_runtime_ready" else 1


if __name__ == "__main__":
    sys.exit(main())
