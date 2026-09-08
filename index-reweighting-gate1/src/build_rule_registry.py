#!/usr/bin/env python3
"""Build the Gate-1 institutional-rule, event, and assignment-evidence tables.

This builder is deliberately limited to public primary-source evidence.  It does
not infer an exact assignment vector from ETF holdings, market capitalization,
or differently dated snapshots.  Blank numeric fields are intentional when the
historical public record is incomplete.
"""

from __future__ import annotations

import argparse
import csv
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable


RETRIEVAL_DATE = "2026-09-08"

SOURCE_HEADERS = [
    "evidence_key", "rule_id", "index_family", "index_name", "index_code",
    "regime_id", "rule_scope", "rule_level", "source_id", "source_title",
    "source_type", "publisher", "publication_date", "effective_start",
    "effective_end", "document_status", "status", "source_url", "archive_url",
    "retrieval_date", "source_sha256", "source_pages",
    "trigger_single_company_pct", "target_single_company_pct",
    "trigger_large_company_pct", "trigger_aggregate_pct",
    "target_aggregate_pct", "input_weighting", "order_of_operations",
    "reference_date_rule", "implementation_rule", "secondary_check_rule",
    "precision_notes", "grade_dimension", "rule_source_grade", "limitations", "notes",
]

EVENT_HEADERS = [
    "evidence_key", "event_id", "event_group_id", "index_family", "index_name",
    "index_code", "sector", "event_type", "calendar_scope", "regime_id",
    "input_reference_date", "earliest_public_announcement_date",
    "pro_forma_available_date", "implementation_close_date", "effective_open_date",
    "secondary_adjustment_date", "next_intervention_date", "binding_status",
    "status", "assignment_observability", "comparison_id",
    "interference_event_ids", "rule_evidence_keys", "source_id", "source_url",
    "retrieval_date", "grade_dimension", "classification_evidence_grade",
    "assignment_evidence_grade", "limitations", "notes",
]

DOSE_HEADERS = [
    "evidence_key", "event_id", "security_or_all", "issuer_name", "security_name",
    "ticker", "identifier", "assignment_level", "uncapped_reference_weight_pct",
    "uncapped_reference_status", "rule_assigned_weight_pct",
    "rule_assignment_status", "rebalance_change_weight_pct", "cap_distortion_pct",
    "etf_holding_weight_pct", "etf_holdings_status", "creation_basket_weight_pct",
    "creation_basket_status", "reported_one_way_turnover_pct",
    "numeric_precision_pct", "vector_complete", "dose_status", "uncapped_source_id",
    "assignment_source_id", "etf_holdings_source_id", "creation_basket_source_id",
    "source_id", "source_url", "retrieval_date", "grade_dimension",
    "evidence_grade", "status",
    "limitations", "notes",
]


URLS = {
    "sp_method": "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf",
    "sp_s1": "https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20240903-1474128/1474128_sp-select-sector-indices-results-20240903.pdf",
    "sp_s2": "https://www.spglobal.com/spdji/en/documents/additional-material/select-sector-capping-impact-analysis-20240808.pdf",
    "sp_dec": "https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20241202-1475776/1475776_constituent-weighting-reference-date-update-20241202.pdf",
    "sp_math": "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-index-math.pdf",
    "sp_policy": "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-equity-indices-policies-practices.pdf?force_download=true",
    "ndx_change": "https://indexes.nasdaqomx.com/docs/Methodology_Change_Log_NDX.pdf",
    "ndx_method": "https://indexes.nasdaq.com/docs/Methodology_NDX.pdf",
    "ndx_special": "https://indexes.nasdaqomx.com/docs/NDX_SpecialRebalance_2023.pdf",
    "ndx_press": "https://www.nasdaq.com/press-release/the-nasdaq-100-index-special-rebalance-to-be-effective-july-24-2023-2023-07-07",
    "ndx_post": "https://www.nasdaq.com/articles/all-about-index-concentration",
    "ndx_weighting": "https://indexes.nasdaqomx.com/Index/Weighting/NDX",
    "ndx_guide": "https://indexes.nasdaq.com/docs/Nasdaq_Index_Weight_Calculations.pdf",
    "ndx_stock_2019": "https://www.sec.gov/Archives/edgar/data/886982/000156459019044233/gs-424b2.htm",
    "ndx_stock_2020q1": "https://www.sec.gov/Archives/edgar/data/886982/000156459020012750/gs-424b2.htm",
    "ndx_issuer_202007": "https://www.sec.gov/Archives/edgar/data/886982/000156459020031554/gs-424b2.htm",
    "ndx_ttd_atvi": "https://www.nasdaq.com/press-release/the-trade-desk-inc.-to-join-the-nasdaq-100-index-beginning-july-17th-2023-2023-07-12",
}


def _rule(rule_id: str, **values: str) -> dict[str, str]:
    row = {name: "" for name in SOURCE_HEADERS}
    grade = values.pop("evidence_grade", values.pop("rule_source_grade", ""))
    index_family = values.get("index_family", "")
    default_publisher = (
        "Nasdaq, Inc."
        if index_family.startswith("Nasdaq")
        else "S&P Dow Jones Indices LLC"
    )
    row.update(
        evidence_key=f"RULE:{rule_id}",
        rule_id=rule_id,
        retrieval_date=RETRIEVAL_DATE,
        publisher=values.pop("publisher", default_publisher),
        grade_dimension="rule/source completeness; never assignment observability",
        rule_source_grade=grade,
    )
    row.update(values)
    return row


def build_source_registry() -> list[dict[str, str]]:
    """Return source-linked regimes; grades describe rule/source completeness."""
    rows = [
        _rule(
            "SP_SS_WEIGHTING_20180308_20240919",
            index_family="S&P Select Sector",
            index_name="S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            regime_id="SP_SS_20180308_20240919",
            rule_scope="quarterly constituent weighting",
            rule_level="company; security lines allocated within company",
            source_id="SPDJI_US_INDICES_METHOD_202607",
            source_title="S&P U.S. Indices Methodology (living document; Appendix C change history)",
            source_type="official methodology and retrospective change log",
            publication_date="2026-07",
            effective_start="2018-03-08",
            effective_end="2024-09-19",
            document_status="OFFICIAL_LIVING_DOCUMENT_WEB_READER_VERIFIED",
            status="CONFIRMED_HISTORICAL_RULE",
            source_url=URLS["sp_method"],
            source_pages="Select Sector weighting section; Appendix C change history",
            trigger_single_company_pct="24",
            target_single_company_pct="23",
            trigger_large_company_pct="4.8",
            trigger_aggregate_pct="50",
            target_aggregate_pct="",
            input_weighting="company float-adjusted market capitalization (FMC)",
            order_of_operations="Cap any company above 24% to 23% and redistribute proportionally; if the post-step sum of companies above 4.8% exceeds 50%, rank by descending FMC and iteratively reduce the smallest company causing the breach to 4.5%; redistribute excess proportionally, repeating as necessary; allocate a capped company across multiple share classes in proportion to line FMC.",
            reference_date_rule="Closing prices on second Friday of March, June, September, or December; effective-date membership, shares, and IWFs.",
            implementation_rule="After close of third Friday; effective at next market open.",
            secondary_check_rule="See separate regime rows.",
            precision_notes="Thresholds and targets are exact methodology percentages; no historical vector is supplied by this row.",
            evidence_grade="A",
            limitations="Current living file documents the historical rule retrospectively; direct PDF transport returned HTTP 403 in this environment, while the official PDF rendered through the web reader.",
            notes="Evidence grade A here means exact rule text, not an A-grade historical assignment.",
        ),
        _rule(
            "SP_SS_SECONDARY_TO_20190429",
            index_family="S&P Select Sector",
            index_name="S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            regime_id="SP_SS_SECONDARY_TO_20190429",
            rule_scope="additional capping review",
            rule_level="company",
            source_id="SPDJI_US_INDICES_METHOD_202607",
            source_title="S&P U.S. Indices Methodology (Appendix C prior-text description)",
            source_type="official retrospective change log",
            publication_date="2026-07",
            effective_start="2018-03-08",
            effective_end="2019-04-29",
            document_status="OFFICIAL_LIVING_DOCUMENT_WEB_READER_VERIFIED",
            status="CONFIRMED_REVIEW_RULE_DATE_UNRESOLVED",
            source_url=URLS["sp_method"],
            source_pages="Appendix C change effective 2019-04-30",
            trigger_single_company_pct="24",
            target_single_company_pct="23",
            trigger_large_company_pct="4.8",
            trigger_aggregate_pct="50",
            input_weighting="not fully recoverable from the current change-log excerpt",
            order_of_operations="Prior language allowed an additional capping review when necessary; exact contemporaneous timing and inputs were not recovered.",
            reference_date_rule="Unknown in the accessible retrospective excerpt.",
            implementation_rule="Potential review before the close of the last business day of the quarter-end month.",
            secondary_check_rule="Not treated as a fixed dated check in the event ledger.",
            precision_notes="Do not infer nonbinding from the absence of a fixed date.",
            evidence_grade="U",
            limitations="A contemporaneous pre-2019 methodology version was not publicly recovered.",
            notes="The ledger retains potential rows with blank check dates and uncertain binding status.",
        ),
        _rule(
            "SP_SS_COMMUNICATION_SERVICES_FROM_20180924",
            index_family="S&P Select Sector",
            index_name="Communication Services Select Sector Index",
            index_code="IXC",
            regime_id="SP_SS_GICS_20180924",
            rule_scope="sector-classification eligibility",
            rule_level="security classification",
            source_id="SPDJI_US_INDICES_METHOD_202607",
            source_title="S&P U.S. Indices Methodology (Appendix C change history)",
            source_type="official retrospective change log",
            publication_date="2026-07",
            effective_start="2018-09-24",
            effective_end="",
            document_status="OFFICIAL_LIVING_DOCUMENT_WEB_READER_VERIFIED",
            status="CONFIRMED_SECTOR_REORGANIZATION",
            source_url=URLS["sp_method"],
            source_pages="Appendix C change effective 2018-09-24",
            input_weighting="S&P 500 constituents assigned by post-reorganization GICS sector",
            order_of_operations="Information Technology eligibility became GICS Information Technology only; the new Communication Services classification was handled separately.",
            reference_date_rule="Effective with the September 2018 sector reorganization.",
            implementation_rule="Effective 2018-09-24.",
            secondary_check_rule="not applicable",
            precision_notes="Calendar rows before 2018Q3 are marked outside the current Communication Services index regime.",
            evidence_grade="A",
            limitations="This row records eligibility timing, not an assignment vector.",
            notes="Pre-transition Telecommunication Services is not silently relabeled as current Communication Services.",
        ),
        _rule(
            "SP_SS_SECONDARY_20190430_20200830",
            index_family="S&P Select Sector",
            index_name="S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            regime_id="SP_SS_SECONDARY_20190430_20200830",
            rule_scope="quarter-end secondary capping check",
            rule_level="company",
            source_id="SPDJI_US_INDICES_METHOD_202607",
            source_title="S&P U.S. Indices Methodology (Appendix C change history)",
            source_type="official retrospective change log",
            publication_date="2026-07",
            effective_start="2019-04-30",
            effective_end="2020-08-30",
            document_status="OFFICIAL_LIVING_DOCUMENT_WEB_READER_VERIFIED",
            status="CONFIRMED_HISTORICAL_RULE",
            source_url=URLS["sp_method"],
            source_pages="Appendix C change effective 2019-04-30",
            trigger_single_company_pct="24",
            target_single_company_pct="23",
            trigger_large_company_pct="4.8",
            trigger_aggregate_pct="50",
            input_weighting="closing weights/prices at the third-to-last business day",
            order_of_operations="Run trigger checks; if binding, rerun the then-current quarterly capping procedure.",
            reference_date_rule="Third-to-last business day of March, June, September, or December.",
            implementation_rule="Effective at the open of the last business day of the month.",
            secondary_check_rule="A scheduled check is not a realized reweighting; binding must be established event by event.",
            precision_notes="Calendar rule exact; historical doses not supplied.",
            evidence_grade="A",
            limitations="Retrospective official change history, not a historical pro forma file.",
            notes="Evidence grade A applies to the calendar rule only.",
        ),
        _rule(
            "SP_SS_SECONDARY_20200831_20240919",
            index_family="S&P Select Sector",
            index_name="S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            regime_id="SP_SS_SECONDARY_20200831_20240919",
            rule_scope="quarter-end secondary capping check",
            rule_level="company",
            source_id="SPDJI_S2_20240808",
            source_title="Select Sector Indices — Capping Considerations & Analysis",
            source_type="official analysis with historical secondary-check appendix",
            publication_date="2024-08-08",
            effective_start="2020-08-31",
            effective_end="2024-09-19",
            document_status="OFFICIAL_PDF_WEB_READER_VERIFIED",
            status="CONFIRMED_HISTORICAL_RULE_AND_ROUNDED_EVENT_SCREEN",
            source_url=URLS["sp_s2"],
            source_pages="6-8; 30-37",
            trigger_single_company_pct="24",
            target_single_company_pct="23",
            trigger_large_company_pct="4.8",
            trigger_aggregate_pct="50",
            input_weighting="closing prices and company weights at second-to-last business day, with effective-date membership, shares, and IWFs",
            order_of_operations="Check either threshold; if binding, rerun the then-current quarterly capping algorithm using updated inputs.",
            reference_date_rule="Second-to-last business day of quarter-end month.",
            implementation_rule="After close of last business day; effective next market open.",
            secondary_check_rule="Appendix reports rounded current-rule maximum and aggregate weights for March 2020 through June 2024.",
            precision_notes="Appendix percentages are rounded to whole percentage points; boundary displays of 24 or 50 remain uncertain.",
            evidence_grade="B",
            limitations="Historical appendix is labelled illustrative/hypothetical; it is adequate for conservative breach screening but not an exact assignment vector.",
            notes="Current-rule columns are kept separate from proposed iterative backtests.",
        ),
        _rule(
            "SP_SS_WEIGHTING_FROM_20240920",
            index_family="S&P Select Sector",
            index_name="S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            regime_id="SP_SS_20240920_20241220",
            rule_scope="quarterly constituent weighting",
            rule_level="company; security lines allocated within company",
            source_id="SPDJI_S1_20240903",
            source_title="Select Sector Constituent Weighting Consultation Results",
            source_type="official contemporaneous implementation notice",
            publication_date="2024-09-03",
            effective_start="2024-09-20",
            effective_end="",
            document_status="OFFICIAL_PDF_WEB_READER_VERIFIED",
            status="CONFIRMED_RULE_CHANGE",
            source_url=URLS["sp_s1"],
            source_pages="1-3",
            trigger_single_company_pct="24",
            target_single_company_pct="23",
            trigger_large_company_pct="4.8",
            trigger_aggregate_pct="50",
            target_aggregate_pct="45",
            input_weighting="company float-adjusted market capitalization (FMC)",
            order_of_operations="If any FMC company exceeds 24%, cap every company at 23%; if companies above 4.8% sum above 50%, set each such company to max(45% times its weight divided by that cohort's total, 4.5%); redistribute excess from all capping steps to companies with initial weights below 4.8%, each capped at 4.5%; then assign index shares. Multiple share classes are allocated within company in proportion to FMC.",
            reference_date_rule="Second Friday through September 2024; changed separately beginning December 2024.",
            implementation_rule="First implemented after the 2024-09-20 close, effective before the 2024-09-23 market open; pro forma began 2024-09-13.",
            secondary_check_rule="See SP_SS_SECONDARY_FROM_20240920.",
            precision_notes="Formula and thresholds exact; event-specific full vector not public in this notice.",
            evidence_grade="A",
            limitations="The notice does not include the complete September 2024 assignment vector or contemporaneous FMC inputs.",
            notes="One common policy transition across all 11 sector indexes, not 11 independent interventions.",
        ),
        _rule(
            "SP_SS_SECONDARY_FROM_20240920",
            index_family="S&P Select Sector",
            index_name="S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            regime_id="SP_SS_SECONDARY_FROM_20240920",
            rule_scope="quarter-end secondary capping check",
            rule_level="company",
            source_id="SPDJI_S1_20240903",
            source_title="Select Sector Constituent Weighting Consultation Results",
            source_type="official contemporaneous implementation notice",
            publication_date="2024-09-03",
            effective_start="2024-09-20",
            effective_end="",
            document_status="OFFICIAL_PDF_WEB_READER_VERIFIED",
            status="CONFIRMED_RULE_CHANGE",
            source_url=URLS["sp_s1"],
            source_pages="2-3",
            trigger_single_company_pct="24",
            target_single_company_pct="23",
            trigger_large_company_pct="4.8",
            trigger_aggregate_pct="50",
            target_aggregate_pct="45",
            input_weighting="capped index weights/current AWFs at second-to-last business day, adjusted for effective-date changes",
            order_of_operations="Check thresholds using capped index weights; if binding, apply the updated iterative capping procedure.",
            reference_date_rule="Second-to-last business day of March, June, September, or December.",
            implementation_rule="After close of last business day; effective next market open.",
            secondary_check_rule="Potential checks are scheduled; realized reweightings require separate evidence of a breach.",
            precision_notes="Exact process, but no post-September-2024 public event vectors recovered.",
            evidence_grade="A",
            limitations="No complete public historical pro forma/assignment files were recovered.",
            notes="Do not recode an unobserved breach as nonbinding.",
        ),
        _rule(
            "SP_SS_REFERENCE_DATE_FROM_20241221",
            index_family="S&P Select Sector",
            index_name="S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            regime_id="SP_SS_FROM_20241221",
            rule_scope="quarterly weighting reference date",
            rule_level="company",
            source_id="SPDJI_REFDATE_20241202",
            source_title="Constituent Weighting Reference Date Update",
            source_type="official contemporaneous implementation notice",
            publication_date="2024-12-02",
            effective_start="2024-12-21",
            effective_end="",
            document_status="OFFICIAL_PDF_WEB_READER_VERIFIED",
            status="CONFIRMED_RULE_CHANGE",
            source_url=URLS["sp_dec"],
            source_pages="1-2",
            input_weighting="same updated company FMC procedure; only reference-date timing changed",
            order_of_operations="Apply the post-September-2024 capping algorithm.",
            reference_date_rule="Wednesday before the second Friday of the rebalance month.",
            implementation_rule="First applied after 2024-12-20 close, effective before 2024-12-23 open; pro forma began 2024-12-13.",
            secondary_check_rule="Unchanged by this notice.",
            precision_notes="Dates exact; no complete event assignment vector included.",
            evidence_grade="A",
            limitations="No full December 2024 assignment file in the public notice.",
            notes="The methodology change date and next-open effective date are distinct.",
        ),
        _rule(
            "SP_SS_2024_ROUNDED_ASSIGNMENT_TABLES",
            index_family="S&P Select Sector",
            index_name="Technology Select Sector Index",
            index_code="IXT",
            regime_id="SP_SS_20180308_20240919",
            rule_scope="March and June 2024 assignment evidence",
            rule_level="company",
            source_id="SPDJI_S2_20240808",
            source_title="Select Sector Indices — Capping Considerations & Analysis",
            source_type="official analysis with rounded selected-weight tables",
            publication_date="2024-08-08",
            effective_start="2024-03-15",
            effective_end="2024-06-24",
            document_status="OFFICIAL_PDF_WEB_READER_VERIFIED",
            status="VERIFIED_INCOMPLETE_ASSIGNMENT_EVIDENCE",
            source_url=URLS["sp_s2"],
            source_pages="3; 10-15; 30-39",
            trigger_single_company_pct="24",
            target_single_company_pct="23",
            trigger_large_company_pct="4.8",
            trigger_aggregate_pct="50",
            input_weighting="displayed company FMC weights",
            order_of_operations="The 'Current' column reflects the then-current rank-cliff procedure; 'Iterative Capping' is a proposed hypothetical and is never used as realized treatment.",
            reference_date_rule="March chart states hypothetical application on 2024-03-15; June chart states 2024-06-21.",
            implementation_rule="Effective opens 2024-03-18 and 2024-06-24.",
            secondary_check_rule="Separate appendix supplies rounded secondary-check screens, not precise assignments.",
            precision_notes="Top-15 values rounded to 0.1 percentage point; vector incomplete and not renormalized.",
            evidence_grade="B",
            limitations="Retrospective, selected, rounded charts; not a full official pro forma vector and not proof of trader-time availability.",
            notes="The page-3 narrative uses a different snapshot/rounding than page-10; the dose table consistently uses the same page-10 columns.",
        ),
        _rule(
            "SP_INDEX_OBJECT_DEFINITIONS_CURRENT",
            index_family="S&P methodology supplement",
            index_name="S&P capped equity index calculations",
            index_code="GENERAL",
            regime_id="CURRENT_ONLY_202608",
            rule_scope="definitions distinguishing uncapped and capped weights",
            rule_level="security and company depending index",
            source_id="SPDJI_INDEX_MATH_202608",
            source_title="Index Mathematics Methodology",
            source_type="official current methodology supplement",
            publication_date="2026-08",
            effective_start="2026-08",
            effective_end="",
            document_status="OFFICIAL_PDF_WEB_READER_VERIFIED",
            status="CURRENT_DEFINITION_ONLY",
            source_url=URLS["sp_math"],
            source_pages="10-11",
            input_weighting="uncapped market-cap weights and capped weights via adjustment factors",
            order_of_operations="Defines capping and redistribution mechanics and drift after implementation.",
            reference_date_rule="Index-specific.",
            implementation_rule="Index-specific.",
            secondary_check_rule="Index-specific.",
            precision_notes="Not used to backcast historical inputs.",
            evidence_grade="A",
            limitations="Current generic definitions do not supply historical Select Sector vectors.",
            notes="Supports the four-object separation in the dose table.",
        ),
        _rule(
            "SP_PROFORMA_REPLICATION_ACCESS_CURRENT",
            index_family="S&P Select Sector",
            index_name="S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            regime_id="CURRENT_ACCESS_POLICY",
            rule_scope="pro forma and replication-data access",
            rule_level="file/access policy",
            source_id="SPDJI_EQUITY_POLICY_202608",
            source_title="Equity Indices Policies & Practices Methodology",
            source_type="official current data policy",
            publication_date="2026-08",
            effective_start="2026-08",
            effective_end="",
            document_status="OFFICIAL_PDF_WEB_READER_VERIFIED",
            status="BLOCKED_PUBLIC_HISTORICAL_ASSIGNMENT",
            source_url=URLS["sp_policy"],
            source_pages="31-32; 49",
            input_weighting="not applicable",
            order_of_operations="not applicable",
            reference_date_rule="Pro forma files generally precede implementation, but event-specific historical public files were not recovered.",
            implementation_rule="Complete replication data are distributed through provider products/client channels.",
            secondary_check_rule="not applicable",
            precision_notes="No numeric assignment inferred from access-policy text.",
            evidence_grade="U",
            limitations="The public methodology describes delivery; it does not expose the historical assignment contents required for grade A.",
            notes="An access gap is not evidence that the assignments do not exist.",
        ),
        _rule(
            "NDX_SECURITY_LEVEL_2018_2020Q1_SNAPSHOT",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="NDX_SECURITY_LEVEL_SCREEN_2018_2020Q1",
            rule_scope="historical quarterly weighting snapshot",
            rule_level="stock/security; not issuer aggregate",
            source_id="SEC_GS_NDX_STOCK_METHOD_20191122",
            source_title="Goldman Sachs Underlier Supplement No. 1",
            source_type="contemporaneous SEC-filed methodology description",
            publisher="The Goldman Sachs Group, Inc. (SEC filer)",
            publication_date="2019-11-22",
            effective_start="",
            effective_end="2020-03-24",
            document_status="SEC_FILED_CONTEMPORANEOUS_DESCRIPTION",
            status="HISTORICAL_RULE_LEVEL_DOCUMENTED_TRANSITION_DATE_UNRESOLVED",
            source_url=URLS["ndx_stock_2019"],
            archive_url=URLS["ndx_stock_2020q1"],
            source_pages="HTML lines 1831-1852; corroborated 2020-03-24 lines 2179-2195",
            trigger_single_company_pct="24",
            target_single_company_pct="20",
            trigger_large_company_pct="4.5",
            trigger_aggregate_pct="48",
            target_aggregate_pct="40",
            input_weighting="security share weights using prior month-end prices and shares",
            order_of_operations="If the largest component security exceeds 24%, scale the applicable large stocks toward 1% until it reaches 20%; if securities above 4.5% exceed 48% collectively, scale that cohort toward 1% until it reaches 40%.",
            reference_date_rule="Prior month-end inputs; the exact trader-time announcement date is not established by this row.",
            implementation_rule="Changes effective after the third Friday close for the quarterly process.",
            secondary_check_rule="Special rebalances may be called separately.",
            precision_notes="This establishes stock-level—not issuer-level—mechanics in dated snapshots; it does not establish an exact adoption interval.",
            evidence_grade="B",
            limitations="SEC-filed descriptions are contemporaneous but not provider adoption notices. The exact start date and event-specific vectors remain unresolved.",
            notes="Routine events through 2020Q1 are conservatively assigned to this screen; no issuer-level rule is backcast to 2018.",
        ),
        _rule(
            "NDX_RULE_LEVEL_TRANSITION_2020Q2",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="NDX_RULE_LEVEL_TRANSITION_UNRESOLVED_2020Q2",
            rule_scope="2020Q2 quarterly weighting transition",
            rule_level="unresolved stock/security versus issuer aggregate",
            source_id="SEC_GS_NDX_STOCK_METHOD_20200324",
            source_title="Goldman Sachs Underlier Supplement No. 5",
            source_type="contemporaneous SEC-filed methodology description",
            publisher="The Goldman Sachs Group, Inc. (SEC filer)",
            publication_date="2020-03-24",
            effective_start="2020-03-25",
            effective_end="2020-06-30",
            document_status="TRANSITION_BRACKETED_BY_SEC_FILINGS",
            status="RULE_LEVEL_UNRESOLVED",
            source_url=URLS["ndx_stock_2020q1"],
            archive_url=URLS["ndx_issuer_202007"],
            source_pages="stock-level at HTML lines 2179-2195; issuer-level by 2020-07-01 at lines 1694-1733",
            trigger_single_company_pct="24",
            target_single_company_pct="20",
            trigger_large_company_pct="4.5",
            trigger_aggregate_pct="48",
            target_aggregate_pct="40",
            input_weighting="unresolved for the 2020Q2 transition",
            order_of_operations="Do not choose security- or issuer-level aggregation without an exact Nasdaq adoption notice.",
            reference_date_rule="Prior month-end inputs documented; exact announcement date unresolved.",
            implementation_rule="2020Q2 implementation calendar is retained, but rule level is U.",
            secondary_check_rule="not established",
            precision_notes="The transition is bracketed after 2020-03-24 and no later than 2020-07-01.",
            evidence_grade="U",
            limitations="The exact adoption date was not recovered; 2020Q2 cannot be assigned confidently to either method.",
            notes="This is an explicit evidence gap, not an interpolation.",
        ),
        _rule(
            "NDX_ISSUER_LEVEL_2020Q3_20240623",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="NDX_ISSUER_LEVEL_2020Q3_20240623",
            rule_scope="March/June/September quarterly and special weighting",
            rule_level="issuer aggregate; initial security weights aggregated to issuer",
            source_id="SEC_GS_NDX_ISSUER_METHOD_20200701",
            source_title="Goldman Sachs Underlier Supplement No. 9",
            source_type="contemporaneous SEC-filed methodology description",
            publisher="The Goldman Sachs Group, Inc. (SEC filer)",
            publication_date="2020-07-01",
            effective_start="2020-07-01",
            effective_end="2024-06-23",
            document_status="SEC_FILED_DESCRIPTION_PLUS_PROVIDER_CHANGELOG_CORROBORATION",
            status="ISSUER_LEVEL_DOCUMENTED_BY_2020Q3",
            source_url=URLS["ndx_issuer_202007"],
            archive_url=URLS["ndx_change"],
            source_pages="HTML lines 1694-1733; Nasdaq change log labels this the immediately pre-2024 method",
            trigger_single_company_pct="24",
            target_single_company_pct="20",
            trigger_large_company_pct="4.5",
            trigger_aggregate_pct="48",
            target_aggregate_pct="40",
            input_weighting="TSO-derived/index-share-derived initial security weights, aggregated to issuer",
            order_of_operations="Stage 1 adjusts weights so no issuer exceeds 20% after a greater-than-24% breach. Stage 2 reduces the above-4.5% issuer cohort to 40% after a greater-than-48% breach; security index shares are then derived. December uses additional security-level constraints.",
            reference_date_rule="Prior month-end market data for routine quarters; July 2023 special uses 2023-07-03 separately documented.",
            implementation_rule="Routine effective next market open after the third-Friday implementation close; July 2023 special separately documented.",
            secondary_check_rule="A special rebalance may be called for concentration; it is one index event.",
            precision_notes="Rule level is documented by 2020-07-01; complete historical event inputs are not.",
            evidence_grade="B",
            limitations="The precise transition date before 2020-07-01 remains unresolved, so this regime begins conservatively with 2020Q3.",
            notes="Issuer aggregation is not backcast into the stock-level 2018-2020Q1 snapshots.",
        ),
        _rule(
            "NDX_WEIGHTING_20240624_20260430",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="NDX_COMPANY_LEVEL_20240624_20260430",
            rule_scope="March/June/September quarterly and special weighting",
            rule_level="company aggregate; security lines within company",
            source_id="NASDAQ_NDX_CHANGELOG_20260328",
            source_title="Nasdaq-100 Index Methodology Change Log",
            source_type="official retrospective change log",
            publication_date="2026-03-28",
            effective_start="2024-06-24",
            effective_end="2026-04-30",
            document_status="OFFICIAL_PDF_DOWNLOADED_AND_HASHED",
            status="CONFIRMED_HISTORICAL_RULE",
            source_url=URLS["ndx_change"],
            source_sha256="632594100092f802d14104b88ec5704e2b53f75c52b63e0fc305cc3753faec4e",
            source_pages="change effective 2024-06-24",
            trigger_single_company_pct="24",
            target_single_company_pct="20",
            trigger_large_company_pct="4.5",
            trigger_aggregate_pct="48",
            target_aggregate_pct="40",
            input_weighting="company initial weights from reference-date price and TSO/index-share inputs",
            order_of_operations="If any company exceeds 24%, cap it to 20%; if companies above 4.5% aggregate above 48%, reduce the cohort to 40%, with rank-preserving adjustments where required; repeat until constraints are met; derive security index shares.",
            reference_date_rule="Prior month-end market data for routine quarters.",
            implementation_rule="Effective next market open after third Friday of March, June, September, or December.",
            secondary_check_rule="Company-level concentration conditions govern special-rebalance eligibility.",
            precision_notes="Exact rule text, no historical vector.",
            evidence_grade="A",
            limitations="Retrospective change log does not expose event-specific full inputs.",
            notes="June 2024 is assigned to this company-level regime based on the stated 2024-06-24 effective date.",
        ),
        _rule(
            "NDX_WEIGHTING_FROM_20260501",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="NDX_CURRENT_FROM_20260501",
            rule_scope="current quarterly and special weighting",
            rule_level="company aggregate; security lines within company",
            source_id="NASDAQ_NDX_METHOD_20260430",
            source_title="Nasdaq-100 Index Methodology",
            source_type="official current methodology",
            publication_date="2026-04-30",
            effective_start="2026-05-01",
            effective_end="",
            document_status="OFFICIAL_PDF_DOWNLOADED_AND_HASHED",
            status="CONFIRMED_CURRENT_RULE_PARTIAL_EXTENSION_ONLY",
            source_url=URLS["ndx_method"],
            source_sha256="30949663d86e59f3a26422e1e18102edabae347ea315a3a01b9fbb2a0097a70d",
            source_pages="7-9",
            trigger_single_company_pct="24",
            target_single_company_pct="20",
            trigger_large_company_pct="4.5",
            trigger_aggregate_pct="48",
            target_aggregate_pct="40",
            input_weighting="current methodology's modified market-cap company weights and eligible TSO inputs",
            order_of_operations="Company Stage 1 cap to 20% after a greater-than-24% breach; Stage 2 reduce companies above 4.5% to a 40% aggregate after a 48% breach, preserve rank where required, and repeat.",
            reference_date_rule="Last trading day of February, May, August, and November.",
            implementation_rule="Announcement after close six trading days before effective date; effective first trading day after third Friday.",
            secondary_check_rule="Special rebalance may be triggered if company >24% or companies >4.5% aggregate >48%.",
            precision_notes="Current only; not backcast.",
            evidence_grade="A",
            limitations="2026 is a partial extension and excluded from a complete primary-year count.",
            notes="Current rules are kept separate from the July 2023 historical regime.",
        ),
        _rule(
            "NDX_SPECIAL_202307",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="NDX_ISSUER_LEVEL_2020Q3_20240623",
            rule_scope="July 2023 special rebalance schedule and event",
            rule_level="issuer",
            source_id="NASDAQ_NDX_SPECIAL_20230707",
            source_title="The Nasdaq-100 Index Special Rebalance to be Effective July 24, 2023",
            source_type="official contemporaneous schedule notice",
            publication_date="2023-07-07",
            effective_start="2023-07-03",
            effective_end="2023-07-24",
            document_status="OFFICIAL_PDF_DOWNLOADED_AND_HASHED",
            status="CONFIRMED_BINDING_EVENT_INCOMPLETE_DOSE",
            source_url=URLS["ndx_special"],
            archive_url=URLS["ndx_press"],
            source_sha256="3e5d3549fe019b660fd897ef45ebf1a7e858f8bb96fb4f891d632e102bb3a3c7",
            source_pages="1",
            trigger_single_company_pct="24",
            target_single_company_pct="20",
            trigger_large_company_pct="4.5",
            trigger_aggregate_pct="48",
            target_aggregate_pct="40",
            input_weighting="official reference pricing and TSO as of 2023-07-03",
            order_of_operations="No securities added or removed; largest company weights reduced and the remainder redistributed under the then-current issuer-level special-rebalance rule.",
            reference_date_rule="2023-07-03.",
            implementation_rule="Index shares announced/pro forma available 2023-07-14; effective before market open 2023-07-24.",
            secondary_check_rule="Ad hoc special rebalance; third in index history.",
            precision_notes="Schedule exact; public notice contains no full assignment vector.",
            evidence_grade="B",
            limitations="A notice that a pro forma file was released does not make its historical contents publicly accessible.",
            notes="All securities were expected to change weights, but this is one common index event.",
        ),
        _rule(
            "NDX_TTD_ATVI_REPLACEMENT_20230717",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="NDX_MEMBERSHIP_MAINTENANCE_20230717",
            rule_scope="constituent replacement inside special-rebalance anticipation window",
            rule_level="security membership",
            source_id="NASDAQ_IR_TTD_ATVI_20230712",
            source_title="The Trade Desk, Inc. to Join the Nasdaq-100 Index Beginning July 17th, 2023",
            source_type="official contemporaneous issuer press release",
            publication_date="2023-07-12",
            effective_start="2023-07-17",
            effective_end="2023-07-17",
            document_status="OFFICIAL_NASDAQ_IR_HTML_VERIFIED",
            status="CONFIRMED_INDEPENDENT_CONSTITUENT_REPLACEMENT",
            source_url=URLS["ndx_ttd_atvi"],
            source_pages="HTML announcement body",
            input_weighting="not disclosed",
            order_of_operations="The Trade Desk replaced Activision Blizzard before the 2023-07-17 market open.",
            reference_date_rule="not disclosed",
            implementation_rule="Announced 2023-07-12; effective before open 2023-07-17.",
            secondary_check_rule="Official notice says this replacement is independent of the 2023-07-24 special rebalance.",
            precision_notes="Membership and dates exact; weights are not supplied.",
            evidence_grade="B",
            limitations="No assignment weights or implementation quantities are published in the notice.",
            notes="Included as interference/context, not relabeled as a concentration-cap treatment.",
        ),
        _rule(
            "NDX_202307_POSTEVENT_SUMMARY",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="NDX_ISSUER_LEVEL_2020Q3_20240623",
            rule_scope="post-event direction and turnover summary",
            rule_level="issuer/event aggregate",
            source_id="NASDAQ_INDEX_RD_20231116",
            source_title="All About Index Concentration",
            source_type="official provider research article",
            publisher="Nasdaq, Inc.",
            publication_date="2023-11-16",
            effective_start="2023-07-24",
            effective_end="2023-07-24",
            document_status="OFFICIAL_HTML_VERIFIED",
            status="VERIFIED_APPROXIMATE_EVENT_SUMMARY",
            source_url=URLS["ndx_post"],
            source_pages="lines/section: How the Nasdaq-100 special rebalance in 2023 reduced concentration",
            input_weighting="market-cap weights shown graphically",
            order_of_operations="Largest six companies reduced proportionally; nearly all other securities increased.",
            reference_date_rule="Retrospective chart; no complete machine-readable reference vector.",
            implementation_rule="July 2023 special rebalance.",
            secondary_check_rule="not applicable",
            precision_notes="One-way turnover reported as approximately 12%; chart values are not transcribed as exact doses.",
            evidence_grade="B",
            limitations="Graphical/aggregate evidence only; no full exact weight vector.",
            notes="The approximate turnover is retained only on the ALL event row.",
        ),
        _rule(
            "NDX_HISTORICAL_PROFORMA_ACCESS_GAP",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            regime_id="HISTORICAL_ASSIGNMENT_ACCESS",
            rule_scope="historical pro forma/weights access",
            rule_level="file/access policy",
            source_id="NASDAQ_GIW_NDX_WEIGHTING",
            source_title="Nasdaq Global Index Watch — Weighting for NDX",
            source_type="official interactive index-data page",
            publisher="Nasdaq, Inc.",
            publication_date="",
            effective_start="",
            effective_end="",
            document_status="OFFICIAL_HTML_LOGIN_OR_ENTITLEMENT_REQUIRED_FOR_FULL_ACCESS",
            status="BLOCKED_PUBLIC_HISTORICAL_ASSIGNMENT",
            source_url=URLS["ndx_weighting"],
            source_pages="interactive page",
            input_weighting="not retrieved",
            order_of_operations="not applicable",
            reference_date_rule="Historical July 2023 contents not exposed in the public page state inspected.",
            implementation_rule="not applicable",
            secondary_check_rule="not applicable",
            precision_notes="No numbers inferred from the access page.",
            evidence_grade="U",
            limitations="Public page availability does not establish public historical-file availability; no bypass attempted.",
            notes="Minimum resolving input: official 2023-07-14 pro forma/index-share file or complete contemporaneous reference inputs.",
        ),
        _rule(
            "NDX_WEIGHT_OBJECT_DEFINITIONS_CURRENT",
            index_family="Nasdaq methodology supplement",
            index_name="Nasdaq index weight calculations",
            index_code="GENERAL",
            regime_id="CURRENT_ONLY_202605",
            rule_scope="definitions for initial/final weights and adjustment factors",
            rule_level="security, company, or group as specified by index",
            source_id="NASDAQ_WEIGHT_GUIDE_20260520",
            source_title="Nasdaq Index Weight Calculations",
            source_type="official current methodology supplement",
            publisher="Nasdaq, Inc.",
            publication_date="2026-05-20",
            effective_start="2026-05-20",
            effective_end="",
            document_status="OFFICIAL_PDF_DOWNLOADED_AND_HASHED",
            status="CURRENT_DEFINITION_ONLY",
            source_url=URLS["ndx_guide"],
            source_sha256="5bb083ed22669fa0b3c5fee4baf1e6f06830ed54ed7cce62ef7b123ad3532bfc",
            source_pages="1-7",
            input_weighting="index-specific initial weights",
            order_of_operations="Explains adjustment factors, constraint units, and initial versus final weights.",
            reference_date_rule="Index-specific.",
            implementation_rule="Index-specific.",
            secondary_check_rule="Index-specific.",
            precision_notes="Current supplement, not used to backcast July 2023.",
            evidence_grade="A",
            limitations="Generic current calculation guidance is not a historical assignment file.",
            notes="Supports unit labels and object separation only.",
        ),
    ]
    return rows


SECTORS = {
    "COMMS": ("Communication Services", "IXC"),
    "CONS_DISC": ("Consumer Discretionary", "IXY"),
    "CONS_STAP": ("Consumer Staples", "IXR"),
    "ENERGY": ("Energy", "IXE"),
    "FINANCIAL": ("Financials", "IXM"),
    "HEALTH": ("Health Care", "IXV"),
    "INDUSTRIAL": ("Industrials", "IXI"),
    "MATERIAL": ("Materials", "IXB"),
    "REAL_ESTATE": ("Real Estate", "IXRE"),
    "TECH": ("Information Technology", "IXT"),
    "UTILITIES": ("Utilities", "IXU"),
}

QUARTER_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}

# Full-day U.S. equity-market closures needed by the bounded 2018-2026 calendar.
# Early closes are not relevant to the date fields generated here.
MARKET_HOLIDAYS = {
    date.fromisoformat(value)
    for value in (
        "2018-01-01", "2018-01-15", "2018-02-19", "2018-03-30", "2018-05-28", "2018-07-04", "2018-09-03", "2018-11-22", "2018-12-05", "2018-12-25",
        "2019-01-01", "2019-01-21", "2019-02-18", "2019-04-19", "2019-05-27", "2019-07-04", "2019-09-02", "2019-11-28", "2019-12-25",
        "2020-01-01", "2020-01-20", "2020-02-17", "2020-04-10", "2020-05-25", "2020-07-03", "2020-09-07", "2020-11-26", "2020-12-25",
        "2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02", "2021-05-31", "2021-07-05", "2021-09-06", "2021-11-25", "2021-12-24",
        "2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20", "2022-07-04", "2022-09-05", "2022-11-24", "2022-12-26",
        "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29", "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
        "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
        "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    )
}


def is_market_day(day: date) -> bool:
    return day.weekday() < 5 and day not in MARKET_HOLIDAYS


def next_market_day(day: date) -> date:
    candidate = day + timedelta(days=1)
    while not is_market_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def previous_market_day(day: date) -> date:
    candidate = day - timedelta(days=1)
    while not is_market_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


def market_day_on_or_before(day: date) -> date:
    return day if is_market_day(day) else previous_market_day(day)


def move_market_days(day: date, offset: int) -> date:
    candidate = day
    step = 1 if offset >= 0 else -1
    remaining = abs(offset)
    while remaining:
        candidate += timedelta(days=step)
        if is_market_day(candidate):
            remaining -= 1
    return candidate


def nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    shift = (weekday - first.weekday()) % 7
    return first + timedelta(days=shift + 7 * (occurrence - 1))


def last_market_day(year: int, month: int) -> date:
    candidate = date(year, month, monthrange(year, month)[1])
    while not is_market_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


def sp_regular_dates(year: int, quarter: int) -> tuple[date, date, date]:
    month = QUARTER_MONTH[quarter]
    second_friday = market_day_on_or_before(nth_weekday(year, month, 4, 2))
    implementation_close = market_day_on_or_before(
        nth_weekday(year, month, 4, 3)
    )
    if (year, quarter) >= (2024, 4):
        reference = second_friday - timedelta(days=2)
    else:
        reference = second_friday
    return reference, implementation_close, next_market_day(implementation_close)


def sp_secondary_dates(year: int, quarter: int) -> tuple[date, date, date] | None:
    """Return (check input, potential implementation close, potential next open)."""
    month = QUARTER_MONTH[quarter]
    month_end = last_market_day(year, month)
    if (year, quarter) < (2019, 2):
        return None
    if date(year, month, 1) < date(2020, 8, 31):
        check = move_market_days(month_end, -2)  # third-to-last market day
        implementation = previous_market_day(month_end)
        effective = month_end
    else:
        check = previous_market_day(month_end)
        implementation = month_end
        effective = next_market_day(month_end)
    return check, implementation, effective


def ndx_regular_dates(
    year: int, quarter: int
) -> tuple[date, date | None, date, date]:
    month = QUARTER_MONTH[quarter]
    prior_month = month - 1
    reference = last_market_day(year, prior_month)
    implementation_close = market_day_on_or_before(
        nth_weekday(year, month, 4, 3)
    )
    effective_open = next_market_day(implementation_close)
    if effective_open >= date(2026, 5, 1):
        announcement = move_market_days(effective_open, -6)
    else:
        # No exact recurring pre-2026 announcement rule was established by the
        # inspected historical sources.  Missing event-specific dates stay blank.
        announcement = None
    return reference, announcement, implementation_close, effective_open


SECONDARY_CURRENT = {
    "TECH": [(22, 46), (22, 43), (24, 44), (25, 44), (21, 41), (21, 47), (22, 48), (23, 45), (24, 51), (25, 47), (24, 46), (22, 44), (24, 51), (23, 46), (23, 46), (22, 49), (24, 44), (23, 43)],
    "COMMS": [(23, 59), (22, 51), (23, 45), (22, 49), (23, 50), (24, 51), (23, 45), (23, 45), (23, 43), (24, 42), (23, 51), (23, 57), (23, 46), (24, 46), (24, 46), (24, 47), (25, 46), (23, 46)],
    "CONS_DISC": [(31, 55), (24, 49), (23, 49), (23, 47), (23, 45), (23, 50), (22, 47), (22, 41), (23, 53), (24, 55), (22, 44), (23, 49), (24, 49), (23, 42), (22, 42), (23, 50), (23, 46), (24, 48)],
    "CONS_STAP": [(17, 57), (16, 46), (18, 47), (17, 47), (16, 45), (16, 44), (16, 45), (17, 47), (16, 47), (15, 46), (15, 46), (16, 46), (14, 43), (14, 44), (15, 45), (14, 45), (15, 46), (15, 49)],
    "ENERGY": [(25, 56), (23, 46), (23, 46), (23, 46), (23, 50), (24, 44), (23, 53), (23, 49), (22, 44), (24, 45), (23, 43), (23, 43), (23, 43), (23, 47), (23, 42), (22, 49), (23, 49), (23, 41)],
    "MATERIAL": [(18, 48), (17, 48), (17, 48), (17, 50), (16, 46), (16, 46), (17, 41), (17, 43), (16, 42), (17, 41), (18, 42), (18, 39), (19, 39), (20, 45), (21, 46), (21, 46), (22, 47), (21, 52)],
    "REAL_ESTATE": [(15, 48), (16, 48), (15, 53), (13, 45), (13, 38), (13, 44), (13, 43), (12, 43), (12, 42), (13, 41), (12, 40), (12, 42), (13, 44), (12, 40), (12, 39), (12, 40), (12, 39), (11, 43)],
}

SECONDARY_QUARTERS = [(year, quarter) for year in range(2020, 2025) for quarter in range(1, 5) if (year, quarter) <= (2024, 2)]


def secondary_binding(sector_code: str, year: int, quarter: int) -> tuple[str, str, str]:
    """Conservatively classify S2's rounded current-rule secondary screens."""
    if sector_code == "COMMS" and (year, quarter) < (2018, 3):
        return "outside_applicable_regime", "U", "Communication Services is not backcast over the predecessor sector before the 2018-09-24 GICS reorganization."
    if not ((2020, 1) <= (year, quarter) <= (2024, 2)):
        return "uncertain", "U", "No event-specific public breach evidence recovered."
    if sector_code not in SECONDARY_CURRENT:
        return (
            "confirmed_nonbinding",
            "B",
            "S2 states that capping mechanisms were not triggered for sectors omitted from its historical-secondary appendix.",
        )
    index = SECONDARY_QUARTERS.index((year, quarter))
    maximum, aggregate = SECONDARY_CURRENT[sector_code][index]
    metrics = f"S2 displayed current-rule maximum={maximum}% and >4.8% cohort aggregate={aggregate}% (whole-point rounding)."
    if maximum >= 25 or aggregate >= 51:
        return "confirmed_binding", "B", metrics + " At least one displayed value clears the strict trigger despite rounding."
    if maximum <= 23 and aggregate <= 49:
        return "confirmed_nonbinding", "B", metrics + " Both displayed values remain safely below the strict triggers despite rounding."
    return "uncertain", "U", metrics + " A displayed 24% or 50% can straddle a strict threshold after rounding."


def regular_binding(sector_code: str, year: int, quarter: int) -> tuple[str, str, str]:
    if sector_code == "COMMS" and (year, quarter) < (2018, 3):
        return "outside_applicable_regime", "U", "Communication Services is not backcast over the predecessor sector before the 2018-09-24 GICS reorganization."
    if (year, quarter) not in {(2024, 1), (2024, 2)}:
        return "uncertain", "U", "Routine rebalance is scheduled, but public sources inspected do not establish whether the cap bound in this sector-quarter."
    capped = {"COMMS", "CONS_DISC", "CONS_STAP", "ENERGY", "TECH"}
    if sector_code in capped:
        return "confirmed_binding", "B", "S2's current-versus-FMC March/June 2024 tables show a nonzero capping effect for this sector."
    return "confirmed_nonbinding", "B", "S2 states capping did not trigger for omitted sectors and reports current weights equal to FMC for this sector."


def _event(event_id: str, **values: str) -> dict[str, str]:
    row = {name: "" for name in EVENT_HEADERS}
    classification_grade = values.pop("evidence_grade", "")
    binding_status = values.get("binding_status", "")
    assignment_grade = values.pop(
        "assignment_evidence_grade",
        "B"
        if binding_status in {"confirmed_binding", "confirmed_other_intervention"}
        else "U",
    )
    row.update(
        evidence_key=f"EVENT:{event_id}",
        event_id=event_id,
        retrieval_date=RETRIEVAL_DATE,
        grade_dimension="classification evidence and assignment observability are separate",
        classification_evidence_grade=classification_grade,
        assignment_evidence_grade=assignment_grade,
    )
    row.update(values)
    return row


def _scope(year: int) -> str:
    return "PRIMARY_2018_2025" if year <= 2025 else "PARTIAL_2026_EXTENSION"


def next_quarter(year: int, quarter: int) -> tuple[int, int]:
    return (year + 1, 1) if quarter == 4 else (year, quarter + 1)


def build_event_ledger() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    # Primary S&P calendar and separate potential secondary checks.
    for year in range(2018, 2027):
        last_quarter = 2 if year == 2026 else 4
        for quarter in range(1, last_quarter + 1):
            reference, close, effective = sp_regular_dates(year, quarter)
            next_year, next_q = next_quarter(year, quarter)
            next_regular_close = sp_regular_dates(next_year, next_q)[1]
            secondary_dates = sp_secondary_dates(year, quarter)
            if (year, quarter) < (2024, 3):
                regular_regime = "SP_SS_20180308_20240919"
                regular_rule_keys = "RULE:SP_SS_WEIGHTING_20180308_20240919"
            elif (year, quarter) == (2024, 3):
                regular_regime = "SP_SS_20240920_20241220"
                regular_rule_keys = "RULE:SP_SS_WEIGHTING_FROM_20240920"
            else:
                regular_regime = "SP_SS_FROM_20241221"
                regular_rule_keys = (
                    "RULE:SP_SS_WEIGHTING_FROM_20240920|"
                    "RULE:SP_SS_REFERENCE_DATE_FROM_20241221"
                )

            for sector_code, (sector_name, index_code) in SECTORS.items():
                event_id = f"SS_{sector_code}_{year}Q{quarter}_REGULAR"
                binding, grade, binding_note = regular_binding(sector_code, year, quarter)
                if (year, quarter) in {(2024, 1), (2024, 2)}:
                    source_id, source_url = "SPDJI_S2_20240808", URLS["sp_s2"]
                elif (year, quarter) == (2024, 3):
                    source_id, source_url = "SPDJI_S1_20240903", URLS["sp_s1"]
                elif (year, quarter) >= (2024, 4):
                    source_id, source_url = "SPDJI_REFDATE_20241202", URLS["sp_dec"]
                else:
                    source_id, source_url = "SPDJI_US_INDICES_METHOD_202607", URLS["sp_method"]
                group_id = f"SS_COMMON_{year}Q{quarter}_REGULAR_DATE"
                if (year, quarter) == (2024, 3):
                    group_id = "SS_2024Q3_COMMON_RULE_TRANSITION"
                potential_next = secondary_dates[1] if secondary_dates else next_regular_close
                rows.append(
                    _event(
                        event_id,
                        event_group_id=group_id,
                        index_family="S&P Select Sector",
                        index_name=f"{sector_name} Select Sector Index",
                        index_code=index_code,
                        sector=sector_name,
                        event_type="regular_quarterly_rebalance",
                        calendar_scope=_scope(year),
                        regime_id=regular_regime,
                        input_reference_date=reference.isoformat(),
                        implementation_close_date=close.isoformat(),
                        effective_open_date=effective.isoformat(),
                        next_intervention_date=potential_next.isoformat(),
                        binding_status=binding,
                        status="OUTSIDE_APPLICABLE_REGIME" if binding == "outside_applicable_regime" else "CONFIRMED_SCHEDULED_REBALANCE",
                        assignment_observability="not_applicable" if binding == "outside_applicable_regime" else ("rounded_selected_company_weights_only" if event_id in {"SS_TECH_2024Q1_REGULAR", "SS_TECH_2024Q2_REGULAR"} else "no_public_exact_assignment_vector_recovered"),
                        rule_evidence_keys=regular_rule_keys,
                        source_id=source_id,
                        source_url=source_url,
                        evidence_grade=grade,
                        limitations="The calendar date is confirmed by methodology; binding classification is separate. No exact full event vector is inferred.",
                        notes=binding_note + (" This sector event shares one common methodology transition with all sectors." if (year, quarter) == (2024, 3) else "") + " next_intervention_date is the next scheduled potential policy/check date, used conservatively for overlap screening.",
                    )
                )

                secondary_id = f"SS_{sector_code}_{year}Q{quarter}_SECONDARY_CHECK"
                if secondary_dates is None:
                    input_date = implementation = effective_secondary = ""
                    secondary_regime = "SP_SS_SECONDARY_TO_20190429"
                    if sector_code == "COMMS" and (year, quarter) < (2018, 3):
                        secondary_binding_status, secondary_grade, secondary_note = (
                            "outside_applicable_regime",
                            "U",
                            "Communication Services is not backcast over the predecessor sector before the 2018-09-24 GICS reorganization.",
                        )
                    else:
                        secondary_binding_status, secondary_grade, secondary_note = (
                            "uncertain",
                            "U",
                            "The accessible change history confirms a possible additional review but not a fixed event-specific check date.",
                        )
                    source_id_secondary = "SPDJI_US_INDICES_METHOD_202607"
                    source_url_secondary = URLS["sp_method"]
                else:
                    input_day, implementation_day, effective_day = secondary_dates
                    input_date = input_day.isoformat()
                    secondary_binding_status, secondary_grade, secondary_note = secondary_binding(sector_code, year, quarter)
                    # Only claim adjustment/effective dates when a breach is conservatively confirmed.
                    if secondary_binding_status == "confirmed_binding":
                        implementation = implementation_day.isoformat()
                        effective_secondary = effective_day.isoformat()
                    else:
                        implementation = effective_secondary = ""
                    if date(year, QUARTER_MONTH[quarter], 1) < date(2020, 8, 31):
                        secondary_regime = "SP_SS_SECONDARY_20190430_20200830"
                        source_id_secondary = "SPDJI_US_INDICES_METHOD_202607"
                        source_url_secondary = URLS["sp_method"]
                    elif (year, quarter) < (2024, 3):
                        secondary_regime = "SP_SS_SECONDARY_20200831_20240919"
                        source_id_secondary = "SPDJI_S2_20240808" if (year, quarter) >= (2020, 1) else "SPDJI_US_INDICES_METHOD_202607"
                        source_url_secondary = URLS["sp_s2"] if source_id_secondary == "SPDJI_S2_20240808" else URLS["sp_method"]
                    else:
                        secondary_regime = "SP_SS_SECONDARY_FROM_20240920"
                        source_id_secondary = "SPDJI_S1_20240903"
                        source_url_secondary = URLS["sp_s1"]
                rows.append(
                    _event(
                        secondary_id,
                        event_group_id=f"SS_COMMON_{year}Q{quarter}_SECONDARY_DATE",
                        index_family="S&P Select Sector",
                        index_name=f"{sector_name} Select Sector Index",
                        index_code=index_code,
                        sector=sector_name,
                        event_type="secondary_capping_check",
                        calendar_scope=_scope(year),
                        regime_id=secondary_regime,
                        input_reference_date=input_date,
                        implementation_close_date=implementation,
                        effective_open_date=effective_secondary,
                        secondary_adjustment_date=implementation,
                        next_intervention_date=next_regular_close.isoformat(),
                        binding_status=secondary_binding_status,
                        status="OUTSIDE_APPLICABLE_REGIME" if secondary_binding_status == "outside_applicable_regime" else ("CONFIRMED_BINDING_SECONDARY_REWEIGHT" if secondary_binding_status == "confirmed_binding" else ("CONFIRMED_NONBINDING_SCHEDULED_CHECK" if secondary_binding_status == "confirmed_nonbinding" else "SCHEDULED_CHECK_BINDING_UNCERTAIN")),
                        assignment_observability="event_level_only_no_exact_vector" if secondary_binding_status == "confirmed_binding" else "not_applicable_or_unknown",
                        rule_evidence_keys={
                            "SP_SS_SECONDARY_TO_20190429": "RULE:SP_SS_SECONDARY_TO_20190429",
                            "SP_SS_SECONDARY_20190430_20200830": "RULE:SP_SS_SECONDARY_20190430_20200830",
                            "SP_SS_SECONDARY_20200831_20240919": "RULE:SP_SS_SECONDARY_20200831_20240919",
                            "SP_SS_SECONDARY_FROM_20240920": "RULE:SP_SS_SECONDARY_FROM_20240920",
                        }[secondary_regime],
                        source_id=source_id_secondary,
                        source_url=source_url_secondary,
                        evidence_grade=secondary_grade,
                        limitations="Displayed S2 screens are rounded and labelled illustrative; boundary cases remain U. Blank implementation dates mean no adjustment was conservatively established.",
                        notes=secondary_note,
                    )
                )

    # The September transition is one policy event, in addition to the ordinary
    # per-index calendar rows required for downstream basket-date joins.
    rows.append(
        _event(
            "SS_ALL_2024Q3_RULE_TRANSITION",
            event_group_id="SS_2024Q3_COMMON_RULE_TRANSITION",
            index_family="S&P Select Sector",
            index_name="All 11 S&P 500 Select Sector Indices",
            index_code="SELECT_SECTOR_ALL",
            sector="ALL",
            event_type="methodology_change",
            calendar_scope="PRIMARY_2018_2025",
            regime_id="SP_SS_20240920_20241220",
            input_reference_date="2024-09-13",
            earliest_public_announcement_date="2024-09-03",
            pro_forma_available_date="2024-09-13",
            implementation_close_date="2024-09-20",
            effective_open_date="2024-09-23",
            next_intervention_date="2024-09-30",
            binding_status="confirmed_binding",
            status="CONFIRMED_COMMON_POLICY_CHANGE_INCOMPLETE_DOSE",
            assignment_observability="official_rule_and_dates_no_public_full_vector",
            rule_evidence_keys="RULE:SP_SS_WEIGHTING_FROM_20240920",
            source_id="SPDJI_S1_20240903",
            source_url=URLS["sp_s1"],
            evidence_grade="B",
            limitations="The common policy change is confirmed, but the full pre/post assignment vector and identical-input old/new replay are unavailable publicly.",
            notes="Count as one common transition, not one independent shock per sector or constituent. next_intervention_date is the scheduled secondary-check implementation date only if a breach occurred; breach was not established.",
        )
    )

    # Nasdaq routine quarterly calendar, kept separate from its July 2023 special.
    for year in range(2018, 2027):
        last_quarter = 2 if year == 2026 else 4
        for quarter in range(1, last_quarter + 1):
            reference, announcement, close, effective = ndx_regular_dates(year, quarter)
            next_year, next_q = next_quarter(year, quarter)
            next_close = ndx_regular_dates(next_year, next_q)[2]
            if (year, quarter) <= (2020, 1):
                regime = "NDX_SECURITY_LEVEL_SCREEN_2018_2020Q1"
                rule_keys = "RULE:NDX_SECURITY_LEVEL_2018_2020Q1_SNAPSHOT"
                event_source_id = "SEC_GS_NDX_STOCK_METHOD_20191122"
                event_source_url = URLS["ndx_stock_2019"]
            elif (year, quarter) == (2020, 2):
                regime = "NDX_RULE_LEVEL_TRANSITION_UNRESOLVED_2020Q2"
                rule_keys = "RULE:NDX_RULE_LEVEL_TRANSITION_2020Q2"
                event_source_id = "SEC_GS_NDX_STOCK_METHOD_20200324"
                event_source_url = URLS["ndx_stock_2020q1"]
            elif effective < date(2024, 6, 24):
                regime = "NDX_ISSUER_LEVEL_2020Q3_20240623"
                rule_keys = "RULE:NDX_ISSUER_LEVEL_2020Q3_20240623"
                event_source_id = "SEC_GS_NDX_ISSUER_METHOD_20200701"
                event_source_url = URLS["ndx_issuer_202007"]
            elif effective < date(2026, 5, 1):
                regime = "NDX_COMPANY_LEVEL_20240624_20260430"
                rule_keys = "RULE:NDX_WEIGHTING_20240624_20260430"
                event_source_id = "NASDAQ_NDX_CHANGELOG_20260328"
                event_source_url = URLS["ndx_change"]
            else:
                regime = "NDX_CURRENT_FROM_20260501"
                rule_keys = "RULE:NDX_WEIGHTING_FROM_20260501"
                event_source_id = "NASDAQ_NDX_METHOD_20260430"
                event_source_url = URLS["ndx_method"]
            if (year, quarter) == (2023, 2):
                next_intervention = date(2023, 7, 17)
            else:
                next_intervention = next_close
            rows.append(
                _event(
                    f"NDX_{year}Q{quarter}_REGULAR",
                    event_group_id=f"NDX_{year}Q{quarter}_REGULAR_DATE",
                    index_family="Nasdaq-100",
                    index_name="Nasdaq-100 Index",
                    index_code="NDX",
                    sector="multi-sector",
                    event_type="annual_reconstitution_and_rebalance" if quarter == 4 else "regular_quarterly_rebalance",
                    calendar_scope=_scope(year),
                    regime_id=regime,
                    input_reference_date=reference.isoformat(),
                    earliest_public_announcement_date=(
                        announcement.isoformat() if announcement else ""
                    ),
                    implementation_close_date=close.isoformat(),
                    effective_open_date=effective.isoformat(),
                    next_intervention_date=next_intervention.isoformat(),
                    binding_status="uncertain",
                    status="CONFIRMED_SCHEDULE_BINDING_UNRESOLVED",
                    assignment_observability="no_public_exact_historical_assignment_vector_recovered",
                    rule_evidence_keys=rule_keys,
                    source_id=event_source_id,
                    source_url=event_source_url,
                    evidence_grade="U",
                    limitations="Rule and recurring calendar are documented, but no event-specific public pro forma was recovered; scheduled quarter is not proof that concentration constraints bound.",
                    notes="Reference and implementation/effective dates are deterministic applications of the documented routine calendar. Pre-May-2026 exact announcement dates remain blank because no recurring exact rule was established; no dose is inferred.",
                )
            )

    rows.append(
        _event(
            "NDX_2023_07_17_TTD_ATVI_REPLACEMENT",
            event_group_id="NDX_2023_07_17_TTD_ATVI_REPLACEMENT_DATE",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            sector="multi-sector",
            event_type="constituent_replacement",
            calendar_scope="PRIMARY_2018_2025",
            regime_id="NDX_MEMBERSHIP_MAINTENANCE_20230717",
            earliest_public_announcement_date="2023-07-12",
            implementation_close_date="2023-07-14",
            effective_open_date="2023-07-17",
            next_intervention_date="2023-07-21",
            binding_status="confirmed_other_intervention",
            status="CONFIRMED_CONSTITUENT_REPLACEMENT_INTERFERENCE",
            assignment_observability="membership_change_only_weights_unobserved",
            interference_event_ids="NDX_2023_07_SPECIAL",
            rule_evidence_keys="RULE:NDX_TTD_ATVI_REPLACEMENT_20230717",
            source_id="NASDAQ_IR_TTD_ATVI_20230712",
            source_url=URLS["ndx_ttd_atvi"],
            evidence_grade="B",
            limitations="The official notice establishes membership and dates, not exact old/new index weights or quantities.",
            notes="Independent of the July 24 special rebalance but inside its anticipation/implementation window; retained as interference context, not a concentration-cap treatment.",
        )
    )

    rows.append(
        _event(
            "NDX_2023_07_SPECIAL",
            event_group_id="NDX_2023_07_SPECIAL_DATE",
            index_family="Nasdaq-100",
            index_name="Nasdaq-100 Index",
            index_code="NDX",
            sector="multi-sector",
            event_type="special_rebalance",
            calendar_scope="PRIMARY_2018_2025",
            regime_id="NDX_ISSUER_LEVEL_2020Q3_20240623",
            input_reference_date="2023-07-03",
            earliest_public_announcement_date="2023-07-07",
            pro_forma_available_date="2023-07-14",
            implementation_close_date="2023-07-21",
            effective_open_date="2023-07-24",
            next_intervention_date="2023-09-15",
            binding_status="confirmed_binding",
            status="CONFIRMED_SPECIAL_REBALANCE_INCOMPLETE_DOSE",
            assignment_observability="event_and_approximate_turnover_only",
            interference_event_ids="NDX_2023_07_17_TTD_ATVI_REPLACEMENT",
            rule_evidence_keys=(
                "RULE:NDX_ISSUER_LEVEL_2020Q3_20240623|"
                "RULE:NDX_SPECIAL_202307"
            ),
            source_id="NASDAQ_NDX_SPECIAL_20230707",
            source_url=URLS["ndx_special"],
            evidence_grade="B",
            limitations="The 2023-07-21 implementation close is the last market close before the official next-open effective time; the notice does not provide a full precise assignment vector.",
            notes="Official notice: reference pricing/TSO 2023-07-03, pro forma/index shares 2023-07-14, effective before 2023-07-24 open; the special itself caused no additions or deletions. The separate TTD-for-ATVI replacement effective 2023-07-17 is linked as interference. One special event, not many issuer interventions.",
        )
    )

    return sorted(rows, key=lambda row: (row["effective_open_date"] or row["input_reference_date"] or "9999", row["event_id"]))


MARCH_2024_TECH = [
    ("MSFT", "Microsoft Corp", 23.4, 23.4),
    ("AAPL", "Apple Inc.", 19.3, 19.3),
    ("NVDA", "Nvidia Corp", 16.8, 4.5),
    ("AVGO", "Broadcom Inc", 4.5, 4.5),
    ("AMD", "Advanced Micro Devices", 2.6, 3.5),
    ("CRM", "Salesforce, Inc.", 2.3, 3.1),
    ("ADBE", "Adobe Inc.", 1.9, 2.6),
    ("ACN", "Accenture plc Class A", 1.8, 2.5),
    ("CSCO", "Cisco Systems Inc", 1.6, 2.1),
    ("QCOM", "QUALCOMM Inc", 1.5, 2.0),
    ("INTC", "Intel Corp", 1.4, 1.9),
    ("INTU", "Intuit Inc", 1.4, 1.9),
    ("IBM", "International Business Machines Corp", 1.4, 1.9),
    ("ORCL", "Oracle Corp", 1.4, 1.9),
    ("AMAT", "Applied Materials Inc", 1.3, 1.8),
]

JUNE_2024_TECH = [
    ("MSFT", "Microsoft Corp", 21.9, 21.9),
    ("NVDA", "Nvidia Corp", 21.6, 21.6),
    ("AAPL", "Apple Inc.", 20.4, 4.5),
    ("AVGO", "Broadcom Inc", 5.0, 4.5),
    ("AMD", "Advanced Micro Devices", 1.7, 2.6),
    ("QCOM", "QUALCOMM Inc", 1.6, 2.4),
    ("ADBE", "Adobe Inc.", 1.6, 2.4),
    ("CRM", "Salesforce, Inc.", 1.5, 2.3),
    ("ORCL", "Oracle Corp", 1.5, 2.2),
    ("AMAT", "Applied Materials Inc", 1.3, 2.0),
    ("CSCO", "Cisco Systems Inc", 1.2, 1.9),
    ("ACN", "Accenture plc Class A", 1.2, 1.8),
    ("TXN", "Texas Instruments Inc", 1.2, 1.8),
    ("INTU", "Intuit Inc", 1.1, 1.7),
    ("MU", "Micron Technology Inc", 1.0, 1.6),
]


def _dose(event_id: str, security_or_all: str, **values: str) -> dict[str, str]:
    row = {name: "" for name in DOSE_HEADERS}
    row.update(
        evidence_key=f"DOSE:{event_id}:{security_or_all}",
        event_id=event_id,
        security_or_all=security_or_all,
        retrieval_date=RETRIEVAL_DATE,
        grade_dimension="assignment evidence",
    )
    row.update(values)
    return row


def _selected_tech_doses(event_id: str, observations: Iterable[tuple[str, str, float, float]], page: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ticker, company, uncapped, assigned in observations:
        rows.append(
            _dose(
                event_id,
                ticker,
                issuer_name=company,
                security_name=company,
                ticker=ticker,
                identifier="",
                assignment_level="company",
                uncapped_reference_weight_pct=f"{uncapped:.1f}",
                uncapped_reference_status="official_displayed_company_FMC_rounded_selected",
                rule_assigned_weight_pct=f"{assigned:.1f}",
                rule_assignment_status="official_displayed_current_rule_weight_rounded_selected",
                rebalance_change_weight_pct="",
                cap_distortion_pct=f"{assigned - uncapped:.1f}",
                etf_holding_weight_pct="",
                etf_holdings_status="not_observed_not_substituted",
                creation_basket_weight_pct="",
                creation_basket_status="not_observed_not_substituted",
                reported_one_way_turnover_pct="",
                numeric_precision_pct="0.1",
                vector_complete="false",
                dose_status="SELECTED_ROUNDED_SAME_TABLE_CAP_DISTORTION_ONLY",
                uncapped_source_id="SPDJI_S2_20240808",
                assignment_source_id="SPDJI_S2_20240808",
                etf_holdings_source_id="",
                creation_basket_source_id="",
                source_id="SPDJI_S2_20240808",
                source_url=URLS["sp_s2"],
                evidence_grade="B",
                status="DOCUMENTED_INCOMPLETE_DOSE",
                limitations="Only a rounded top-15 subset is published. The table is retrospective and labelled illustrative/hypothetical; it is not a complete precise pro forma vector.",
                notes=f"FMC and Current columns transcribed from S2 page {page} and compared within that same table/date. cap_distortion_pct=Current minus FMC. rebalance_change_weight_pct is blank because old/new portfolios at a verified common valuation state are unavailable. No ETF holding or creation-basket value is substituted.",
            )
        )
    rows.append(
        _dose(
            event_id,
            "ALL",
            assignment_level="event_vector",
            uncapped_reference_status="incomplete_top15_only",
            rule_assignment_status="incomplete_top15_only",
            etf_holdings_status="not_observed_not_substituted",
            creation_basket_status="not_observed_not_substituted",
            vector_complete="false",
            dose_status="FULL_VECTOR_NOT_PUBLICLY_RECOVERED",
            uncapped_source_id="SPDJI_S2_20240808",
            assignment_source_id="SPDJI_S2_20240808",
            source_id="SPDJI_S2_20240808",
            source_url=URLS["sp_s2"],
            evidence_grade="B",
            status="BLOCKED_EXACT_ASSIGNMENT_VECTOR",
            limitations="The selected top-15 rows do not sum to a complete index and are never renormalized. Exact index shares, all constituents, unrounded precision, and trader-time public availability remain unverified.",
            notes=f"S2 page {page}. Minimum resolving input: official historical pro forma/assignment file or complete contemporaneous prices, membership, shares, IWFs, and corporate-action adjustments with reconciliation.",
        )
    )
    return rows


def build_assignment_doses() -> list[dict[str, str]]:
    rows = _selected_tech_doses("SS_TECH_2024Q1_REGULAR", MARCH_2024_TECH, "10")
    rows.extend(_selected_tech_doses("SS_TECH_2024Q2_REGULAR", JUNE_2024_TECH, "11"))
    rows.append(
        _dose(
            "SS_ALL_2024Q3_RULE_TRANSITION",
            "ALL",
            assignment_level="common_policy_event",
            uncapped_reference_status="not_publicly_observed",
            rule_assignment_status="rule_known_assignment_vector_not_publicly_observed",
            etf_holdings_status="not_observed_not_substituted",
            creation_basket_status="not_observed_not_substituted",
            vector_complete="false",
            dose_status="RULE_CHANGE_CONFIRMED_FULL_VECTOR_BLOCKED",
            assignment_source_id="SPDJI_S1_20240903",
            source_id="SPDJI_S1_20240903",
            source_url=URLS["sp_s1"],
            evidence_grade="B",
            status="BLOCKED_EXACT_ASSIGNMENT_VECTOR",
            limitations="The official notice establishes the updated algorithm, announcement, pro forma start, implementation close, and effective open, but publishes no full old-rule or new-rule assignment vector.",
            notes="This is one common methodology change across all 11 sectors. No constituent-level row is manufactured, and no identical-input old-versus-new replay is claimed.",
        )
    )
    rows.append(
        _dose(
            "NDX_2023_07_SPECIAL",
            "ALL",
            assignment_level="event_aggregate",
            uncapped_reference_status="reference_date_confirmed_vector_not_publicly_recovered",
            rule_assignment_status="direction_documented_full_vector_not_publicly_recovered",
            etf_holdings_status="not_observed_not_substituted",
            creation_basket_status="not_observed_not_substituted",
            reported_one_way_turnover_pct="12",
            numeric_precision_pct="",
            vector_complete="false",
            dose_status="EVENT_CONFIRMED_APPROXIMATE_TURNOVER_ONLY",
            uncapped_source_id="NASDAQ_NDX_SPECIAL_20230707",
            assignment_source_id="NASDAQ_INDEX_RD_20231116",
            source_id="NASDAQ_INDEX_RD_20231116",
            source_url=URLS["ndx_post"],
            evidence_grade="B",
            status="BLOCKED_EXACT_ASSIGNMENT_VECTOR",
            limitations="Nasdaq reports approximately 12% one-way turnover and directional effects, not exact issuer/security weights. Historical 2023-07-14 pro forma contents were not available in the public GIW page inspected.",
            notes="Largest six company weights were reduced proportionally and nearly all other securities increased. The ~12% value is approximate event-level turnover, not a dose assigned to ALL and not an exact vector statistic.",
        )
    )
    return rows


def write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, str]]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Directory receiving the three Gate-1 CSV files.",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    counts = {
        "source_and_rule_registry.csv": write_csv(output_dir / "source_and_rule_registry.csv", SOURCE_HEADERS, build_source_registry()),
        "rebalance_event_ledger.csv": write_csv(output_dir / "rebalance_event_ledger.csv", EVENT_HEADERS, build_event_ledger()),
        "assignment_doses_and_evidence.csv": write_csv(output_dir / "assignment_doses_and_evidence.csv", DOSE_HEADERS, build_assignment_doses()),
    }
    for filename, count in counts.items():
        print(f"wrote {count:4d} rows  {output_dir / filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
