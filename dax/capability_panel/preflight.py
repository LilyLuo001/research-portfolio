"""W4 budget gate and conservative direct-API upper-bound projection."""

from __future__ import annotations

import argparse
import re
import csv
import datetime as dt
import hashlib
import json
import pathlib
from collections.abc import Mapping


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PreflightError(ValueError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def signed_budget_ceiling(path: pathlib.Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PI_SIGNED":
        raise PreflightError("W4 budget file exists but is not PI_SIGNED")
    ceiling = receipt.get("usd_ceiling")
    if not isinstance(ceiling, (int, float)) or ceiling <= 0:
        raise PreflightError("signed W4 budget lacks a positive USD ceiling")
    for key in ("signed_by", "signed_at_utc"):
        if not str(receipt.get(key, "")).strip():
            raise PreflightError(f"signed W4 budget lacks {key}")
    return {
        "status": "PI_SIGNED",
        "usd_ceiling": float(ceiling),
        "signed_by": receipt["signed_by"],
        "signed_at_utc": receipt["signed_at_utc"],
        "receipt_sha256": sha256_file(path),
    }


def _latest_verified_rates(price_csv: pathlib.Path) -> dict[str, dict[str, float]]:
    with price_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rates: dict[str, dict[str, float]] = {}
    for row in sorted(rows, key=lambda value: value["effective_date_latest"]):
        if row.get("price_status") != "verified":
            continue
        kind = str(row.get("price_kind", ""))
        if kind in {"input", "output", "cache_read"}:
            rates.setdefault(str(row["model_id"]), {})[kind] = float(row["usd_per_1m"])
    return rates


def direct_api_upper_bound(
    registry: Mapping[str, object],
    price_csv: pathlib.Path,
    *,
    task_count: int,
    perturbation_count: int = 4,
    input_token_cap: int = 4096,
    output_token_cap: int = 2048,
) -> dict[str, object]:
    if min(task_count, perturbation_count, input_token_cap, output_token_cap) < 1:
        raise PreflightError("projection dimensions and token caps must be positive")
    rates = _latest_verified_rates(price_csv)
    direct = [
        row for row in registry.get("models", [])  # type: ignore[union-attr]
        if row.get("measurement_route") == "direct"
    ]
    missing: list[str] = []
    total = 0.0
    for row in direct:
        model = str(row["source_model_id"])
        model_rates = rates.get(model, {})
        if "input" not in model_rates or "output" not in model_rates:
            missing.append(model)
            continue
        per_call = (
            input_token_cap * model_rates["input"]
            + output_token_cap * model_rates["output"]
        ) / 1_000_000.0
        total += per_call * task_count * perturbation_count
    return {
        "basis": "conservative_token_caps_x_latest_verified_w2_rates",
        "scope": "direct_openai_rows_only; excludes open-weight hosting and blocked aliases",
        "task_count_upper_bound": task_count,
        "perturbations": perturbation_count,
        "input_token_cap_per_call": input_token_cap,
        "output_token_cap_per_call": output_token_cap,
        "direct_model_rows": len(direct),
        "missing_price_model_rows": sorted(missing),
        "usd_upper_bound_per_repetition": total if not missing else None,
        "price_panel_sha256": sha256_file(price_csv),
    }


def run_plan_formula(registry: Mapping[str, object], *, task_universe: int) -> dict[str, object]:
    planned = sum(
        1 for row in registry.get("models", [])  # type: ignore[union-attr]
        if row.get("status") != "excluded_binding"
    )
    return {
        "nonexcluded_event_model_rows": planned,
        "perturbations": 4,
        "rows_formula": f"{planned * 4} * eligible_task_ids * signed_repetitions",
        "maximum_rows_per_repetition_at_task_universe": planned * 4 * task_universe,
        "task_universe_upper_bound": task_universe,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=pathlib.Path, required=True)
    parser.add_argument("--prices", type=pathlib.Path, required=True)
    parser.add_argument("--availability", type=pathlib.Path, required=True)
    parser.add_argument("--duration-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--budget-file", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--integration-commit", required=True)
    parser.add_argument("--evidence-source-commit", required=True)
    parser.add_argument("--evidence-applied-commit", required=True)
    parser.add_argument("--evidence-patch-id", required=True)
    parser.add_argument("--w3-status", choices=("not_pushed", "pushed_validated"), required=True)
    parser.add_argument("--w3-commit")
    parser.add_argument("--preservation-stimulus",
                        help="PRESERVE-1: name a pinned stimulus set as "
                             "<label>:<sha256>:<task_count>. Declares the "
                             "preservation route, which consumes no mapping.")
    args = parser.parse_args(argv)

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    availability = json.loads(args.availability.read_text(encoding="utf-8"))
    duration = json.loads(args.duration_receipt.read_text(encoding="utf-8"))
    duration_fields = duration.get("task_completion_duration_fields")
    duration_status = str(duration.get("task_completion_duration_status", ""))
    task_count = int(duration.get("n_unique_task_ids", 0))
    covered = task_count if duration_status == "VERIFIED" and duration_fields else 0
    budget = signed_budget_ceiling(args.budget_file)

    # PRESERVE-1 resolves the task universe BEFORE anything consumes it. A
    # preservation run takes its universe from a named pinned stimulus set,
    # never from the duration receipt -- the receipt is precisely what is being
    # deferred, so deriving task_count from it leaves the universe undefined
    # exactly when it matters.
    preservation = None
    if args.preservation_stimulus:
        parts = args.preservation_stimulus.split(":")
        if len(parts) != 3 or not SHA256_RE.fullmatch(parts[1]) or not parts[2].isdigit():
            raise PreflightError(
                "--preservation-stimulus must be <label>:<sha256>:<task_count>")
        preservation = {"label": parts[0], "sha256": parts[1],
                        "task_count": int(parts[2])}
        if preservation["task_count"] < 1:
            raise PreflightError("preservation stimulus needs a positive task count")
        task_count = preservation["task_count"]

    projection = direct_api_upper_bound(registry, args.prices, task_count=task_count)
    availability_counts = dict(availability.get("status_counts", {}))
    account_available = int(availability_counts.get("account_available", 0))

    # Capture gates. Duration moved to scoring_gates (amendment section 3), and
    # PRESERVE-2 records the W3 gate not_applicable for a declared preservation
    # route rather than passing or waiving it. A run that DOES consume a mapping
    # keeps the gate unchanged.
    gates = {
        "w3_exact_commit": (
            "not_applicable" if preservation
            else (args.w3_status == "pushed_validated" and bool(args.w3_commit))),
        "account_availability_probed": bool(availability.get("account_probe_performed")),
        "at_least_one_account_model_available": account_available > 0,
        "signed_repository_usd_ceiling": budget is not None,
    }
    scoring_gates = {
        "task_duration_complete": task_count > 0 and covered == task_count,
    }
    receipt = {
        "receipt_version": "dax-w4-preflight-v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "dependencies": {
            "w5_base": args.base_commit,
            "integration": args.integration_commit,
            "evidence_source": args.evidence_source_commit,
            "evidence_applied": args.evidence_applied_commit,
            "evidence_stable_patch_id": args.evidence_patch_id,
            "w3_status": args.w3_status,
            "w3_commit": args.w3_commit,
        },
        "availability": {
            "receipt_sha256": sha256_file(args.availability),
            "target_rows": availability.get("target_rows"),
            "account_probe_performed": availability.get("account_probe_performed"),
            "status_counts": availability_counts,
        },
        "duration": {
            "source_receipt_sha256": sha256_file(args.duration_receipt),
            "source_status": duration_status,
            "task_ids": task_count,
            "covered_task_ids": covered,
            "missing_task_ids": task_count - covered,
            "coverage_rate": 0 if task_count == 0 else covered / task_count,
            "duration_fields": duration_fields,
            "rows_blocked_missing_duration": task_count - covered,
        },
        "run_plan": run_plan_formula(registry, task_universe=task_count),
        "cost_projection": projection,
        "budget": {
            "signed_repository_ceiling": budget,
            "fallback_smoke_ceiling_usd": 5.0,
            "realized_cost_usd": 0.0,
            "smoke_probe_cost_usd": 0.0,
            "full_paid_capture_started": False,
        },
        "preservation_route": preservation,
        "gates": gates,
        "scoring_gates": scoring_gates,
        "full_capture_allowed": all(
            g is True or g == "not_applicable" for g in gates.values()),
        "scoring_allowed": all(scoring_gates.values()),
        "captured_rows": 0,
        "blocked_rows": task_count,
        "private_panel_committed": False,
        "outcomes_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
