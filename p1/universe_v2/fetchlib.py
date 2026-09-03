"""One way to pull bytes from SEC, and one place that records having done it.

Every retrieval appends a manifest line before the caller ever sees the file, so
a document cannot enter the pipeline without provenance. The manifest is JSONL
and append-only: a rebuild adds lines rather than rewriting history, which means
the record of what was fetched when survives the rebuild.

The hash is of the bytes on disk. A cached file is re-hashed rather than trusted,
so silent corruption shows up as a manifest line that disagrees with its
predecessor instead of as a number that quietly moved.

SEC asks for a declared User-Agent and a request rate under 10/s. RATE is set to
about 3/s, well inside that, and applies to fetches only -- a cache hit costs
nothing and waits for nothing.
"""
import hashlib
import json
import os
import ssl
import subprocess
import time
import urllib.error
import urllib.request

import certifi

from paths import MANIFEST

UA = "Qingyan Luo luoqingyan166@gmail.com"
CTX = ssl.create_default_context(cafile=certifi.where())
RATE = 0.34
_last = [0.0]


def _commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=os.path.dirname(os.path.abspath(__file__)),
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


COMMIT = _commit()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(path, url="", accession="", kind="", parser="", extra=None):
    """Append one provenance line. Safe to call for derived artifacts too."""
    row = {"path": str(path), "url": url, "accession": accession, "kind": kind,
           "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sha256": sha256(path), "bytes": os.path.getsize(path),
           "parser": parser, "git_commit": COMMIT}
    if extra:
        row.update(extra)
    with open(MANIFEST, "a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def get(url, dest, accession="", kind="", retries=3):
    """Fetch url to dest unless dest already holds bytes. Returns dest or None.

    A failure writes a .err sidecar rather than raising, because these run over
    thousands of documents and one dead URL must not end the sweep. The sidecar
    is what later distinguishes "never attempted" from "attempted and refused".
    """
    dest = str(dest)
    if os.path.exists(dest) and os.path.getsize(dest):
        return dest
    err = os.path.splitext(dest)[0] + ".err"
    for attempt in range(retries):
        wait = RATE - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120, context=CTX) as resp:
                body = resp.read()
            with open(dest, "wb") as fh:
                fh.write(body)
            record(dest, url=url, accession=accession, kind=kind)
            if os.path.exists(err):
                os.remove(err)
            return dest
        except urllib.error.HTTPError as e:
            # 404 is a fact about the archive, not a transient fault
            if e.code == 404:
                with open(err, "w") as fh:
                    fh.write(f"HTTPError 404 {url}")
                return None
            time.sleep(2 ** attempt)
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
    with open(err, "w") as fh:
        fh.write(locals().get("last", "failed"))
    return None
