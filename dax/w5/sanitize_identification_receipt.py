"""Create a release-safe receipt from the private W5 identification gate.

The private panel path, hash, singular-value vector, occupation labels, event
labels, and any cell-level values are deliberately omitted. The receipt keeps
only aggregate design diagnostics and exact code/input commits.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
from collections.abc import Mapping


COMMIT = re.compile(r"^[0-9a-f]{40}$")
GATE_FIELDS = (
    "status",
    "n_occupations",
    "n_months",
    "n_panel_rows",
    "weighted_residual_dose_variance",
    "effective_rank",
    "leading_singular_share",
    "minimum_rank",
    "maximum_leading_share",
    "rank_tolerance",
    "dynamic_claim_allowed",
    "degenerate_reporting_rule",
    "outcome_data_opened",
)
REQUIRED_INPUTS = ("seat_c", "price_redteam", "integration", "event_evidence")


def sanitize(
    gate_receipt: Mapping[str, object],
    *,
    input_commits: Mapping[str, str],
    output_commit: str,
    panel_version: str,
    component_row_count: int,
    event_occupation_cell_count: int,
    retained_event_count: int,
    occupation_count: int,
    exclusion_counts: Mapping[str, int],
    reconciliation_passed: bool,
) -> dict[str, object]:
    """Return an aggregate-only receipt or fail closed on unsafe gate state."""

    missing = [field for field in GATE_FIELDS if field not in gate_receipt]
    if missing:
        raise ValueError(f"identification receipt missing fields: {missing}")
    if gate_receipt["outcome_data_opened"] is not False:
        raise ValueError("identification receipt does not certify sealed outcomes")
    if int(gate_receipt["minimum_rank"]) < 2:
        raise ValueError("identification gate is weaker than minimum rank 2")
    if float(gate_receipt["maximum_leading_share"]) > 0.95:
        raise ValueError("identification gate is weaker than leading-share 0.95")
    if not reconciliation_passed:
        raise ValueError("cannot issue receipt for unreconciled panel components")

    commits = dict(input_commits)
    if set(commits) != set(REQUIRED_INPUTS):
        raise ValueError(
            f"input commits must be exactly {sorted(REQUIRED_INPUTS)}"
        )
    for label, value in [*commits.items(), ("output", output_commit)]:
        if not COMMIT.fullmatch(str(value)):
            raise ValueError(f"{label} is not an exact 40-character commit")

    counts = {
        "component_row_count": component_row_count,
        "event_occupation_cell_count": event_occupation_cell_count,
        "retained_event_count": retained_event_count,
        "occupation_count": occupation_count,
    }
    if any(not isinstance(value, int) or value < 0 for value in counts.values()):
        raise ValueError("panel aggregate counts must be nonnegative integers")
    exclusions = dict(sorted(exclusion_counts.items()))
    if any(
        not reason or not isinstance(count, int) or count < 0
        for reason, count in exclusions.items()
    ):
        raise ValueError("exclusion counts require named categories and integers")

    return {
        "receipt_version": "dax-w5-gate1-sanitized-v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "panel_version": panel_version,
        "input_commits": commits,
        "output_commit": output_commit,
        "panel_aggregates": counts,
        "exclusion_counts": exclusions,
        "component_reconciliation_passed": True,
        "identification_gate": {
            field: gate_receipt[field] for field in GATE_FIELDS
        },
        "privacy": {
            "private_panel_committed": False,
            "outcomes_opened": False,
            "cell_values_included": False,
            "occupation_or_event_labels_included": False,
            "singular_value_vector_included": False,
        },
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--build-summary", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    gate = json.loads(args.gate_receipt.read_text(encoding="utf-8"))
    build = json.loads(args.build_summary.read_text(encoding="utf-8"))
    receipt = sanitize(gate, **build)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
