"""Channel A — corroboration of prices against archived official pricing pages.

WHY CORROBORATION AND NOT PARSING
---------------------------------
The obvious design is "parse the official pricing table at each archived
snapshot". That is fragile in the way that matters: the page was redesigned
repeatedly across 2021-2026, so a parser silently returns nothing (or worse,
the wrong column) on layouts it was not written for, and a silent miss is
indistinguishable from a real absence.

So this channel does not parse layout. Channel B proposes a candidate value;
this channel asks the far more robust question: *does the official page, as
archived on date D, contain this model's name and this price?* Presence is
stable across redesigns. The cost is that it can only confirm or contradict a
proposed value, never originate one — which is exactly the role it should have.

Unit drift is handled explicitly: OpenAI quoted per-1K tokens early on and
per-1M later, so a proposed $30/1M is searched for as 30, 30.00, 0.03 and
0.030. Missing that would turn every pre-2024 row into a false contradiction.

NETWORK
-------
web.archive.org is blocked by some execution environments' egress policy (it
is blocked in the Claude Code web sandbox as of 2026-08-14). Every function
here degrades to an explicit status rather than an exception, and the panel
builder treats an unreachable archive as "not yet corroborated", never as
"contradicted". Run this channel on the always-on box.
"""

from __future__ import annotations

import dataclasses
import hashlib
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request

CDX_ENDPOINT = "http://web.archive.org/cdx/search/cdx"
PRICING_URLS = (
    "openai.com/pricing",
    "openai.com/api/pricing",
    "platform.openai.com/docs/pricing",
    "developers.openai.com/api/docs/pricing",
)

CORROBORATED = "corroborated"
CONTRADICTED = "contradicted"
NOT_FOUND = "not_found"          # page archived, model name absent
NO_SNAPSHOT = "no_snapshot"      # nothing archived near that date
UNREACHABLE = "unreachable"      # egress blocked / archive down


@dataclasses.dataclass(frozen=True)
class Snapshot:
    timestamp: str               # YYYYMMDDhhmmss
    original: str
    archived_url: str

    @property
    def date(self) -> str:
        return f"{self.timestamp[:4]}-{self.timestamp[4:6]}-{self.timestamp[6:8]}"


@dataclasses.dataclass(frozen=True)
class Corroboration:
    model_id: str
    price_kind: str
    usd_per_1m: float
    status: str
    snapshot_date: str | None
    locator: str | None
    detail: str = ""


# Archived snapshots are large and web.archive.org is slow, but many panel rows
# resolve against the SAME captures. Without a cache the box run is ~850 fetches
# and blows the 25-minute inbox timeout; with one it is ~150 and fits.
CACHE_DIR: pathlib.Path | None = None


def _cache_path(url: str) -> pathlib.Path | None:
    if CACHE_DIR is None:
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest()[:32] + ".html")


def _get(url: str, timeout: int = 45) -> str | None:
    cached = _cache_path(url)
    if cached is not None and cached.is_file():
        return cached.read_text(encoding="utf-8", errors="replace")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "dax-w2-price-harvester"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception:
        return None
    if cached is not None:
        cached.write_text(body, encoding="utf-8")
    return body


def list_snapshots(url: str, from_year: int = 2021, to_year: int = 2026,
                   limit: int = 400) -> tuple[list[Snapshot], str]:
    """Enumerate archived captures of `url`. Returns (snapshots, status)."""
    query = urllib.parse.urlencode({
        "url": url, "output": "json", "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200", "collapse": "timestamp:6",
        "from": str(from_year), "to": str(to_year), "limit": str(limit),
    })
    body = _get(f"{CDX_ENDPOINT}?{query}")
    if body is None:
        return [], UNREACHABLE
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return [], UNREACHABLE
    if not rows or len(rows) < 2:
        return [], NO_SNAPSHOT
    snapshots = [
        Snapshot(timestamp=r[0], original=r[1],
                 archived_url=f"https://web.archive.org/web/{r[0]}/{r[1]}")
        for r in rows[1:]
    ]
    return snapshots, "ok"


def _visible_text(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", markup)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text))


def price_tokens(usd_per_1m: float) -> list[str]:
    """Every plausible textual rendering of one price, across quoting units."""
    per_1k = usd_per_1m / 1000.0
    candidates: list[str] = []
    for value in (usd_per_1m, per_1k):
        if value <= 0:
            continue
        for text in (f"{value:.10f}".rstrip("0").rstrip("."),
                     f"{value:.2f}", f"{value:.3f}", f"{value:.4f}"):
            if text and text not in candidates:
                candidates.append(text)
    return candidates


def corroborate_in_text(text: str, model_id: str, usd_per_1m: float) -> tuple[str, str]:
    """Is `model_id` present, and does `usd_per_1m` appear near it?"""
    haystack = text.lower()
    exact = model_id.lower()
    aliases = [exact]
    # Official pages often display a family label rather than the API id:
    # dated snapshots lose their date suffix and preview ids lose "-preview".
    for candidate in list(aliases):
        undated = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", candidate)
        if undated not in aliases:
            aliases.append(undated)
    for candidate in list(aliases):
        unpreviewed = re.sub(r"-preview$", "", candidate)
        if unpreviewed not in aliases:
            aliases.append(unpreviewed)
    present_aliases = [alias for alias in aliases if alias in haystack]
    if not present_aliases:
        return NOT_FOUND, f"model id {model_id!r} absent from snapshot"

    # Search a window around each mention rather than the whole page, so an
    # unrelated "$5.00" elsewhere on the page cannot fake a match.
    # Try every present alias. The exact API id can occur in navigation or
    # serialized metadata while the visible pricing card uses the family name.
    for needle in present_aliases:
        for match in re.finditer(re.escape(needle), haystack):
            window = haystack[max(0, match.start() - 400): match.end() + 400]
            for token in price_tokens(usd_per_1m):
                if re.search(rf"\${re.escape(token)}\b|\b{re.escape(token)}\b", window):
                    return CORROBORATED, f"matched {token!r} near {needle!r}"
    return CONTRADICTED, (
        f"aliases {present_aliases!r} present but no rendering of {usd_per_1m} nearby"
    )


def corroborate(model_id: str, price_kind: str, usd_per_1m: float,
                snapshots: list[Snapshot], on_or_after: str) -> Corroboration:
    """Check the earliest snapshot at/after `on_or_after` that mentions the model."""
    if not snapshots:
        return Corroboration(model_id, price_kind, usd_per_1m, NO_SNAPSHOT, None, None,
                             "no archived capture in range")
    ordered = sorted((s for s in snapshots if s.date >= on_or_after), key=lambda s: s.timestamp)
    if not ordered:
        return Corroboration(model_id, price_kind, usd_per_1m, NO_SNAPSHOT, None, None,
                             f"no capture on/after {on_or_after}")

    first_contradiction: Corroboration | None = None
    for snapshot in ordered[:12]:
        markup = _get(snapshot.archived_url)
        if markup is None:
            continue
        status, detail = corroborate_in_text(_visible_text(markup), model_id, usd_per_1m)
        if status == CORROBORATED:
            return Corroboration(model_id, price_kind, usd_per_1m, CORROBORATED,
                                 snapshot.date, snapshot.archived_url, detail)
        if status == CONTRADICTED and first_contradiction is None:
            first_contradiction = Corroboration(model_id, price_kind, usd_per_1m, CONTRADICTED,
                                                snapshot.date, snapshot.archived_url, detail)
    if first_contradiction is not None:
        return first_contradiction
    return Corroboration(model_id, price_kind, usd_per_1m, UNREACHABLE, None, None,
                         "no snapshot could be fetched")
