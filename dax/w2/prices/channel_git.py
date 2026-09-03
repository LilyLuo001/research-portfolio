"""Channel B — dated API prices from the git history of a third-party price table.

WHY THIS EXISTS
---------------
Historical API prices are the highest-hallucination fact class in this project:
the live vendor pricing page shows only *current* prices, so "what did gpt-4o
cost in June 2024" is a pure recall question, and wrong answers look right.
Meta-rule 1 forbids sourcing it from a model. This channel replaces recall with
a deterministic read of an append-only archive: a third-party price table whose
git history records what the price was believed to be on each commit date.

WHAT THIS CHANNEL CAN AND CANNOT ESTABLISH
------------------------------------------
It establishes an **upper bound** on the effective date, never the date itself.
A commit dated 2024-06-14 carrying $5.00/1M for gpt-4o proves the price was in
effect on or before 2024-06-14; it says nothing about how long before. The
observation is therefore emitted with ``bound="upper"`` and the panel builder
keeps it as an interval. Pinning the true effective date is Channel A's job
(official pricing-page snapshots). A single channel never yields ``verified``.

It is also a *third-party* record. It corroborates; it is not authoritative.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import subprocess
import sys
from typing import Iterable

DEFAULT_REPO = "https://github.com/BerriAI/litellm"
DEFAULT_PATH = "model_prices_and_context_window.json"

# Table field -> our price_kind. Only per-token list prices; batch/priority
# tiers are deliberately excluded, the memo's cost grid is list price.
KIND_FIELDS = {
    "input": "input_cost_per_token",
    "output": "output_cost_per_token",
    "cache_read": "cache_read_input_token_cost",
}


@dataclasses.dataclass(frozen=True)
class GitPriceObservation:
    model_id: str
    price_kind: str
    usd_per_1m: float
    observed_on: str          # committer date, ISO — the UPPER BOUND
    locator: str              # repo@sha:path — permanent, re-fetchable
    bound: str = "upper"


def _run(args: list[str], cwd: pathlib.Path, timeout: int = 300) -> str:
    proc = subprocess.run(
        args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git failed: {' '.join(args)}\n{proc.stderr.strip()}")
    return proc.stdout


def ensure_mirror(mirror: pathlib.Path, repo: str = DEFAULT_REPO) -> pathlib.Path:
    """Blobless clone (or refresh) — full history, blobs fetched on demand."""
    mirror = pathlib.Path(mirror)
    if (mirror / ".git").is_dir():
        _run(["git", "fetch", "--filter=blob:none", "origin"], mirror, timeout=600)
        return mirror
    mirror.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--filter=blob:none", "--no-checkout", "--quiet", repo, str(mirror)],
        check=True, timeout=900,
    )
    # Auto-gc thrashes on a blobless clone that is fetching blobs one at a time.
    for key, val in (("gc.auto", "0"), ("maintenance.auto", "false")):
        _run(["git", "config", key, val], mirror)
    return mirror


def monthly_commits(mirror: pathlib.Path, path: str = DEFAULT_PATH) -> list[tuple[str, str]]:
    """Latest commit touching `path` in each calendar month, oldest month first.

    Monthly resolution is deliberate: the CPS design is monthly, so a finer
    sample would buy precision the outcome data cannot use. It also keeps the
    harvest to ~one blob fetch per month instead of one per commit.
    """
    # Use the committer date, not the author date. A cherry-picked commit can
    # retain an author date months before the content entered the observed
    # branch. Treating that retained date as an observation created impossible
    # pre-launch bounds for dated model snapshots.
    out = _run(["git", "log", "--format=%H %cd", "--date=short", "--", path], mirror)
    latest_per_month: dict[str, tuple[str, str]] = {}
    for line in out.splitlines():          # git log is newest-first
        if not line.strip():
            continue
        sha, date = line.split()
        latest_per_month.setdefault(date[:7], (sha, date))
    return [latest_per_month[m] for m in sorted(latest_per_month)]


def _prices_at(mirror: pathlib.Path, sha: str, path: str, provider: str) -> dict[tuple[str, str], float]:
    """{(model_id, price_kind): usd_per_1m} at one commit."""
    try:
        blob = _run(["git", "show", f"{sha}:{path}"], mirror, timeout=300)
        table = json.loads(blob)
    except (RuntimeError, json.JSONDecodeError):
        return {}                           # missing/renamed/malformed at this commit
    if not isinstance(table, dict):
        return {}

    out: dict[tuple[str, str], float] = {}
    for model_id, entry in table.items():
        if not isinstance(entry, dict) or entry.get("litellm_provider") != provider:
            continue
        for kind, field in KIND_FIELDS.items():
            raw = entry.get(field)
            if isinstance(raw, (int, float)) and raw > 0:
                # Stored per-token; the memo's cost grid is per 1M tokens.
                out[(model_id, kind)] = round(float(raw) * 1_000_000, 6)
    return out


def harvest(
    mirror: pathlib.Path,
    path: str = DEFAULT_PATH,
    provider: str = "openai",
    progress: bool = False,
) -> list[GitPriceObservation]:
    """Walk monthly snapshots and emit one observation per price CHANGE POINT.

    A change point is the first month a (model, kind) is seen at a given value.
    Unchanged months are not re-emitted — the panel is a price *history*, not a
    monthly repetition of the same number.
    """
    observations: list[GitPriceObservation] = []
    last_seen: dict[tuple[str, str], float] = {}
    commits = monthly_commits(mirror, path)

    for index, (sha, date) in enumerate(commits, start=1):
        snapshot = _prices_at(mirror, sha, path, provider)
        if progress:
            print(f"  [{index}/{len(commits)}] {date} {sha[:9]} "
                  f"{len(snapshot)} priced cells", file=sys.stderr)
        for key, value in snapshot.items():
            if last_seen.get(key) != value:
                observations.append(GitPriceObservation(
                    model_id=key[0],
                    price_kind=key[1],
                    usd_per_1m=value,
                    observed_on=date,
                    locator=f"{DEFAULT_REPO}@{sha}:{path}",
                ))
                last_seen[key] = value
    return observations


def restrict_to_models(
    observations: Iterable[GitPriceObservation], model_ids: set[str]
) -> list[GitPriceObservation]:
    """Keep only models the DAX event registry actually references."""
    return [o for o in observations if o.model_id in model_ids]
