"""Schema and independence checks for private Mapping A v2 labels.

The functions validate metadata but never print task text, rationales, vendor
identities, credentials, or labels.  Callers may emit aggregate sanitized
receipts only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


RELATION_LABELS = frozenset({"D", "F", "N", "U"})
ALLOWED_SPLITS = frozenset({"development", "calibration", "locked_test", "recall_audit"})
REQUIRED_FIELDS = frozenset(
    {
        "onet_task_id",
        "gdpval_task_id",
        "split",
        "annotator_1_label",
        "annotator_1_vendor_family",
        "annotator_2_label",
        "annotator_2_vendor_family",
        "third_label",
        "third_vendor_family",
        "human_label",
        "final_label",
    }
)


def _value(row: Mapping[str, object], field: str) -> str:
    return str(row.get(field, "")).strip()


def validate_independent_labels(
    rows: Iterable[Mapping[str, object]],
    *,
    allowed_splits: set[str] | frozenset[str] = ALLOWED_SPLITS,
) -> dict[str, int]:
    """Validate complete dual-family labels and escalation lineage.

    The third family is mandatory when round-1 labels disagree or either is U,
    and must differ from both initial families.  Final D/F disagreements that
    lack a two-of-three D/F majority require a human D/F decision.  Other
    unresolved cases may conservatively remain U.
    """
    materialized = list(rows)
    if not materialized:
        raise ValueError("label artifact is empty")
    missing_fields = REQUIRED_FIELDS - set(materialized[0])
    if missing_fields:
        raise ValueError(f"label artifact missing fields: {sorted(missing_fields)}")

    seen: set[tuple[str, str]] = set()
    escalated = 0
    human = 0
    for row in materialized:
        pair = (_value(row, "onet_task_id"), _value(row, "gdpval_task_id"))
        if not all(pair) or pair in seen:
            raise ValueError("pair IDs must be non-empty and unique")
        seen.add(pair)
        split = _value(row, "split")
        if split not in allowed_splits:
            raise ValueError(f"forbidden or unknown split: {split}")
        first = _value(row, "annotator_1_label").upper()
        second = _value(row, "annotator_2_label").upper()
        final = _value(row, "final_label").upper()
        if first not in RELATION_LABELS or second not in RELATION_LABELS or final not in RELATION_LABELS:
            raise ValueError("round-1 and final labels must use D/F/N/U")
        family_1 = _value(row, "annotator_1_vendor_family").casefold()
        family_2 = _value(row, "annotator_2_vendor_family").casefold()
        if not family_1 or not family_2 or family_1 == family_2:
            raise ValueError("round-1 annotators require two distinct vendor families")

        needs_third = first != second or "U" in {first, second}
        third = _value(row, "third_label").upper()
        family_3 = _value(row, "third_vendor_family").casefold()
        if needs_third:
            escalated += 1
            if third not in RELATION_LABELS:
                raise ValueError("disagreement/U requires a valid third-family label")
            if not family_3 or family_3 in {family_1, family_2}:
                raise ValueError("third annotator requires a distinct third vendor family")
        elif third or family_3:
            raise ValueError("untriggered third-family fields must remain empty")

        non_u_votes = [label for label in (first, second, third if needs_third else "") if label and label != "U"]
        df_dispute = "D" in non_u_votes and "F" in non_u_votes
        df_majority = max(non_u_votes.count("D"), non_u_votes.count("F")) >= 2
        human_label = _value(row, "human_label").upper()
        if human_label and (human_label not in RELATION_LABELS or final != human_label):
            raise ValueError("a human decision must use D/F/N/U and become final")
        if df_dispute and not df_majority:
            human += 1
            if human_label not in {"D", "F"} or final != human_label:
                raise ValueError("unresolved D/F dispute requires a human D/F final label")
        if not needs_third and final != first:
            raise ValueError("agreed non-U round-1 label must be final")
        if needs_third and not human_label:
            counts = {label: (first, second, third).count(label) for label in RELATION_LABELS}
            majority = [label for label, count in counts.items() if count >= 2]
            expected = majority[0] if majority else "U"
            if final != expected:
                raise ValueError("third-family majority is final; no majority is conservatively U")

    return {"pairs": len(materialized), "third_family_escalations": escalated, "human_resolutions": human}
