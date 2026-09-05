#!/usr/bin/env python3
"""Finalize R3 registries from completed, versioned aggregate evidence."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
R3 = Path(__file__).resolve().parent


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def finalize_specifications(production_complete: bool) -> None:
    path = R3 / "SPECIFICATION_REGISTRY.csv"
    fields, rows = read_rows(path)
    statuses = {
        "INV-01": "complete_with_source_version_limitation",
        "DATA-03": "complete_descriptive_with_public_design_limit",
        "CHAR-02": "complete_exploratory",
        "INF-01": "complete_reconciled",
        "DYN-01": "complete_with_pretrend_warning",
        "DYN-02": "complete_official_honestdid_nondetection",
        "DYN-03": "complete_exploratory",
        "DYN-04": "complete_with_retained_nonconvergence",
        "ARCH-01": "complete_exploratory",
        "ARCH-02": "complete_exploratory",
        "ARCH-03": "complete_archived_from_scientific_paper",
        "WRITE-01": "complete" if production_complete else "ready_for_production",
        "WRITE-02": "complete" if production_complete else "ready_for_production",
        "WRITE-03": "complete" if production_complete else "ready_for_production",
        "QA-01": "complete" if production_complete else "ready_for_production",
        "QA-02": "complete" if production_complete else "ready_for_production",
    }
    outputs = {
        "INF-01": "inference_rebuilt/results + NUMERICAL_CONSISTENCY_AUDIT.csv",
        "DYN-01": "dynamics/results/DYNAMIC_Q5_Q1_PROFILE.csv + PRETREND_TESTS.csv",
        "DYN-02": "dynamics/results/HONESTDID_*.csv",
        "DYN-03": "dynamics/results/SEASONALITY_SENSITIVITY.csv",
        "DYN-04": "dynamics/results/ONSET_DATE_SENSITIVITY.csv + ENDPOINT_SENSITIVITY.csv",
        "ARCH-01": "architecture/results/LAMBDA_GRID_*.csv",
        "ARCH-02": "architecture/results/PRIMITIVE_JOINT_*.csv",
        "ARCH-03": "architecture/results/ARCHIVED_REPARAMETERIZATION_AUDIT.*",
        "WRITE-01": "paper/main + paper/build/YAX_REVISED_MANUSCRIPT.pdf",
        "WRITE-02": "paper/appendix + paper/build/YAX_FOCUSED_ONLINE_APPENDIX.pdf",
        "WRITE-03": "paper/revision + paper/build/YAX_REFEREE_RESPONSE.pdf",
        "QA-01": "SUBSTANTIVE_REVISION_AUDIT.json + full pytest suite",
        "QA-02": "paper/build/SUBSTANTIVE_REVISION_PDF_SHA256.txt + rendered-page QA receipt",
    }
    for row in rows:
        if row["spec_id"] in statuses:
            row["status"] = statuses[row["spec_id"]]
        if row["spec_id"] in outputs:
            row["required_output"] = outputs[row["spec_id"]]
    write_rows(path, fields, rows)


def finalize_response_matrix() -> None:
    path = R3 / "responses" / "COMMENT_RESPONSE_MATRIX.csv"
    fields, rows = read_rows(path)
    locations = {
        "R1:M1": "Main Table 4; Appendix E",
        "R1:M2": "Sections 4 and 6; Main Table 4; Appendices E--F",
        "R1:M3": "Section 5; Appendix C",
        "R1:M4": "Section 5; Appendix C",
        "R1:M5": "Section 4; Appendix A",
        "R1:M6": "Sections 3 and 7; Appendices B and H",
        "R1:M7": "Sections 4--5; Appendix E",
        "R1:M8": "Section 7; Appendix H",
        "R1:M9": "Section 6; Appendix F",
        "R1:M10": "Section 7; Appendix H",
        "R1:M11": "Section 7; Main Table 5; Appendix G",
        "R1:M12": "Section 8; Appendix H",
        "R1:S1": "Removed from scientific manuscript; evidence ledger only",
        "R1:S2": "Section 4",
        "R1:S3": "Section 4; Appendix A",
        "R1:S4": "Sections 3--4; Appendices A--B",
        "R1:S5": "Section 3; Appendix B",
        "R1:S6": "Section 3; Appendix D",
        "R1:S7": "Section 7; Appendix H",
        "R1:S8": "Section 5, Figure 1",
        "R1:S9": "All main tables and appendices",
        "R1:S10": "Section 4; Appendix A",
        "R1:S11": "Section 3; Appendix B",
        "R1:S12": "All delivered sources and PDFs",
        "R1:S13": "Title page; author placeholders retained",
        "R1:S14": "Section 4; Appendix I",
        "R2:M1": "Sections 3--4; Appendices A--B",
        "R2:M2": "Sections 5 and 7; Appendices C and H",
        "R2:M3": "Sections 3 and 7; Appendices D and H",
        "R2:M4": "Section 5; Appendix C",
        "R2:M5": "Sections 3--5; Appendices A--B",
        "R2:M6": "Section 4; Main Table 4; Appendix E",
        "R2:M7": "Section 7; Appendix H",
        "R2:M8": "Section 7; Appendix G; historical method archived",
        "R2:M9": "Section 4; Appendix I",
        "R2:C1": "Section 6; Appendix F",
        "R2:C2": "Section 7, Table 6; Appendix H",
        "R2:C3": "Section 4; Appendix A",
        "R2:C4": "Section 7; Appendix D",
        "R2:C5": "Main Tables 1--6",
        "R2:C6": "Section 7, Table 5; Appendix G",
    }
    evidence_updates = {
        "R1:M1": "inference_rebuilt/results; survey_sim/results; dynamics/results/STATIC_STRUCTURE_PAIRING.csv",
        "R1:M2": "inference_rebuilt/results; survey_sim/results; dynamics/results",
        "R1:M3": "dynamics/rebuilt_family_harmonization/results",
        "R1:M7": "rebuilt_baseline/results; dynamics/results; inference_rebuilt/results; NUMERICAL_CONSISTENCY_AUDIT.csv",
        "R1:M10": "architecture/results; historical replication archive",
        "R1:M11": "flows/results; flows/results_household",
        "R2:M2": "architecture/results; inference_rebuilt/results",
        "R2:M4": "dynamics/rebuilt_family_harmonization/results; dynamics/results",
        "R2:M6": "inference_rebuilt/results; survey_sim/results",
        "R2:C1": "dynamics/results",
        "R2:C2": "architecture/results/LAMBDA_GRID_RESULTS.csv; architecture/results/CONSTRUCTION_IDENTITY_AUDIT.json",
        "R2:C6": "flows/results; flows/results_household",
    }
    status_updates = {
        "R1:M5": "completed_with_unavailable_counterfactual",
        "R1:M8": "completed_approximation",
        "R1:M9": "completed_scoped_nonadoption",
        "R1:S4": "completed_with_limit",
        "R1:S13": "blocked_author_input",
        "R2:M8": "completed_scoped_nonadoption",
    }
    for row in rows:
        key = f"{row['report']}:{row['comment_id']}"
        row["manuscript_location"] = locations[key]
        row["status"] = status_updates.get(key, "completed")
        if key in evidence_updates:
            row["evidence_location"] = evidence_updates[key]
    write_rows(path, fields, rows)


def append_failures() -> None:
    path = R3 / "FAILURE_REGISTRY.csv"
    fields, rows = read_rows(path)
    additions = [
        ["DYN-ENDPOINT-ABORT", "2026-09-05", "dynamic_endpoint", "SCC job 7468697", "The initial authoritative dynamics job stopped at the first nonconvergent post-2020 grouped-binomial endpoint model", "dynamics/failed_7468697", "Partial results are not used", "Retain the failed row and continue all other predeclared grid rows without substituting a new estimator"],
        ["DYN-HONEST-GLPK", "2026-09-05", "HonestDiD_install", "SCC job 7468699", "Rglpk could not locate the SCC GLPK headers and library", "dynamics/EXECUTION_HISTORY.md", "No sensitivity result was produced", "Load and verify glpk/5.0 in a clean project library"],
        ["DYN-HONEST-BOOL", "2026-09-05", "HonestDiD_handoff", "SCC job 7469127", "R read Python Boolean event flags as character values", "dynamics/honestdid_execution.log", "No sensitivity result was produced", "Validate and convert the six admitted Boolean serializations"],
        ["DYN-HONEST-CVXR", "2026-09-05", "HonestDiD_dependency", "SCC job 7469157", "Installed CVXR did not export status as required by HonestDiD 0.2.8", "dynamics/honestdid_execution.log", "No sensitivity result was produced", "Pin official CVXR 1.8.2 and verify its namespace"],
        ["DYN-HONEST-RUST", "2026-09-05", "HonestDiD_dependency", "SCC job 7469187", "CVXR dependency clarabel could not compile without Rust", "dynamics/EXECUTION_HISTORY.md", "No sensitivity result was produced", "Load SCC rust/1.84.0 in a fresh project library"],
        ["DYN-HONEST-HIGHS", "2026-09-05", "HonestDiD_dependency", "SCC job 7469208", "CVXR 1.8.2 requires highs at least 1.12 but SCC resolved 1.10.0-3", "dynamics/EXECUTION_HISTORY.md", "No sensitivity result was produced", "Install and verify official highs 1.12.0-3"],
        ["DYN-HONEST-OSQP", "2026-09-05", "HonestDiD_dependency", "SCC job 7469229", "CVXR 1.8.2 requires osqp at least 1.0 but SCC resolved 0.6.3.3", "dynamics/EXECUTION_HISTORY.md", "No sensitivity result was produced", "Install and verify official osqp 1.0.0"],
        ["INF-REBUILT-ROOT", "2026-09-05", "inference_execution", "SCC job 7469348", "The first wrapper retained an obsolete hard-coded repository root", "inference_rebuilt/scc_execution.log", "The process failed before reading data", "Use YAX_REPO_ROOT and rerun from an isolated clean worktree"],
        ["FAM-REBUILT-OUTPUT", "2026-09-05", "family_execution", "SCC job 7469964", "The scheduler could not open the declared output log because its parent directory was absent", "dynamics/rebuilt_family_harmonization/scc_execution.log", "The job never started and no data were read", "Create the project output directory and submit a fresh unchanged job"],
    ]
    existing = {row["spec_id"] for row in rows}
    for values in additions:
        if values[0] not in existing:
            rows.append(dict(zip(fields, values)))
    write_rows(path, fields, rows)


def append_results() -> None:
    path = R3 / "RESULTS_LEDGER.csv"
    fields, rows = read_rows(path)
    additions = [
        ["FAM-01-REBUILT", "complete", "2026-09-05", "7a07ab2", "dynamics/rebuilt_family_harmonization/results/EXECUTION_RECEIPT.json", "dynamics/rebuilt_family_harmonization/results/PROFILE_COEFFICIENTS.csv", "-0.021675", "0.071323", "-0.159538", "0.116188", "0.199816", "468 occupations; 22 SOC2 families; rebuilt treatment; 113 months", "Family-month conditioning moves the pooled Q5 coefficient by 0.110434 on common draws", "Profile-conditioned vector is jointly consistent with zero; paired Q5 interval [0.008463,0.212406]"],
        ["FAM-02-REBUILT", "complete_nondetection_changed_population", "2026-09-05", "7a07ab2", "dynamics/rebuilt_family_harmonization/results/EXECUTION_RECEIPT.json", "dynamics/rebuilt_family_harmonization/results/DIRECT_TAIL_MODELS.csv", "0.149364", "0.163331", "-0.169434", "0.468161", "0.457586", "29 occupations in four families; 5.03% of full-support preperiod stock", "Direct within-family tail comparison is highly imprecise", "Changed population; rebuilt treatment contract"],
        ["FAM-03-REBUILT", "complete_nondetection", "2026-09-05", "7a07ab2", "dynamics/rebuilt_family_harmonization/results/EXECUTION_RECEIPT.json", "dynamics/rebuilt_family_harmonization/results/CONTINUOUS_WITHIN_FAMILY_MODELS.csv", "-0.002465", "0.011184", "-0.023989", "0.019059", "0.031332", "468 occupations; one within-family SD is 0.108385 raw beta units", "Common within-family slope is not detected", "SOC2-by-calendar-month; rebuilt treatment contract"],
        ["INF-02-REBUILT-PAIR", "complete", "2026-09-05", "08b4edc", "inference_rebuilt/results/EXECUTION_RECEIPT.json", "inference_rebuilt/results/SOC2_WILD_SENSITIVITY.csv", "0.110434", "0.054828", "0.005876", "0.214993", "0.153604", "22 SOC2 clusters; 99,999 Webb six-point draws", "Paired conditioning movement remains detected under broad-family shocks", "Distinct shock interpretation from occupation clustering"],
        ["DYN-01-POOL", "complete_with_pretrend_warning", "2026-09-05", "7a07ab2", "dynamics/results/EXECUTION_RECEIPT.json", "dynamics/results/STATIC_DYNAMIC_MAPPING.csv", "-0.119889", "0.073348", "-0.261836", "0.022058", "0.202699", "38 Q5 event coefficients; 23 pre and 15 post", "Calendar-weighted dynamic functional is not detected and unrestricted pretrend test rejects", "Companion linear functional; not nonlinear static coefficient"],
        ["DYN-01-SOC2", "complete_with_pretrend_warning", "2026-09-05", "7a07ab2", "dynamics/results/EXECUTION_RECEIPT.json", "dynamics/results/STATIC_DYNAMIC_MAPPING.csv", "-0.207434", "0.111088", "-0.421567", "0.006700", "0.290967", "38 Q5 event coefficients; SOC2-specific monthly paths", "Family-conditioned dynamic functional is not detected and unrestricted pretrend test rejects", "Companion linear functional"],
        ["DYN-02-HONEST-POOL", "complete_nondetection", "2026-09-05", "7a07ab2", "dynamics/results/HONESTDID_EXECUTION_RECEIPT.csv", "dynamics/results/HONESTDID_ORIGINAL_rebuilt_corrected_preperiod_weight_unconditioned.csv", "-0.119889", "", "-0.263649", "0.023871", "", "Official HonestDiD 0.2.8; rebuilt pooled event vector", "Conventional companion interval already includes zero", "No positive zero-exclusion breakdown is defined"],
        ["DYN-02-HONEST-SOC2", "complete_nondetection", "2026-09-05", "7a07ab2", "dynamics/results/HONESTDID_EXECUTION_RECEIPT.csv", "dynamics/results/HONESTDID_ORIGINAL_rebuilt_corrected_preperiod_weight_SOC2_x_calendar_month.csv", "-0.207434", "", "-0.425163", "0.010295", "", "Official HonestDiD 0.2.8; rebuilt family-conditioned event vector", "Conventional companion interval already includes zero", "No positive zero-exclusion breakdown is defined"],
        ["ARCH-01-LAMBDA", "complete_exploratory", "2026-09-05", "fc3d34c", "architecture/results/EXECUTION_RECEIPT.json", "architecture/results/LAMBDA_GRID_RESULTS.csv", "-0.132109", "0.045174", "-0.219789", "-0.044429", "0.126559", "468 occupations; lambda=.5 exact beta construction", "Point estimates vary with architecture but every lambda-versus-beta paired interval includes zero", "Tail membership changes are reported separately"],
        ["ARCH-02-D", "complete_exploratory", "2026-09-05", "fc3d34c", "architecture/results/EXECUTION_RECEIPT.json", "architecture/results/PRIMITIVE_ILLUSTRATIVE_CONTRASTS.csv", "-0.030923", "0.013896", "-0.057982", "-0.003865", "0.038930", "468 occupations; one weighted SD of D holding S fixed", "Illustrative primitive association; not adoption decomposition", "Joint D/S model"],
        ["ARCH-02-S", "complete_exploratory", "2026-09-05", "fc3d34c", "architecture/results/EXECUTION_RECEIPT.json", "architecture/results/PRIMITIVE_ILLUSTRATIVE_CONTRASTS.csv", "-0.027927", "0.013604", "-0.054185", "-0.001669", "0.038113", "468 occupations; one weighted SD of S holding D fixed", "Illustrative primitive association; not adoption decomposition", "Joint D/S model"],
        ["CHAR-01-COMP-408", "complete_exploratory", "2026-09-05", "fc3d34c", "architecture/results/EXECUTION_RECEIPT.json", "architecture/results/CHARACTERISTIC_CONDITIONING_RESULTS.csv", "-0.212433", "0.061390", "-0.330977", "-0.093889", "0.171990", "408-occupation literal common support with finite beta Webb computer-use and remotability", "Adding the preperiod computer-use characteristic makes the beta coefficient more negative", "Paired movement from beta-plus-Webb is -0.105392 [-0.183452,-0.027332]; descriptive suppressor pattern"],
    ]
    for row in rows:
        if row["spec_id"] == "INV-01":
            row["status"] = "complete_with_source_version_limitation"
            row["output_path"] = "baseline_inventory; revision_inputs/REVISION_INPUTS_MANIFEST.csv"
            row["interpretation"] = "All located analysis inputs and supplied referee texts are hashed and inventoried"
            row["notes"] = "A separately numbered source report cited by the integrated prompt was not supplied and is not claimed as read"
    existing = {row["spec_id"] for row in rows}
    for values in additions:
        if values[0] not in existing:
            rows.append(dict(zip(fields, values)))
    write_rows(path, fields, rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-complete", action="store_true")
    args = parser.parse_args()
    finalize_specifications(args.production_complete)
    finalize_response_matrix()
    append_failures()
    append_results()
    print("PASS: R3 registries finalized" + (" for production" if args.production_complete else " for pre-production"))


if __name__ == "__main__":
    main()
