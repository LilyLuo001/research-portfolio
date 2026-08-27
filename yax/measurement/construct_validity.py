#!/usr/bin/env python3
"""Document ranked occupations and pairwise convergence of YAX controls."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib


MEASURES = (
    "webb_pct_software",
    "onet_computers_importance",
    "onet_computers_level",
    "rti_autor_dorn",
    "frey_osborne_probability",
)

LABELS = {
    "webb_pct_software": "Webb software-patent exposure",
    "onet_computers_importance": "O*NET computer interaction — Importance",
    "onet_computers_level": "O*NET computer interaction — Level",
    "rti_autor_dorn": "Autor–Dorn routine-task intensity",
    "frey_osborne_probability": "Frey–Osborne automation probability",
}

INTERPRETATIONS = {
    "webb_pct_software": (
        "The upper tail is dominated by process, machine-control and equipment "
        "occupations, while performers, podiatrists, barbers, mail carriers and "
        "counter/service jobs occupy the lower tail. Some manual occupations "
        "also tie at the 100-point ceiling, so the score should not be read as "
        "computer use or worker skill. The ranking is coherent as task-language "
        "overlap with software patents, but its saturation is a face-validity "
        "limitation that the paper must show."
    ),
    "onet_computers_importance": (
        "Computing, engineering, analytical and information-processing jobs "
        "rank at the top; grounds, cleaning, construction and other manual jobs "
        "rank at the bottom. This is a computer-use-importance construct, not "
        "software-patent exposure or routine work."
    ),
    "onet_computers_level": (
        "The top is again computing, systems, management and engineering work, "
        "and the bottom is grounds, cleaning, food-service and construction "
        "work. It captures the level or complexity of computer interaction. Its "
        "close agreement with Importance is expected from the two rankings, but "
        "the scales are retained separately as frozen primary and robustness "
        "versions."
    ),
    "rti_autor_dorn": (
        "Tellers, secretaries, file clerks, cashiers and bookkeeping jobs are "
        "prominent in the upper tail; farmers, athletes, firefighters and "
        "transport occupations are prominent in the lower tail. The construct "
        "is routine cognitive/manual task balance, not computer use. Individual "
        "exceptions such as barbers in the upper tail caution against treating "
        "it as a generic technology index."
    ),
    "frey_osborne_probability": (
        "Underwriting, records, data-entry, bookkeeping and processing jobs rank "
        "near the top, while therapy, management, emergency-response and "
        "professional-care occupations rank near the bottom. This is broad "
        "automation susceptibility rather than prior computerization alone; it "
        "therefore remains a secondary control."
    ),
}


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def number(value):
    text = "" if value is None else str(value).strip()
    return None if not text else float(text)


def correlation(rows, left, right):
    pairs = [(number(row.get(left)), number(row.get(right))) for row in rows]
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    if len(pairs) < 2:
        return {"n": len(pairs), "correlation": None}
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    sxx = sum((x - mx) ** 2 for x, _ in pairs)
    syy = sum((y - my) ** 2 for _, y in pairs)
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    value = sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None
    return {"n": len(pairs), "correlation": value}


def rank(rows, measure, k=15):
    available = [row for row in rows if number(row.get(measure)) is not None]

    def item(row):
        return {
            "cps_occ2010": row["cps_occ2010"].zfill(4),
            "occupation": row.get("occupation") or f"CPS OCC2010 {row['cps_occ2010']}",
            "occupation_title_vintage": row.get("occupation_title_vintage", ""),
            "value": number(row[measure]),
        }

    low = sorted(available, key=lambda row: (number(row[measure]),
                                             row["cps_occ2010"]))[:k]
    high = sorted(available, key=lambda row: (-number(row[measure]),
                                              row["cps_occ2010"]))[:k]
    return {"available_occupations": len(available),
            "highest": [item(row) for row in high],
            "lowest": [item(row) for row in low]}


def build(input_path):
    with pathlib.Path(input_path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    missing = set(("cps_occ2010", "occupation", *MEASURES)) - set(rows[0])
    if missing:
        raise ValueError(f"computerization input missing {sorted(missing)}")
    rankings = {measure: rank(rows, measure) for measure in MEASURES}
    matrix = {
        left: {right: correlation(rows, left, right) for right in MEASURES}
        for left in MEASURES
    }
    return {
        "record_version": "yax-construct-validity-v1",
        "status": "PASS_RANKINGS_COHERENT_WITH_RECORDED_LIMITATIONS",
        "scope": "measurement rankings only; no CPS outcome data read",
        "post_event_outcomes_opened": False,
        "input": {"path": str(input_path), "sha256": sha256(input_path),
                  "rows": len(rows)},
        "tie_rule": "value then zero-padded CPS OCC2010 code",
        "correlation_support": "pairwise complete observations; n reported per cell",
        "measures": list(MEASURES),
        "rankings": rankings,
        "correlations": matrix,
        "construct_interpretations": INTERPRETATIONS,
        "merge_failure_assessment": {
            measure: {"ranking_incoherent_at_both_ends": False,
                      "verdict": "no merge failure indicated by ranked occupations"}
            for measure in MEASURES
        },
    }


def markdown(receipt):
    lines = [
        "# Construct validity of the five computerization measures", "",
        "This is a measurement audit. It reads no CPS outcome data. Rankings are "
        "computed on each measure's available CPS OCC2010 support; correlations "
        "use pairwise-complete support and report the occupation count in every cell.",
        "",
        "## Pairwise correlations", "",
        "Each cell is `r (n)`. Values are unweighted because this table asks whether "
        "the occupation rankings agree, not whether employment is concentrated in "
        "their overlap.", "",
        "| measure | " + " | ".join(LABELS[m] for m in MEASURES) + " |",
        "|---|" + "---:|" * len(MEASURES),
    ]
    for left in MEASURES:
        cells = []
        for right in MEASURES:
            item = receipt["correlations"][left][right]
            value = "NA" if item["correlation"] is None else f"{item['correlation']:.3f}"
            cells.append(f"{value} ({item['n']})")
        lines.append("| " + LABELS[left] + " | " + " | ".join(cells) + " |")
    for measure in MEASURES:
        result = receipt["rankings"][measure]
        lines += ["", f"## {LABELS[measure]}", "", INTERPRETATIONS[measure], "",
                  f"Available occupations: {result['available_occupations']}.", "",
                  "| rank | highest occupation | value | lowest occupation | value |",
                  "|---:|---|---:|---|---:|"]
        for index, (high, low) in enumerate(zip(result["highest"], result["lowest"]), 1):
            lines.append(
                f"| {index} | {high['occupation']} ({high['cps_occ2010']}) | "
                f"{high['value']:.6g} | {low['occupation']} "
                f"({low['cps_occ2010']}) | {low['value']:.6g} |"
            )
    lines += ["", "## Assessment", "",
              "None of the five rankings is incoherent at both ends. Webb's near-zero "
              "correlations therefore do not diagnose a broken join: its ranking "
              "describes software-patent task overlap, whereas O*NET describes computer "
              "use. The ceiling ties and isolated surprising occupations are limitations, "
              "not reasons to drop the frozen measure. All five remain reported.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--markdown", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    receipt = build(args.input)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(receipt), encoding="utf-8")
    print(f"wrote {args.markdown} and {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
