#!/usr/bin/env python3
"""Freeze the private 40-task GDPval human-duration pilot before responses."""

from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import pathlib
from urllib.parse import urlparse

import pandas as pd
import pyarrow.parquet as pq

from duration_pilot import PILOT_SEED, PilotCandidate, select_pilot


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _list(value: object) -> list[str]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [str(item) for item in value if str(item).strip()] if isinstance(value, (list, tuple)) else []


def _rank_percentile(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values, key=lambda task_id: (values[task_id], task_id))
    denominator = max(1, len(ordered) - 1)
    return {task_id: index / denominator for index, task_id in enumerate(ordered)}


def _format(row: pd.Series) -> str:
    names = _list(row["deliverable_files"]) + _list(row["deliverable_file_urls"])
    extensions = {pathlib.Path(urlparse(name).path).suffix.casefold() for name in names}
    groups = set()
    if extensions & {".xlsx", ".xls", ".xlsm", ".csv", ".tsv"}:
        groups.add("spreadsheet_tabular")
    if extensions & {".ppt", ".pptx"}:
        groups.add("presentation")
    if extensions & {".doc", ".docx", ".pdf", ".txt", ".md", ".rtf"}:
        groups.add("document")
    if extensions & {".py", ".ipynb", ".json", ".sql", ".xml", ".html"}:
        groups.add("code_data")
    if extensions & {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".svg", ".psd"}:
        groups.add("media_design")
    if len(groups) > 1:
        return "mixed"
    if groups:
        return next(iter(groups))
    return "other_file" if extensions else "text_or_no_file"


def _rubric_count(value: str) -> int:
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return 0
    return len(parsed) if isinstance(parsed, list) else 1


def build_candidates(frame: pd.DataFrame) -> tuple[list[PilotCandidate], dict[str, dict[str, object]]]:
    raw: dict[str, dict[str, object]] = {}
    measures: dict[str, dict[str, float]] = {
        "prompt_words": {}, "rubric_items": {}, "reference_files": {}, "deliverable_files": {}
    }
    for _, row in frame.iterrows():
        task_id = str(row["task_id"]).strip()
        measures["prompt_words"][task_id] = len(str(row["prompt"]).split())
        measures["rubric_items"][task_id] = _rubric_count(row["rubric_json"])
        measures["reference_files"][task_id] = len(_list(row["reference_files"]))
        measures["deliverable_files"][task_id] = len(_list(row["deliverable_files"]))
        raw[task_id] = {"row": row, "format": _format(row)}
    percentiles = {name: _rank_percentile(values) for name, values in measures.items()}
    score = {task_id: sum(values[task_id] for values in percentiles.values()) for task_id in raw}
    ordered = sorted(score, key=lambda task_id: (score[task_id], task_id))
    band = {}
    labels = ("anticipated_short_proxy", "anticipated_medium_proxy", "anticipated_long_proxy")
    for index, task_id in enumerate(ordered):
        band[task_id] = labels[min(2, index * 3 // len(ordered))]
    candidates = []
    for task_id, values in raw.items():
        row = values["row"]
        candidates.append(
            PilotCandidate(
                task_id=task_id,
                task_family=str(row["sector"]).strip(),
                occupation=str(row["occupation"]).strip(),
                anticipated_duration_band=band[task_id],
                task_format=str(values["format"]),
                complexity_score=score[task_id],
            )
        )
    return candidates, raw


def execute(args: argparse.Namespace) -> dict[str, object]:
    private_dir = args.private_output.resolve()
    receipt = args.receipt.resolve()
    if private_dir == receipt.parent or private_dir in receipt.parents:
        raise SystemExit("REFUSED: sanitized receipt must remain outside private storage")
    private_dir.mkdir(parents=True, exist_ok=True)
    private_dir.chmod(0o700)
    receipt.parent.mkdir(parents=True, exist_ok=True)

    frame = pq.read_table(args.gdpval_parquet).to_pandas()
    if len(frame) != 220 or frame["task_id"].nunique() != 220:
        raise SystemExit("REFUSED: GDPval 220-task universe drift")
    candidates, raw = build_candidates(frame)
    selected = select_pilot(candidates)
    selected_ids = {row.task_id for row in selected}

    sample_path = private_dir / "gdpval_duration_pilot_40.csv"
    pd.DataFrame([dataclasses.asdict(row) | {"selection_order": index + 1} for index, row in enumerate(selected)]).to_csv(sample_path, index=False)
    sample_path.chmod(0o600)
    reserve_path = private_dir / "gdpval_duration_production_reserve_180.csv"
    pd.DataFrame(
        [{"task_id": row.task_id, "task_family": row.task_family, "occupation": row.occupation,
          "anticipated_duration_band": row.anticipated_duration_band, "task_format": row.task_format}
         for row in candidates if row.task_id not in selected_ids]
    ).sort_values("task_id").to_csv(reserve_path, index=False)
    reserve_path.chmod(0o600)

    packet_path = private_dir / "gdpval_duration_pilot_packets.jsonl"
    with packet_path.open("w", encoding="utf-8") as handle:
        for selected_row in selected:
            row = raw[selected_row.task_id]["row"]
            packet = {field: (_list(row[field]) if field.endswith("files") or field.endswith("urls") or field.endswith("uris") else str(row[field])) for field in frame.columns}
            handle.write(json.dumps(packet, sort_keys=True) + "\n")
    packet_path.chmod(0o600)

    roster_template = private_dir / "qualified_human_roster_template.csv"
    pd.DataFrame(columns=[
        "private_annotator_code", "occupation", "sector", "experience_role", "years_experience",
        "last_active_year", "task_format_competence", "credential_status", "conflict_clear",
        "consent_complete", "confidentiality_complete", "human_identity_verified",
        "qualification_reviewer_code", "qualification_status",
    ]).to_csv(roster_template, index=False)
    roster_template.chmod(0o600)

    counts = lambda field: dict(sorted(collections.Counter(getattr(row, field) for row in selected).items()))
    artifacts = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in (sample_path, reserve_path, packet_path, roster_template)
    }
    manifest = {
        "status": "PILOT_40_FROZEN_NO_HUMAN_RESPONSES",
        "seed": PILOT_SEED,
        "universe_tasks": 220,
        "pilot_tasks": 40,
        "production_reserve_tasks": 180,
        "selection_algorithm": "greedy_balance_new_occupation_then_least_family_duration_proxy_format_joint_stratum_then_SHA256",
        "complexity_proxy": "sum of within-universe rank percentiles for prompt words, rubric items, reference-file count, and deliverable-file count; terciles assigned before annotation",
        "task_family_definition": "public GDPval sector",
        "unique_occupations": len({row.occupation for row in selected}),
        "counts_by_family": counts("task_family"),
        "counts_by_anticipated_duration_band": counts("anticipated_duration_band"),
        "counts_by_task_format": counts("task_format"),
        "artifacts": artifacts,
        "human_responses_collected": 0,
        "outcomes_opened": False,
    }
    manifest_path = private_dir / "gdpval_duration_pilot_private_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    safe = {
        **{key: value for key, value in manifest.items() if key != "artifacts"},
        "private_manifest_sha256": sha256(manifest_path),
        "private_artifact_hashes": {key: value["sha256"] for key, value in artifacts.items()},
        "task_ids_committed": False,
        "task_text_committed": False,
        "annotator_PII_committed": False,
        "pilot_metrics": "NOT_EVALUABLE_NO_HUMAN_RESPONSES",
    }
    receipt.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return safe


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--gdpval-parquet", type=pathlib.Path, required=True)
    value.add_argument("--private-output", type=pathlib.Path, required=True)
    value.add_argument("--receipt", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    print(json.dumps(execute(parser().parse_args()), indent=2, sort_keys=True))
