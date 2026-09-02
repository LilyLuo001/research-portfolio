"""Where code lives and where data lives, kept deliberately apart.

The first build of this pipeline kept both under /tmp. macOS purges /tmp on an
access-time basis, and on 2026-09-01 it did: the raw SEC corpus, four bulk
caches and thirteen scripts went with it. The scripts were the expensive loss,
because a cache can be refetched and a script cannot.

So code is committed here in the repository and data is written to a cache root
outside it. The cache is reproducible from the manifest; the repository is the
only thing that has to survive.

Set P1_CACHE to relocate the cache (a bigger disk, an external volume). It must
not be set to anything under /tmp.
"""
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parent
CACHE = pathlib.Path(os.environ.get(
    "P1_CACHE", pathlib.Path.home() / "p1_data_cache" / "universe_v2")).resolve()

if str(CACHE).startswith(("/tmp", "/private/tmp", "/var/folders")):
    raise RuntimeError(
        f"P1_CACHE={CACHE} is under a purge-prone temp directory; "
        f"the 2026-09-01 data loss is exactly this mistake")

RAW = CACHE / "raw"           # untouched bytes as fetched from SEC
NCEN = RAW / "ncen"           # DERA bulk zips
HEADERS = RAW / "n14_headers"  # N-14 SGML headers
BODIES = RAW / "n14_bodies"   # N-14 documents
SUBMISSIONS = RAW / "submissions"   # EDGAR per-company submissions JSON
INDEX = RAW / "index"         # EDGAR quarterly form indexes
ESCALATION = CACHE / "escalation"   # per-event completion documents
SUP497 = CACHE / "sup497"     # corpus-sweep 497 documents
MANIFEST = CACHE / "manifest.jsonl"

for d in (CACHE, RAW, NCEN, HEADERS, BODIES, SUBMISSIONS, INDEX,
          ESCALATION, SUP497):
    d.mkdir(parents=True, exist_ok=True)
