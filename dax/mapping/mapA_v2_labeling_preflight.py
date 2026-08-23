#!/usr/bin/env python3
"""Aggregate-only no-inference labeling volume and cost preflight."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import math
import pathlib
import zipfile

import pyarrow.parquet as pq


ADJUDICATION_EXPECTED_SHARE = 0.20
OUTPUT_TOKENS = {"lower": 20, "expected": 80, "upper": 160}
# Official list prices retrieved 2026-08-21; each prompt is far below a context tier boundary.
PRICE = {
    "deepseek": {"currency": "USD", "input": 0.435, "output": 0.87},
    "alibaba": {"currency": "CNY", "input": 0.8, "output": 2.0},
    "google": {"currency": "USD", "input": 0.30, "output": 2.50},
}
CONSERVATIVE_CNY_PER_USD = 7.0


def read_rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_onet_text(path: pathlib.Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        payload = archive.read("db_26_1_text/Task Statements.txt").decode("utf-8-sig")
    return {row["Task ID"].strip(): row["Task"].strip() for row in csv.DictReader(io.StringIO(payload), delimiter="\t")}


def load_gdpval_text(path: pathlib.Path) -> dict[str, str]:
    frame = pq.read_table(path, columns=["task_id", "prompt"]).to_pandas()
    return dict(zip(frame["task_id"].astype(str).str.strip(), frame["prompt"].astype(str).str.strip()))


def prompt_characters(onet_text: str, gdpval_text: str, spec: dict[str, object]) -> int:
    rubric = "\n".join(f"{key}: {value}" for key, value in spec["rubric"].items())
    prompt = (
        f"{spec['task_instruction']}\n\nRELATION RUBRIC\n{rubric}\n\n"
        f"O*NET SOURCE TASK\n{onet_text}\n\nGDPVAL TARGET TASK\n{gdpval_text}\n\n"
        f"OUTPUT\n{spec['output_contract']['format']}"
    )
    return len(prompt)


def token_bounds(characters: int) -> dict[str, int]:
    # Provider tokenizers differ.  The deliberately wide character ratios are
    # planning bounds, not claims about a vendor's billed count.
    return {
        "lower": math.ceil(characters / 5.0),
        "expected": math.ceil(characters / 4.0),
        "upper": math.ceil(characters / 3.0),
    }


def calls(pair_count: int) -> dict[str, int]:
    third_expected = math.ceil(pair_count * ADJUDICATION_EXPECTED_SHARE)
    return {
        "lower": pair_count * 2,
        "expected": pair_count * 2 + third_expected,
        "upper": pair_count * 3,
        "round_1": pair_count * 2,
        "third_expected": third_expected,
        "third_upper": pair_count,
    }


def vendor_cost(input_tokens: int, output_tokens: int, family: str) -> float:
    price = PRICE[family]
    value = (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000
    return value / CONSERVATIVE_CNY_PER_USD if price["currency"] == "CNY" else value


def execute(args: argparse.Namespace) -> dict[str, object]:
    spec = json.loads(args.annotation_spec.read_text(encoding="utf-8"))
    onet = load_onet_text(args.onet_zip)
    gdpval = load_gdpval_text(args.gdpval_parquet)
    validation = read_rows(args.validation_sample)
    recall_sources = read_rows(args.recall_source_sample)
    if len(gdpval) != 220 or len(validation) != 2586 or len(recall_sources) != 100:
        raise SystemExit("REFUSED: frozen annotation universes drifted")

    scope_pairs: dict[str, list[tuple[str, str]]] = {
        "development_calibration": [
            (row["onet_task_id"], row["gdpval_task_id"])
            for row in validation
            if row["split"] in {"development", "calibration"}
        ],
        "locked_test_sealed": [
            (row["onet_task_id"], row["gdpval_task_id"])
            for row in validation
            if row["split"] == "locked_test"
        ],
        "recall_initial_60": [
            (row["onet_task_id"], target)
            for row in recall_sources
            if row["batch"] == "initial_60"
            for target in sorted(gdpval)
        ],
        "recall_reserves_40": [
            (row["onet_task_id"], target)
            for row in recall_sources
            if row["batch"] != "initial_60"
            for target in sorted(gdpval)
        ],
    }
    expected_counts = {
        "development_calibration": 2053,
        "locked_test_sealed": 533,
        "recall_initial_60": 13200,
        "recall_reserves_40": 8800,
    }
    if {key: len(value) for key, value in scope_pairs.items()} != expected_counts:
        raise SystemExit("REFUSED: pair-count drift in labeling preflight")

    scope_receipts: dict[str, object] = {}
    for name, pairs in scope_pairs.items():
        characters = sum(prompt_characters(onet[source], gdpval[target], spec) for source, target in pairs)
        per_round_tokens = token_bounds(characters)
        call_counts = calls(len(pairs))
        # Two initial vendors each receive the full pair universe.  The expected
        # third-vendor volume uses the signed 20% adjudication ceiling as a
        # planning assumption; upper cost sends every pair to the third family.
        expected_third_input = math.ceil(per_round_tokens["expected"] * ADJUDICATION_EXPECTED_SHARE)
        upper_third_input = per_round_tokens["upper"]
        lower_cost = 0.0  # possible only if existing granted/free balances cover all usage
        expected_cost = (
            vendor_cost(per_round_tokens["expected"], len(pairs) * OUTPUT_TOKENS["expected"], "deepseek")
            + vendor_cost(per_round_tokens["expected"], len(pairs) * OUTPUT_TOKENS["expected"], "alibaba")
            + vendor_cost(expected_third_input, call_counts["third_expected"] * OUTPUT_TOKENS["expected"], "google")
        )
        upper_cost = (
            vendor_cost(per_round_tokens["upper"], len(pairs) * OUTPUT_TOKENS["upper"], "deepseek")
            + vendor_cost(per_round_tokens["upper"], len(pairs) * OUTPUT_TOKENS["upper"], "alibaba")
            + vendor_cost(upper_third_input, len(pairs) * OUTPUT_TOKENS["upper"], "google")
        )
        scope_receipts[name] = {
            "pair_tasks": len(pairs),
            "annotation_calls": call_counts,
            "input_token_planning_bounds_per_full_vendor_round": per_round_tokens,
            "output_token_assumption_per_call": OUTPUT_TOKENS,
            "estimated_cost_usd": {
                "lower_if_grants_cover_all_usage": round(lower_cost, 2),
                "expected": round(expected_cost, 2),
                "upper_no_cache_all_third_adjudication": round(upper_cost, 2),
            },
        }

    through_initial = ["development_calibration", "locked_test_sealed", "recall_initial_60"]
    all_scopes = list(scope_pairs)
    def aggregate(names: list[str]) -> dict[str, object]:
        return {
            "pair_tasks": sum(scope_receipts[name]["pair_tasks"] for name in names),
            "annotation_calls": {
                bound: sum(scope_receipts[name]["annotation_calls"][bound] for name in names)
                for bound in ("lower", "expected", "upper")
            },
            "estimated_cost_usd": {
                field: round(sum(scope_receipts[name]["estimated_cost_usd"][field] for name in names), 2)
                for field in ("lower_if_grants_cover_all_usage", "expected", "upper_no_cache_all_third_adjudication")
            },
        }

    return {
        "status": "NEED_PI_BUDGET_AUTHORIZATION",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "providers": {
            "round_1": ["deepseek/deepseek-v4-pro", "alibaba/qwen-plus"],
            "third_only": "google/gemini-2.5-flash",
            "true_vendor_family_independence": True,
            "credential_values_exposed": False,
            "incremental_cost_certified_zero": False,
        },
        "pricing_basis": {
            "retrieved_at_utc_date": "2026-08-21",
            "official_sources": {
                "deepseek": "https://api-docs.deepseek.com/quick_start/pricing/",
                "qwen": "https://help.aliyun.com/en/model-studio/model-pricing",
                "gemini": "https://ai.google.dev/gemini-api/docs/pricing",
            },
            "deepseek_v4_pro_USD_per_1M": {"input_cache_miss": 0.435, "output": 0.87},
            "qwen_plus_CNY_per_1M_under_128K": {"input": 0.8, "output_nonthinking": 2.0},
            "gemini_2_5_flash_USD_per_1M": {"input": 0.30, "output_including_thinking": 2.50},
            "planning_conversion_CNY_per_USD": CONSERVATIVE_CNY_PER_USD,
        },
        "scopes": scope_receipts,
        "aggregate_through_initial_60": aggregate(through_initial),
        "aggregate_maximum_100": aggregate(all_scopes),
        "requested_budget_cap_usd": 60.0,
        "budget_cap_includes": "maximum_100_source_scope upper token estimate plus approximately 60% headroom for provider tokenizer variance and retryable transport failures",
        "realized_spend_usd": 0.0,
        "inference_calls_made": 0,
        "locked_labels_opened": False,
        "outcomes_opened": False,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--annotation-spec", type=pathlib.Path, required=True)
    value.add_argument("--onet-zip", type=pathlib.Path, required=True)
    value.add_argument("--gdpval-parquet", type=pathlib.Path, required=True)
    value.add_argument("--validation-sample", type=pathlib.Path, required=True)
    value.add_argument("--recall-source-sample", type=pathlib.Path, required=True)
    value.add_argument("--receipt", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    arguments = parser().parse_args()
    result = execute(arguments)
    arguments.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
