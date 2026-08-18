"""Public sources for the CPS <-> O*NET-SOC crosswalk, with locators.

Three public files, each fetched once, checksummed, and cached under
`dax/data_raw/_crosswalk_raw/` (git-ignored). Nothing here is derived from a
language model: meta-rule 1 means the mapping comes from the agencies that
publish it, and every emitted row can be traced back to a downloaded file by
its SHA256.

    A. Census occupation code list and crosswalk  (CPS/ACS occ code -> SOC)
    B. O*NET-SOC taxonomy                          (SOC -> O*NET-SOC detail)
    C. OEWS national employment by SOC             (the weights)

Fetching is a separate, explicit step from building, so a host without egress
can still build from a previously fetched cache — and so a build can never
silently depend on a network round-trip whose result nobody recorded.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import urllib.request

RAW_DIR_NAME = "_crosswalk_raw"
RECEIPT_NAME = "fetch_receipt.json"


@dataclasses.dataclass(frozen=True)
class Source:
    key: str
    url: str
    filename: str
    agency: str
    vintage: str
    note: str


# Vintages are pinned to the memo's frozen 2021 primary (section 0). Changing a
# vintage here changes the index and needs a section 11 deviation memo, not an
# edit.
SOURCES = (
    Source(
        key="census_occ_crosswalk",
        url="https://www2.census.gov/programs-surveys/demo/guidance/"
            "industry-occupation/2018-occupation-code-list-and-crosswalk.xlsx",
        filename="census_2018_occ_crosswalk.xlsx",
        agency="U.S. Census Bureau",
        vintage="2018 occupation code list",
        note="CPS/ACS occupation codes to SOC 2018. One census code may map to "
             "several SOC codes; that is the many-to-many the memo requires.",
    ),
    Source(
        key="onet_taxonomy",
        url="https://www.onetcenter.org/taxonomy/2019/list/"
            "2019_Occupations.csv",
        filename="onet_2019_occupations.csv",
        agency="O*NET Resource Center",
        vintage="O*NET-SOC 2019",
        note="SOC to O*NET-SOC detailed occupations. OEWS publishes employment "
             "at SOC, not O*NET-SOC, which is why split_rule matters downstream.",
    ),
    Source(
        key="oews_national",
        url="https://www.bls.gov/oes/special-requests/oesm21nat.zip",
        filename="oesm21nat.zip",
        agency="U.S. Bureau of Labor Statistics",
        vintage="OEWS May 2021",
        note="National employment by SOC. The frozen 2021 vintage per memo "
             "section 0; the 2019 baseline is a registered robustness variant.",
    ),
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_dir(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root / "dax" / "data_raw" / RAW_DIR_NAME


def fetch_all(repo_root: pathlib.Path, force: bool = False) -> dict[str, object]:
    """Download each source once and write a checksummed receipt.

    Returns the receipt. Raises on any failure rather than emitting a partial
    cache: a half-fetched crosswalk is worse than none, because it would build
    and look plausible.
    """
    directory = raw_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    import datetime as dt

    files: dict[str, object] = {}
    for source in SOURCES:
        target = directory / source.filename
        if force or not target.is_file():
            request = urllib.request.Request(
                source.url, headers={"User-Agent": "dax-w2-crosswalk"})
            with urllib.request.urlopen(request, timeout=180) as response:
                target.write_bytes(response.read())
        files[source.key] = {
            "url": source.url,
            "agency": source.agency,
            "vintage": source.vintage,
            "path": str(target.relative_to(repo_root)),
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
        }

    receipt = {
        "status": "CROSSWALK_SOURCES_FETCHED",
        "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": files,
    }
    (directory / RECEIPT_NAME).write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def load_receipt(repo_root: pathlib.Path) -> dict[str, object] | None:
    path = raw_dir(repo_root) / RECEIPT_NAME
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def verify_cache(repo_root: pathlib.Path) -> list[str]:
    """Re-checksum the cache against the receipt. Returns a list of problems."""
    receipt = load_receipt(repo_root)
    if receipt is None:
        return ["no fetch receipt — run sources.fetch_all on a host with egress"]
    problems: list[str] = []
    for key, entry in receipt["files"].items():
        path = repo_root / str(entry["path"])
        if not path.is_file():
            problems.append(f"{key}: cached file missing at {entry['path']}")
        elif sha256(path) != entry["sha256"]:
            problems.append(f"{key}: checksum mismatch — cache was modified")
    return problems
