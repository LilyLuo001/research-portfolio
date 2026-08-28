"""Audit whether the registered entrant-margin companion is estimable.

The memo's original complement rule (no prior valid occupation) mixes survey
entrants, linkage failures, and long non-employment spells. This audit uses
only adjacent-month CPSIDP links in rotation months where a prior interview is
expected. A labour-market entrant is currently employed with a valid
occupation and was non-employed in the linked prior month.

Only aggregate cell/occupation counts may leave private storage. Person rows,
identifiers, and the detailed audit table remain on the SCC backbone.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib

EXPECTED_PRIOR_MISH = {2, 3, 4, 6, 7, 8}
EMPLOYED = {10, 12}
REQUIRED = {
    "YEAR", "MONTH", "MISH", "CPSIDP", "AGE", "SEX", "RACE", "HISPAN",
    "EDUC", "EMPSTAT", "OCC2010", "WTFINL",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _weighted_share(mask, weights) -> float | None:
    denominator = float(weights.sum())
    return float(weights[mask].sum() / denominator) if denominator > 0 else None


def audit_frame(frame, minimum_pair_count: int = 20):
    """Return a sanitized receipt and private cell/occupation details."""
    import pandas as pd

    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"extract lacks required columns {sorted(missing)}")
    data = frame.loc[frame["AGE"].between(22, 25)].copy()
    data["month_index"] = data["YEAR"].astype(int) * 12 + data["MONTH"].astype(int)
    data["employed"] = data["EMPSTAT"].isin(EMPLOYED)
    data["valid_occ"] = data["OCC2010"].notna() & data["OCC2010"].between(10, 9899)
    data["weight"] = pd.to_numeric(data["WTFINL"], errors="coerce").fillna(0).clip(lower=0)

    duplicate_person_months = int(data.duplicated(["CPSIDP", "month_index"]).sum())
    if duplicate_person_months:
        raise ValueError(f"extract has {duplicate_person_months} duplicate CPSIDP-month rows")

    prior = data[["CPSIDP", "month_index", "EMPSTAT"]].copy()
    prior["month_index"] += 1
    prior = prior.rename(columns={"EMPSTAT": "prior_empstat"})
    linked = data.merge(prior, on=["CPSIDP", "month_index"], how="left", validate="one_to_one")

    expected = linked["MISH"].isin(EXPECTED_PRIOR_MISH) & (
        linked["month_index"] > linked["month_index"].min()
    )
    has_prior = linked["prior_empstat"].notna()
    linkable = expected & has_prior
    link_failure = expected & ~has_prior
    linked_entry = (
        linkable & linked["employed"] & linked["valid_occ"]
        & ~linked["prior_empstat"].isin(EMPLOYED)
    )

    entrants = linked.loc[linked_entry].copy()
    entrants["sex_group"] = entrants["SEX"].map({1: "male", 2: "female"}).fillna("other")
    entrants["race_ethnicity"] = "other_nonhispanic"
    entrants.loc[entrants["RACE"].eq(100), "race_ethnicity"] = "white_nonhispanic"
    entrants.loc[entrants["RACE"].eq(200), "race_ethnicity"] = "black_nonhispanic"
    entrants.loc[entrants["HISPAN"].fillna(0).astype(float).gt(0), "race_ethnicity"] = "hispanic"
    entrants["education_group"] = entrants["EDUC"].ge(111).map(
        {True: "college", False: "noncollege"}
    )
    entrants["entry_mix_cell"] = (
        entrants["sex_group"] + "|" + entrants["race_ethnicity"] + "|"
        + entrants["education_group"]
    )

    details = (
        entrants.groupby(["entry_mix_cell", "OCC2010"], dropna=False)
        .agg(n_unweighted=("CPSIDP", "size"), weight_sum=("weight", "sum"))
        .reset_index()
        .sort_values(["entry_mix_cell", "OCC2010"])
    )
    pair_counts = details["n_unweighted"] if not details.empty else pd.Series(dtype=float)
    cell_counts = (entrants.groupby("entry_mix_cell").size()
                   if not entrants.empty else pd.Series(dtype=float))
    n_entries = int(linked_entry.sum())
    sparse_entry_share = (
        float(details.loc[details["n_unweighted"] < minimum_pair_count, "n_unweighted"].sum()
              / n_entries) if n_entries else None
    )

    receipt = {
        "status": "ENTRANT_COMPANION_DEMOTED_TO_EXPLORATORY",
        "method": "adjacent-month CPSIDP transition in MISH 2-4 or 6-8",
        "reason": (
            "The registered complement rule is not a labour-market entrant definition. "
            "Only linked nonemployment-to-employment transitions are interpretable; "
            "a PI amendment must define cells, pooling, and error propagation before "
            "the companion can return to the Gate-1 evidence set."
        ),
        "minimum_pair_count_diagnostic": minimum_pair_count,
        "n_person_months_age_22_25": int(len(linked)),
        "n_expected_prior_interviews": int(expected.sum()),
        "n_successfully_linked_prior_month": int(linkable.sum()),
        "n_expected_prior_link_failures": int(link_failure.sum()),
        "unweighted_link_failure_rate": (
            float(link_failure.sum() / expected.sum()) if expected.sum() else None
        ),
        "weighted_link_failure_rate": _weighted_share(
            link_failure.loc[expected], linked.loc[expected, "weight"]
        )
        if expected.any() else None,
        "n_linked_labor_market_entries": n_entries,
        "n_entry_mix_cells_observed": int(len(cell_counts)),
        "n_cell_occupation_pairs": int(len(details)),
        "pair_count_min": int(pair_counts.min()) if len(pair_counts) else None,
        "pair_count_median": float(pair_counts.median()) if len(pair_counts) else None,
        "pair_count_max": int(pair_counts.max()) if len(pair_counts) else None,
        "share_linked_entries_in_pairs_below_minimum": sparse_entry_share,
        "occupation_level_pi_go_estimable": bool(
            len(pair_counts) and pair_counts.min() >= minimum_pair_count
        ),
        "outcome_data_opened": False,
        "person_identifiers_committed": False,
        "private_details_committed": False,
    }
    return receipt, details


def main() -> int:
    import pandas as pd

    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--private-details", type=pathlib.Path, required=True)
    parser.add_argument("--minimum-pair-count", type=int, default=20)
    args = parser.parse_args()
    if args.minimum_pair_count < 2:
        raise ValueError("minimum pair count must be at least two")
    frame = (pd.read_parquet(args.extract) if args.extract.suffix == ".parquet"
             else pd.read_csv(args.extract))
    receipt, details = audit_frame(frame, args.minimum_pair_count)
    receipt["generated_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    receipt["input_name"] = args.extract.name
    receipt["input_sha256"] = sha256(args.extract)
    receipt["private_details_name"] = args.private_details.name

    args.private_details.parent.mkdir(parents=True, exist_ok=True)
    details.to_csv(args.private_details, index=False)
    os.chmod(args.private_details, 0o600)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
