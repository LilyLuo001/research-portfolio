"""Build dax/data_built/price_histories.csv — the W2 price panel.

Two independent channels, machine-diffed, no language model anywhere in the
path. Channel B (git history of a third-party price table) proposes dated
values; Channel A (archived official pricing pages) confirms or contradicts
them. Meta-rule 2 is satisfied structurally rather than by asking two models
the same question.

The panel never invents an effective date. Each price change is emitted as a
closed interval [effective_date_earliest, effective_date_latest]: the price was
last seen at its old value on the former date and first seen at its new value
on the latter. W5 consumes the interval; a row whose interval is too wide for
the event it feeds is the registry's problem to resolve, not this script's to
paper over.

    python dax/w2/prices/build_price_panel.py --offline     # Channel B only
    python dax/w2/prices/build_price_panel.py               # both channels
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "ops" / "runner"))

import channel_git                                  # noqa: E402
import channel_wayback                              # noqa: E402
from lineage import write_lineage                   # noqa: E402

REGISTRY = REPO / "dax" / "memo" / "event_registry_v1.csv"
OUTPUT = REPO / "dax" / "data_built" / "price_histories.csv"
COVERAGE = REPO / "dax" / "data_built" / "price_coverage_report.md"
MIRROR = REPO / "dax" / "data_raw" / "_litellm_mirror"
WAYBACK_CACHE = REPO / "dax" / "data_raw" / "_wayback_cache"

FIELDS = [
    "model_id", "price_kind", "usd_per_1m",
    "effective_date_earliest", "effective_date_latest",
    "price_status",
    "channel_git_observed", "channel_git_locator",
    "channel_web_status", "channel_web_snapshot", "channel_web_locator",
    "date_coherence", "notes",
]

VERIFIED = "verified"
SINGLE_CHANNEL = "single_channel"
CONFLICT = "conflict"
DATED_MODEL_RE = re.compile(r"-(20\d{2}-\d{2}-\d{2})$")


def registry_models() -> tuple[set[str], list[dict[str, str]]]:
    """Model snapshot ids referenced by the frozen event registry."""
    rows = list(csv.DictReader(REGISTRY.open(encoding="utf-8")))
    models: set[str] = set()
    for row in rows:
        for model_id in row["model_ids"].split("|"):
            model_id = model_id.strip()
            if model_id:
                models.add(model_id)
    return models, rows


def to_intervals(observations: list[channel_git.GitPriceObservation]) -> list[dict[str, object]]:
    """Change points -> interval-censored rows, per (model, kind)."""
    series: dict[tuple[str, str], list[channel_git.GitPriceObservation]] = {}
    for observation in observations:
        series.setdefault((observation.model_id, observation.price_kind), []).append(observation)

    rows: list[dict[str, object]] = []
    for (model_id, price_kind), points in sorted(series.items()):
        points.sort(key=lambda o: o.observed_on)
        for index, point in enumerate(points):
            # The old value was still in force at the previous observation, so
            # the change happened after it. The first row has no lower bound.
            earliest = points[index - 1].observed_on if index else ""
            rows.append({
                "model_id": model_id,
                "price_kind": price_kind,
                "usd_per_1m": f"{point.usd_per_1m:.6f}".rstrip("0").rstrip("."),
                "effective_date_earliest": earliest,
                "effective_date_latest": point.observed_on,
                "price_status": SINGLE_CHANNEL,
                "channel_git_observed": point.observed_on,
                "channel_git_locator": point.locator,
                "channel_web_status": "not_attempted",
                "channel_web_snapshot": "",
                "channel_web_locator": "",
                "date_coherence": "",
                "notes": "" if index else "first observation; no lower bound on effective date",
            })
    return rows


COHERENCE_OK = "ok"
COHERENCE_EARLY = "precedes_registry_launch"
COHERENCE_UNKNOWN = "no_registry_date"


def apply_date_coherence(rows: list[dict[str, object]],
                         events: list[dict[str, str]]) -> dict[str, int]:
    """Flag prices dated before the model's own earliest registry event.

    Found 2026-08-19: after Channel A ran, 15 rows across 5 models carried a
    price whose upper-bound date PRECEDED the launch date the registry gives for
    that model — and 9 of them were marked `verified`, meaning an archived page
    apparently corroborated a price for a model that had not launched.

    At least one of the two sources must be wrong: the registry date, or the
    price observation (a third-party table seeded pre-launch, or a Channel A
    match against a page that predates the model). The panel cannot say which,
    so it says neither — it records the incoherence and refuses to leave the row
    reading as clean corroboration.
    """
    earliest: dict[str, str] = {}
    for event in events:
        for model_id in event["model_ids"].split("|"):
            model_id = model_id.strip()
            if not model_id:
                continue
            date = event["api_effective_date"]
            earliest[model_id] = min(earliest.get(model_id, "9999-99-99"), date)

    counts = {COHERENCE_OK: 0, COHERENCE_EARLY: 0, COHERENCE_UNKNOWN: 0}
    for row in rows:
        launch = earliest.get(str(row["model_id"]))
        observed = str(row["effective_date_latest"])
        if launch is None:
            row["date_coherence"] = COHERENCE_UNKNOWN
        elif observed and observed < launch:
            row["date_coherence"] = COHERENCE_EARLY
            row["notes"] = (str(row["notes"]) +
                            f"; priced on or before {observed} but the registry "
                            f"dates this model to {launch}").lstrip("; ")
            # A corroboration that is chronologically impossible is not evidence.
            if row["price_status"] == VERIFIED:
                row["price_status"] = CONFLICT
        else:
            row["date_coherence"] = COHERENCE_OK
        counts[str(row["date_coherence"])] += 1
    return counts


def load_prior_corroboration(path: pathlib.Path) -> dict[tuple[str, str, str], dict[str, str]]:
    """Channel-A verdicts from an earlier run, keyed by primary key.

    The box executes each inbox payload once inside a 25-minute timeout, so a
    full corroboration sweep may need more than one cycle. Resuming makes a
    partial run cumulative instead of wasted.
    """
    if not path.is_file():
        return {}
    prior: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in csv.DictReader(path.open(encoding="utf-8")):
        if row.get("channel_web_status") not in ("", "not_attempted", channel_wayback.UNREACHABLE):
            prior[(row["model_id"], row["price_kind"], row["effective_date_latest"])] = row
    return prior


def apply_corroboration(rows: list[dict[str, object]], limit: int, verbose: bool,
                        deadline: float | None = None,
                        prior: dict[tuple[str, str, str], dict[str, str]] | None = None) -> None:
    """Run Channel A over the panel, in place."""
    prior = prior or {}
    carried = 0
    for row in rows:
        key = (str(row["model_id"]), str(row["price_kind"]), str(row["effective_date_latest"]))
        if key in prior:
            for field in ("price_status", "channel_web_status",
                          "channel_web_snapshot", "channel_web_locator", "notes"):
                row[field] = prior[key][field]
            carried += 1
    if carried and verbose:
        print(f"  resumed {carried} rows already corroborated", file=sys.stderr)

    snapshot_cache: dict[str, list[channel_wayback.Snapshot]] = {}
    for url in channel_wayback.PRICING_URLS:
        snapshots, status = channel_wayback.list_snapshots(url)
        snapshot_cache[url] = snapshots
        if verbose:
            print(f"  CDX {url}: {len(snapshots)} captures ({status})", file=sys.stderr)

    every_snapshot = [s for snaps in snapshot_cache.values() for s in snaps]
    if not every_snapshot:
        for row in rows:
            row["channel_web_status"] = channel_wayback.UNREACHABLE
            row["notes"] = (str(row["notes"]) + "; archive unreachable from this host").lstrip("; ")
        return

    pending = [r for r in rows if r["channel_web_status"] == "not_attempted"]
    for index, row in enumerate(pending[:limit] if limit else pending):
        if deadline is not None and time.monotonic() > deadline:
            print(f"  time budget reached after {index} rows; "
                  f"{len(pending) - index} left for the next run", file=sys.stderr)
            break
        result = channel_wayback.corroborate(
            str(row["model_id"]), str(row["price_kind"]), float(row["usd_per_1m"]),
            every_snapshot, str(row["effective_date_latest"]),
        )
        row["channel_web_status"] = result.status
        row["channel_web_snapshot"] = result.snapshot_date or ""
        row["channel_web_locator"] = result.locator or ""
        if result.status == channel_wayback.CORROBORATED:
            row["price_status"] = VERIFIED
            # An official capture showing the new price is a tighter upper bound.
            if result.snapshot_date and result.snapshot_date < str(row["effective_date_latest"]):
                row["effective_date_latest"] = result.snapshot_date
        elif result.status == channel_wayback.CONTRADICTED:
            row["price_status"] = CONFLICT
            row["notes"] = (str(row["notes"]) + f"; {result.detail}").lstrip("; ")


def apply_temporal_sanity(rows: list[dict[str, object]]) -> int:
    """Fail closed when a source claims to observe a dated model before its date.

    Channel B uses git author dates as upper bounds. Those dates are not
    trustworthy for a row whose dated model id is later than the commit date;
    a later official snapshot can corroborate the price, but it cannot repair
    the impossible Channel-B bound. Such rows remain visible as conflicts.
    """
    conflicts = 0
    for row in rows:
        match = DATED_MODEL_RE.search(str(row["model_id"]))
        observed = str(row["channel_git_observed"])
        if match and observed and observed < match.group(1):
            row["price_status"] = CONFLICT
            detail = (
                f"Channel B observed {observed} before dated model snapshot "
                f"{match.group(1)}; git date cannot serve as an upper bound"
            )
            row["notes"] = (str(row["notes"]) + f"; {detail}").lstrip("; ")
            conflicts += 1
    return conflicts


def write_coverage(rows: list[dict[str, object]], events: list[dict[str, str]], offline: bool) -> None:
    by_model: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_model.setdefault(str(row["model_id"]), []).append(row)

    lines = [
        "# W2 price-panel coverage against the frozen event registry",
        "",
        f"Channel B (git price table): **{len(rows)}** interval rows across "
        f"**{len(by_model)}** model snapshots.",
        f"Channel A (archived pricing pages): **{'not run (offline)' if offline else 'run'}**.",
        "",
        "A row reaches `verified` only when both channels agree. Everything else",
        "stays `single_channel` or `conflict` and, per meta-rule 4, the event it",
        "feeds stays ineligible until a human resolves it.",
        "",
        "| Event | Registry price_status | Models | Priced models | Panel rows | Panel status |",
        "|---|---|---|---|---|---|",
    ]
    unresolved: list[str] = []
    for event in events:
        models = [m.strip() for m in event["model_ids"].split("|") if m.strip()]
        priced = [m for m in models if m in by_model]
        event_rows = [r for m in priced for r in by_model[m]]
        statuses = sorted({str(r["price_status"]) for r in event_rows}) or ["none"]
        lines.append(
            f"| `{event['event_id']}` | {event['price_status']} | {len(models)} | "
            f"{len(priced)} | {len(event_rows)} | {', '.join(statuses)} |"
        )
        if not priced and event["price_status"] != "n_a":
            unresolved.append(event["event_id"])

    lines += ["", "## Events with no price row in either channel", ""]
    lines += ([f"- `{e}`" for e in unresolved] or ["- none"])
    lines += [
        "",
        "These stay UNKNOWN. They are not filled by inference, and the events",
        "they belong to cannot enter the primary stacked analysis until a dated",
        "price row exists. That is the intended outcome, not a harvester failure.",
        "",
        "## Known limits",
        "",
        "- Channel B's table begins 2023-09; events before that date can only be",
        "  priced by Channel A. `GPT4_LAUNCH` (2023-03) is in that window.",
        "- Channel B dates are upper bounds (see `channel_git` docstring), so a",
        "  single-channel row's interval can be wide. Only Channel A narrows it.",
        "- Channel B is a third-party record. It corroborates; it never overrides",
        "  an official capture.",
    ]
    COVERAGE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true",
                        help="Channel B only; skip archive corroboration")
    parser.add_argument("--mirror", type=pathlib.Path, default=MIRROR)
    parser.add_argument("--corroborate-limit", type=int, default=0,
                        help="cap Channel A checks (0 = no cap)")
    parser.add_argument("--time-budget", type=int, default=0,
                        help="seconds for Channel A before stopping cleanly "
                             "(0 = unlimited); keep under the box inbox timeout")
    parser.add_argument("--cache", type=pathlib.Path, default=WAYBACK_CACHE,
                        help="on-disk cache of fetched snapshots")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    channel_wayback.CACHE_DIR = args.cache

    models, events = registry_models()
    print(f"registry references {len(models)} model snapshots", file=sys.stderr)

    mirror = channel_git.ensure_mirror(args.mirror)
    observations = channel_git.harvest(mirror, progress=args.verbose)
    observations = channel_git.restrict_to_models(observations, models)
    print(f"channel B: {len(observations)} change points for registry models", file=sys.stderr)

    rows = to_intervals(observations)
    if not args.offline:
        deadline = time.monotonic() + args.time_budget if args.time_budget else None
        apply_corroboration(rows, args.corroborate_limit, args.verbose,
                            deadline=deadline, prior=load_prior_corroboration(OUTPUT))
    temporal_conflicts = apply_temporal_sanity(rows)
    if temporal_conflicts:
        print(f"temporal sanity: {temporal_conflicts} impossible git bounds marked conflict",
              file=sys.stderr)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    coherence = apply_date_coherence(rows, events)
    if coherence[COHERENCE_EARLY]:
        print(f"date-coherence: {coherence[COHERENCE_EARLY]} rows priced before "
              f"their model's registry launch — demoted from verified",
              file=sys.stderr)

    write_coverage(rows, events, args.offline)
    write_lineage(str(OUTPUT), [str(REGISTRY)], extra={
        "channels": {
            "git": {"repo": channel_git.DEFAULT_REPO, "path": channel_git.DEFAULT_PATH,
                    "observations": len(observations)},
            "wayback": {"run": not args.offline, "urls": list(channel_wayback.PRICING_URLS)},
        },
        "note": "no language model is involved in producing any value in this file",
    })

    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["price_status"])] = counts.get(str(row["price_status"]), 0) + 1
    print(f"wrote {OUTPUT.relative_to(REPO)} — {len(rows)} rows {counts}", file=sys.stderr)
    print(f"wrote {COVERAGE.relative_to(REPO)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
