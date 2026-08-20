"""Safe target-only model availability audit for the DAX W4 registry."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import stat
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping


ENV_LINE = re.compile(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)\s*$")


class AvailabilityError(RuntimeError):
    pass


def load_registry(path: pathlib.Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    models = data.get("models")
    if not isinstance(models, list) or not models:
        raise AvailabilityError("vintage registry must contain models")
    seen: set[tuple[str, str]] = set()
    for row in models:
        if not isinstance(row, dict):
            raise AvailabilityError("registry model rows must be objects")
        key = (str(row.get("event_id", "")), str(row.get("source_model_id", "")))
        if not all(key) or key in seen:
            raise AvailabilityError(f"blank or duplicate registry key {key}")
        seen.add(key)
        if row.get("source_model_id") == "gpt-4.5-preview":
            if row.get("status") != "excluded_binding" or row.get("measurement_model_id") is not None:
                raise AvailabilityError("gpt-4.5-preview must remain excluded without a stand-in")
        if row.get("measurement_route") == "direct" and not row.get("approved_rule_id"):
            raise AvailabilityError("direct rows require an approved rule")
        if row.get("measurement_route") == "blocked_alias" and row.get("measurement_model_id"):
            raise AvailabilityError("blocked aliases cannot silently name a measurement model")
    return data


def private_env_value(path: pathlib.Path, variable: str) -> str | None:
    """Read one value inside the process; callers must never print it."""

    if not path.exists():
        return None
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise AvailabilityError(f"private env must be mode 0600 or stricter: {path}")
    found: str | None = None
    with path.open(encoding="utf-8", errors="strict") as handle:
        for line in handle:
            match = ENV_LINE.fullmatch(line.rstrip("\n"))
            if match and match.group(1) == variable:
                value = match.group(2).strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                found = value or None
    return found


def list_openai_models(api_key: str, *, timeout_seconds: float = 20.0) -> list[dict[str, object]]:
    if not api_key:
        raise AvailabilityError("missing API key")
    request = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise AvailabilityError(f"models metadata request failed with HTTP {error.code}") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AvailabilityError("models metadata request failed") from error
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise AvailabilityError("models endpoint returned no data list")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def audit_registry(
    registry: Mapping[str, object],
    account_models: Iterable[Mapping[str, object]] | None,
    *,
    probed_at_utc: str | None = None,
) -> dict[str, object]:
    account = None if account_models is None else {
        str(row.get("id", "")): row for row in account_models if row.get("id")
    }
    when = probed_at_utc or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    matrix: list[dict[str, object]] = []
    for source in registry["models"]:  # type: ignore[index]
        row = dict(source)
        route = row["measurement_route"]
        target = row.get("measurement_model_id")
        if row["status"] == "excluded_binding":
            status = "excluded_binding"
            method = "none"
        elif route == "blocked_alias":
            status = "blocked_missing_approved_snapshot_rule"
            method = "none"
        elif row["provider"] != "openai":
            status = str(row["status"])
            method = "none"
        elif account is None:
            status = "unprobed_missing_key"
            method = "none"
        elif target in account:
            status = "account_available"
            method = "models_list_metadata"
        else:
            status = "account_unavailable"
            method = "models_list_metadata"
        matrix.append({
            "event_id": row["event_id"],
            "event_date": row["event_date"],
            "source_model_id": row["source_model_id"],
            "measurement_model_id": target,
            "measurement_route": route,
            "approved_rule_id": row.get("approved_rule_id"),
            "availability_status": status,
            "probe_method": method,
            "shutdown_date": None if not account or target not in account else account[target].get("shutdown_date"),
        })
    counts: dict[str, int] = {}
    for row in matrix:
        key = str(row["availability_status"])
        counts[key] = counts.get(key, 0) + 1
    return {
        "receipt_version": "dax-w4-availability-v1",
        "registry_version": registry["registry_version"],
        "probed_at_utc": when if account is not None else None,
        "account_probe_performed": account is not None,
        "target_rows": len(matrix),
        "status_counts": counts,
        "matrix": matrix,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=pathlib.Path, required=True)
    parser.add_argument("--env-file", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    registry = load_registry(args.registry)
    key = os.environ.get("OPENAI_API_KEY")
    if not key and args.env_file:
        key = private_env_value(args.env_file, "OPENAI_API_KEY")
    models = list_openai_models(key) if key else None
    receipt = audit_registry(registry, models)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
