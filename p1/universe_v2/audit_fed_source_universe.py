"""Reconcile the public Saglam--Tuzun FEDS Note event evidence to P1.

The note publishes two different objects that must not be conflated:

* an industry-wide aggregate of 125 mutual funds converted by end-2024; and
* Table 1's four fund-to-ETF conversions used in the empirical analysis.

Only the four Table 1 rows are publicly identified.  To keep the published
aggregate visible without inventing names or dates, the source-universe output
contains 121 explicitly labelled, unidentifiable placeholder slots in addition
to the four disclosed rows.  Those placeholders are not treated as events that
can be matched, dated, or excluded from P1.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "output"
MASTER = OUT / "event_master_final_reconciled.csv"
GATE0 = REPO / "p1" / "t2_free" / "nport_gate0_event_level.csv"

FED_NOTE = (
    "https://www.federalreserve.gov/econres/notes/feds-notes/"
    "implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-"
    "conversions-20251119.html"
)
FED_ACCESSIBLE = (
    "https://www.federalreserve.gov/econres/notes/feds-notes/"
    "implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-"
    "conversions-accessible-20251119.htm"
)
FED_CITED_SEC = (
    "https://www.sec.gov/Archives/edgar/data/1816125/"
    "000179420221000103/dimensionaletf497.htm"
)

# Table 1 is the complete event list for the note's empirical conversion shock.
# pre_series_id is a P1 reconciliation key, not a field printed in the note.
TABLE1 = [
    {
        "source_study_event_identifier": "FED2025_T1_01",
        "predecessor_fund_name": "DFA T.A. US Core Equity 2",
        "successor_etf_name": "Dimensional US Core Equity 2 ETF",
        "adviser_sponsor": "Dimensional Fund Advisors LP",
        "source_study_conversion_date": "2021-06-11",
        "source_study_date_precision": "exact_realized_day",
        "net_assets_usd_bn": "13.32",
        "pre_series_id": "S000016732",
    },
    {
        "source_study_event_identifier": "FED2025_T1_02",
        "predecessor_fund_name": "DFA Tax-Managed US Equity",
        "successor_etf_name": "Dimensional US Equity ETF",
        "adviser_sponsor": "Dimensional Fund Advisors LP",
        "source_study_conversion_date": "2021-06-11",
        "source_study_date_precision": "exact_realized_day",
        "net_assets_usd_bn": "5.58",
        "pre_series_id": "S000000972",
    },
    {
        "source_study_event_identifier": "FED2025_T1_03",
        "predecessor_fund_name": "DFA Tax-Managed US Small Cap",
        "successor_etf_name": "Dimensional US Small Cap ETF",
        "adviser_sponsor": "Dimensional Fund Advisors LP",
        "source_study_conversion_date": "2021-06-11",
        "source_study_date_precision": "exact_realized_day",
        "net_assets_usd_bn": "3.97",
        "pre_series_id": "S000000976",
    },
    {
        "source_study_event_identifier": "FED2025_T1_04",
        "predecessor_fund_name": "DFA Tax-Managed US Targeted Value",
        "successor_etf_name": "Dimensional US Targeted Value ETF",
        "adviser_sponsor": "Dimensional Fund Advisors LP",
        "source_study_conversion_date": "2021-06-11",
        "source_study_date_precision": "exact_realized_day",
        "net_assets_usd_bn": "5.91",
        "pre_series_id": "S000000977",
    },
]


def _bool(v: bool) -> str:
    return "TRUE" if bool(v) else "FALSE"


def build_source_universe() -> pd.DataFrame:
    rows = []
    for r in TABLE1:
        rows.append(
            {
                **{k: v for k, v in r.items() if k != "pre_series_id"},
                "source_scope": "empirical_sample_table_1",
                "published_row_status": "identified",
                "included_in_published_125_aggregate": "TRUE",
                "source_locator": f"{FED_NOTE}#table-1",
                "source_cited_sec_locator": FED_CITED_SEC,
                "public_replication_row_available": "FALSE",
                "source_record_limitation": "",
            }
        )

    # The public note reports 125 but does not disclose the other 121 records.
    # One placeholder per undisclosed unit prevents the aggregate from silently
    # becoming either four rows or an invented list.
    for i in range(5, 126):
        rows.append(
            {
                "source_study_event_identifier": f"FED2025_AGG_UNPUBLISHED_{i:03d}",
                "predecessor_fund_name": "",
                "successor_etf_name": "",
                "adviser_sponsor": "",
                "source_study_conversion_date": "",
                "source_study_date_precision": "not_published",
                "net_assets_usd_bn": "",
                "source_scope": "narrative_aggregate_only",
                "published_row_status": "unidentified_placeholder",
                "included_in_published_125_aggregate": "TRUE",
                "source_locator": f"{FED_NOTE}#section-1-introduction",
                "source_cited_sec_locator": "",
                "public_replication_row_available": "FALSE",
                "source_record_limitation": (
                    "The note publishes only the aggregate count; no fund name, "
                    "ETF name, identifier, or date is supplied for this slot."
                ),
            }
        )
    source = pd.DataFrame(rows)
    assert len(source) == 125
    assert (source.published_row_status == "identified").sum() == 4
    return source


def build_crosswalk(source: pd.DataFrame, master: pd.DataFrame,
                    gate0: pd.DataFrame) -> pd.DataFrame:
    by_pre = master.set_index("pre_series_id", drop=False)
    g = gate0.set_index("event_id", drop=False)
    pre_key = {r["source_study_event_identifier"]: r["pre_series_id"]
               for r in TABLE1}
    rows = []
    for s in source.itertuples(index=False):
        key = pre_key.get(s.source_study_event_identifier)
        if key is None:
            rows.append(
                {
                    **s._asdict(),
                    "p1_event_id": "",
                    "p1_pre_series_id": "",
                    "p1_pre_cik": "",
                    "p1_pre_class_ids": "",
                    "p1_pre_tickers": "",
                    "p1_post_series_id": "",
                    "p1_post_cik": "",
                    "p1_post_class_ids": "",
                    "p1_predecessor_name": "",
                    "p1_successor_name": "",
                    "p1_current_effective_date": "",
                    "p1_current_precision_class": "",
                    "p1_verified_date_source_accession": "",
                    "p1_verified_date_source_form": "",
                    "p1_in_156_completed_universe": "UNKNOWN",
                    "p1_in_74_timing_eligible_universe": "UNKNOWN",
                    "p1_in_71_gate0_pass_universe": "UNKNOWN",
                    "p1_wave_id": "",
                    "match_status": "unmatchable_source_record_not_published",
                    "exclusion_reason": (
                        "Not adjudicable: the Fed note withholds the row-level "
                        "identity behind this aggregate slot."
                    ),
                }
            )
            continue

        m = by_pre.loc[key]
        if isinstance(m, pd.DataFrame):
            raise AssertionError(f"duplicate master pre_series_id: {key}")
        completed = str(m.final_tier).startswith(("A_", "B_"))
        timing = str(m.timing_eligible_primary).lower() == "true"
        gate_row = g.loc[m.event_id] if m.event_id in g.index else None
        gate_pass = gate_row is not None and gate_row.gate0 == "PASS"
        rows.append(
            {
                **s._asdict(),
                "p1_event_id": m.event_id,
                "p1_pre_series_id": m.pre_series_id,
                "p1_pre_cik": m.pre_cik,
                "p1_pre_class_ids": m.pre_class_ids,
                "p1_pre_tickers": m.pre_tickers,
                "p1_post_series_id": m.post_series_id,
                "p1_post_cik": m.post_cik,
                "p1_post_class_ids": m.post_class_ids,
                "p1_predecessor_name": m.pre_series_name,
                "p1_successor_name": m.post_series_name,
                "p1_current_effective_date": m.final_effective_date,
                "p1_current_precision_class": m.final_precision,
                "p1_verified_date_source_accession":
                    m.verified_date_source_accession,
                "p1_verified_date_source_form": m.verified_date_source_form,
                "p1_in_156_completed_universe": _bool(completed),
                "p1_in_74_timing_eligible_universe": _bool(timing),
                "p1_in_71_gate0_pass_universe": _bool(gate_pass),
                "p1_wave_id": gate_row.wave_id if gate_row is not None else "",
                "match_status": "exact_match",
                "exclusion_reason": "" if gate_pass else (
                    gate_row.failure_reason if gate_row is not None
                    else "not present in Gate0 event file"
                ),
            }
        )
    out = pd.DataFrame(rows)
    assert len(out) == 125
    assert (out.match_status == "exact_match").sum() == 4
    return out


def build_excluded_audit(master: pd.DataFrame) -> pd.DataFrame:
    completed = master.final_tier.str.startswith(("A_", "B_"), na=False)
    timing = master.timing_eligible_primary.astype(str).str.lower() == "true"
    q = master[completed & ~timing].copy()
    assert len(q) == 82, len(q)
    expected = {
        "proposed_exact_day_only": 14,
        "month_only": 57,
        "bounded_window": 9,
        "year_only": 2,
    }
    assert q.final_precision.value_counts().to_dict() == expected

    keep = [
        "event_id", "pre_series_id", "pre_series_name", "pre_cik",
        "pre_class_ids", "pre_tickers", "post_series_id", "post_series_name",
        "post_cik", "post_class_ids", "adviser", "final_tier",
        "final_effective_date", "final_precision", "final_source_accession",
        "final_proposed_day", "proposed_effective_date_source",
        "cease_window_lo", "cease_window_hi", "completion_evidence",
    ]
    out = q[keep].copy()
    out["source_study_empirical_match"] = "FALSE"
    out["source_study_exact_date_available"] = "FALSE"
    out["source_study_conversion_date"] = ""
    out["source_study_date_precision"] = "not_applicable_not_enumerated"
    out["source_study_locator_checked"] = (
        FED_NOTE + "#table-1 | " + FED_ACCESSIBLE + " | " + FED_CITED_SEC
    )
    out["upgradeable_from_public_source_study_evidence"] = "FALSE"
    out["audit_disposition"] = "no_upgrade_from_fed_source"
    out["audit_reason"] = (
        "This P1 event is not one of the four conversions enumerated in the "
        "Fed note's empirical Table 1. The note's 125-event industry statement "
        "has no public row-level names or dates, and its sole cited conversion "
        "filing covers only the four June 2021 Dimensional events."
    )
    return out.sort_values(["final_precision", "event_id"])


def build_summary(source: pd.DataFrame, cross: pd.DataFrame,
                  master: pd.DataFrame, gate0: pd.DataFrame,
                  excluded: pd.DataFrame) -> pd.DataFrame:
    completed = master[master.final_tier.str.startswith(("A_", "B_"), na=False)]
    exact = completed[completed.final_precision == "verified_exact_day"]
    p1_2024 = completed[pd.to_numeric(completed.final_year, errors="coerce") <= 2024]
    metrics = [
        ("fed_reported_industry_conversions_through_2024", 125,
         "predecessor funds (aggregate)", "reported_not_row_level",
         "Narrative aggregate; do not treat as the empirical regression sample."),
        ("fed_publicly_identified_industry_rows", 4, "fund conversions",
         "verified", "The four Table 1 events are identifiable within the 125."),
        ("fed_unidentified_aggregate_slots", 121, "aggregate slots",
         "unresolved", "No public row-level list or replication file was found."),
        ("fed_empirical_sample_completed_conversions", 4, "fund conversions",
         "verified", "Complete Table 1 empirical event list."),
        ("fed_empirical_sample_distinct_conversion_dates", 1, "dates",
         "verified", "All four converted on 2021-06-11."),
        ("fed_source_rows_with_public_exact_realized_date", 4,
         "fund conversions", "verified",
         "Remaining 121 aggregate slots have unknown public date availability."),
        ("fed_empirical_rows_exact_matched_to_p1", 4, "fund conversions",
         "verified", "All four match by predecessor/successor/date."),
        ("fed_empirical_rows_missing_from_p1_156", 0, "fund conversions",
         "verified", "Zero among the four publicly enumerated empirical events."),
        ("fed_aggregate_rows_confirmed_in_p1_156", 4, "fund conversions",
         "lower_bound", "The other 121 cannot be row-matched without the source list."),
        ("fed_aggregate_rows_missing_from_p1_156", "UNKNOWN", "fund conversions",
         "not_identifiable", "The aggregate-only source does not disclose identities."),
        ("p1_structural_members", len(master), "P1 event rows", "verified", ""),
        ("p1_completed_conversions_all_years", len(completed),
         "predecessor funds", "verified", "Includes 2025-2026 and 9 ambiguous-year rows."),
        ("p1_completed_conversions_through_2024", len(p1_2024),
         "predecessor funds", "verified", "Comparable cutoff, but definitions may differ."),
        ("arithmetic_gap_fed_125_minus_p1_through_2024", 125 - len(p1_2024),
         "predecessor funds", "open", "Cannot be named without the Fed/Morningstar rows."),
        ("p1_verified_exact_day_timing_eligible", len(exact),
         "fund conversions", "verified", ""),
        ("p1_completed_excluded_nonexact", len(excluded),
         "fund conversions", "verified", "14 proposed, 57 month, 9 bounded, 2 year."),
        ("source_public_exact_dates_not_verified_in_p1", 0,
         "fund conversions", "verified", "All four published dates already verified."),
        ("excluded_82_upgradable_from_public_fed_evidence", 0,
         "fund conversions", "verified", "None is enumerated in the published empirical list."),
        ("fed_empirical_events_in_gate0_pass", int((cross.p1_in_71_gate0_pass_universe == "TRUE").sum()),
         "fund conversions", "verified", "All four are in wave W002."),
        ("p1_gate0_pass_events", int((gate0.gate0 == "PASS").sum()),
         "fund conversions", "verified", "Conditional analysis subset, not the Fed aggregate."),
        ("p1_gate0_pass_waves", gate0.loc[gate0.gate0 == "PASS", "wave_id"].nunique(),
         "waves", "verified", ""),
        ("scc_wrds_mutualfund_schema_present", 0, "schema inventories",
         "absent_from_mirror",
         "Read-only FINAL_SCC_MANIFEST/meta audit found CRSP mutual-fund schemas "
         "but no wrds_mutualfund schema or extract."),
    ]
    out = pd.DataFrame(metrics, columns=["metric", "value", "unit", "status", "note"])
    assert int(out.loc[out.metric == "p1_completed_excluded_nonexact", "value"].iloc[0]) == 82
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    master = pd.read_csv(MASTER, dtype=str, keep_default_na=False)
    gate0 = pd.read_csv(GATE0, dtype=str, keep_default_na=False)
    source = build_source_universe()
    cross = build_crosswalk(source, master, gate0)
    excluded = build_excluded_audit(master)
    summary = build_summary(source, cross, master, gate0, excluded)

    source.to_csv(OUT / "fed_source_event_universe.csv", index=False)
    cross.to_csv(OUT / "fed_to_p1_event_crosswalk.csv", index=False)
    excluded.to_csv(OUT / "excluded_82_source_date_audit.csv", index=False)
    summary.to_csv(OUT / "event_universe_reconciliation_summary.csv", index=False)
    print("wrote Fed source reconciliation outputs")
    print(summary[["metric", "value", "status"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
