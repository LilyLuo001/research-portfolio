"""Cached SEC HTTP transport, shared by every job in this directory.

It lives on its own because the TLS workaround below is load-bearing and a second
copy would eventually diverge from it: SEC drops the urllib3 handshake on this
machine's OpenSSL 1.1.1n with an SSLEOFError, while the same request over urllib
with an explicit certifi context succeeds.

The cache is immutable and permanent, so what may be written into it matters. A
403 or 404 is a fact about the archive and is remembered; anything else is a
network condition and is not, because caching it would turn one bad minute into a
permanent negative and silently drop a fund from the sample on every later run.
"""
import gzip
import logging
import os
import pathlib
import ssl
import time
import urllib.error
import urllib.request

CACHE = pathlib.Path(__file__).resolve().parent / "cache"
SEC_SLEEP = 0.15          # be polite; SEC ceiling is 10 req/s
SEC_UA = os.environ.get("SEC_UA", "").strip()

log = logging.getLogger("t2free.http")

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def headers():
    # SEC hosts demand a descriptive User-Agent or they 403.
    ua = SEC_UA or "research-portfolio P1-T2-free (set SEC_UA env)"
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def http_get(url, cache_file, is_json=True, host="sec"):
    """GET with immutable on-disk cache. Returns text, or None on failure."""
    cache_file = pathlib.Path(cache_file)
    if cache_file.exists():
        txt = cache_file.read_text(encoding="utf-8", errors="ignore")
        return txt if txt and not txt.startswith("__ERR__") else None
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers())
            with urllib.request.urlopen(req, timeout=45, context=SSL_CTX) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            time.sleep(SEC_SLEEP)
            txt = raw.decode("utf-8", errors="ignore")
            cache_file.write_text(txt, encoding="utf-8")
            return txt
        except urllib.error.HTTPError as e:
            log.warning("HTTP %s on %s (attempt %d)", e.code, url, attempt + 1)
            if e.code in (403, 404):
                cache_file.write_text("__ERR__", encoding="utf-8")
                return None
            time.sleep(1.0 + attempt)
        except Exception as e:  # noqa: BLE001 - any transport fault is retryable
            log.warning("GET error %s on %s (attempt %d)", e, url, attempt + 1)
            time.sleep(1.0 + attempt)
    log.error("GIVING UP (not cached, will retry next run): %s", url)
    return None
