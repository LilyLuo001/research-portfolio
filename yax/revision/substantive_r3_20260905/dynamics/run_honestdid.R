#!/usr/bin/env Rscript

# Official Rambachan--Roth sensitivity analysis for validated R3 event vectors.
# This script never approximates or reimplements HonestDiD. It fails if the
# official package is unavailable, preserving non-adoption as an explicit fact.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("usage: run_honestdid.R OUTPUT_DIR")
}
output_dir <- normalizePath(args[[1]], mustWork = TRUE)
if (!requireNamespace("HonestDiD", quietly = TRUE)) {
  stop("official HonestDiD package is unavailable; no sensitivity result produced")
}
PINNED_HONESTDID_SHA <- "6813f02ed38f0b63bdca6915604b2eac90491303"
PINNED_CVXR_SHA <- "2fe1dac4d0c903c4a29515bef19c5d3824d09656"
PINNED_HIGHS_VERSION <- "1.12.0-3"
PINNED_OSQP_VERSION <- "1.0.0"
honestdid_description <- utils::packageDescription("HonestDiD")
installed_remote_sha <- honestdid_description$RemoteSha
if (is.null(installed_remote_sha) || installed_remote_sha != PINNED_HONESTDID_SHA) {
  stop("HonestDiD does not match the pinned official source commit")
}
if (!requireNamespace("CVXR", quietly = TRUE)) {
  stop("CVXR is unavailable")
}
cvxr_description <- utils::packageDescription("CVXR")
installed_cvxr_sha <- cvxr_description$RemoteSha
if (as.character(utils::packageVersion("CVXR")) != "1.8.2" ||
    is.null(installed_cvxr_sha) || installed_cvxr_sha != PINNED_CVXR_SHA ||
    !"status" %in% getNamespaceExports("CVXR")) {
  stop("CVXR does not match pinned compatible 1.8.2 source and API")
}
if (!requireNamespace("highs", quietly = TRUE)) {
  stop("highs is unavailable")
}
highs_description <- utils::packageDescription("highs")
if (is.null(highs_description$Version) ||
    highs_description$Version != PINNED_HIGHS_VERSION) {
  stop("highs does not match pinned compatible 1.12.0-3 CRAN release")
}
if (!requireNamespace("osqp", quietly = TRUE)) {
  stop("osqp is unavailable")
}
osqp_description <- utils::packageDescription("osqp")
if (is.null(osqp_description$Version) ||
    osqp_description$Version != PINNED_OSQP_VERSION) {
  stop("osqp does not match pinned compatible 1.0.0 CRAN release")
}

sha256_file <- function(path) {
  output <- system2("sha256sum", path, stdout = TRUE, stderr = TRUE)
  status <- attr(output, "status")
  if (length(output) != 1 || (!is.null(status) && status != 0)) {
    stop(paste("sha256sum failed for", path))
  }
  strsplit(output[[1]], "[[:space:]]+")[[1]][[1]]
}

parse_boolean_column <- function(values, column_name, suffix) {
  normalized <- tolower(trimws(as.character(values)))
  if (any(!normalized %in% c("true", "false", "t", "f", "1", "0"))) {
    stop(paste("invalid Boolean serialization in", column_name, "for", suffix))
  }
  normalized %in% c("true", "t", "1")
}

app_path <- file.path(output_dir, "RAMBACHAN_ROTH_APPLICABILITY.csv")
app <- read.csv(app_path, stringsAsFactors = FALSE, check.names = FALSE)
ready <- app[app$execution_status == "READY_FOR_OFFICIAL_HONESTDID", , drop = FALSE]
if (nrow(ready) == 0) {
  stop("no validated event vector is ready for official HonestDiD")
}

smooth_grid <- c(0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05)
relative_grid <- c(0, 0.5, 1, 1.5, 2)
receipt_rows <- list()

for (row_index in seq_len(nrow(ready))) {
  treatment <- ready$treatment_contract[[row_index]]
  structure <- ready$structure[[row_index]]
  suffix <- paste(treatment, structure, sep = "_")
  vector_path <- file.path(output_dir, paste0("HONESTDID_EVENT_VECTOR_", suffix, ".csv"))
  covariance_path <- file.path(output_dir, paste0("HONESTDID_COVARIANCE_", suffix, ".csv"))
  vector <- read.csv(vector_path, stringsAsFactors = FALSE, check.names = FALSE)
  covariance_long <- read.csv(covariance_path, stringsAsFactors = FALSE, check.names = FALSE)
  vector$is_pre <- parse_boolean_column(vector$is_pre, "is_pre", suffix)
  vector$is_post <- parse_boolean_column(vector$is_post, "is_post", suffix)
  event_bins <- vector$event_bin
  sigma <- matrix(NA_real_, nrow = length(event_bins), ncol = length(event_bins),
                  dimnames = list(event_bins, event_bins))
  for (index in seq_len(nrow(covariance_long))) {
    sigma[covariance_long$row_event_bin[[index]],
          covariance_long$column_event_bin[[index]]] <- covariance_long$covariance[[index]]
  }
  if (any(!is.finite(sigma)) || max(abs(sigma - t(sigma))) > 1e-10) {
    stop(paste("invalid covariance for", suffix))
  }
  pre <- which(vector$is_pre)
  post <- which(vector$is_post)
  if (length(pre) == 0 || length(post) == 0 || max(pre) >= min(post)) {
    stop(paste("pre/post event ordering invalid for", suffix))
  }
  l_vec <- vector$l_vec_post_functional_weight[post]
  if (abs(sum(l_vec) - 1) > 1e-12 || any(l_vec < 0)) {
    stop(paste("post functional invalid for", suffix))
  }
  beta <- vector$coefficient_q5_vs_q1
  common <- list(
    betahat = beta,
    sigma = sigma,
    numPrePeriods = length(pre),
    numPostPeriods = length(post),
    l_vec = l_vec,
    alpha = 0.05
  )
  original <- do.call(HonestDiD::constructOriginalCS, common)
  smooth <- do.call(
    HonestDiD::createSensitivityResults,
    c(common, list(Mvec = smooth_grid, seed = 2026090529))
  )
  relative <- do.call(
    HonestDiD::createSensitivityResults_relativeMagnitudes,
    c(common, list(Mbarvec = relative_grid, seed = 2026090529))
  )
  original_frame <- as.data.frame(original)
  smooth_frame <- as.data.frame(smooth)
  relative_frame <- as.data.frame(relative)
  original_frame$treatment_contract <- treatment
  original_frame$structure <- structure
  smooth_frame$treatment_contract <- treatment
  smooth_frame$structure <- structure
  smooth_frame$event_time_unit <- "quarter"
  relative_frame$treatment_contract <- treatment
  relative_frame$structure <- structure
  relative_frame$event_time_unit <- "quarter"
  original_path <- file.path(output_dir, paste0("HONESTDID_ORIGINAL_", suffix, ".csv"))
  smooth_path <- file.path(output_dir, paste0("HONESTDID_SMOOTHNESS_", suffix, ".csv"))
  relative_path <- file.path(output_dir, paste0("HONESTDID_RELATIVE_MAGNITUDE_", suffix, ".csv"))
  write.csv(original_frame, original_path, row.names = FALSE, na = "")
  write.csv(smooth_frame, smooth_path, row.names = FALSE, na = "")
  write.csv(relative_frame, relative_path, row.names = FALSE, na = "")
  conventional_includes_zero <- any(
    original_frame$lb <= 0 & original_frame$ub >= 0,
    na.rm = TRUE
  )
  smooth_includes <- smooth_frame$lb <= 0 & smooth_frame$ub >= 0
  relative_includes <- relative_frame$lb <= 0 & relative_frame$ub >= 0
  first_smooth_grid_including_zero <- if (any(smooth_includes)) {
    min(smooth_frame$M[smooth_includes])
  } else {
    NA_real_
  }
  relative_parameter <- if ("Mbar" %in% names(relative_frame)) "Mbar" else "M"
  first_relative_grid_including_zero <- if (any(relative_includes)) {
    min(relative_frame[[relative_parameter]][relative_includes])
  } else {
    NA_real_
  }
  receipt_rows[[length(receipt_rows) + 1]] <- data.frame(
    analysis_status = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1",
    treatment_contract = treatment,
    structure = structure,
    package = "HonestDiD",
    package_version = as.character(utils::packageVersion("HonestDiD")),
    official_source_commit = PINNED_HONESTDID_SHA,
    installed_remote_sha = installed_remote_sha,
    cvxr_version = as.character(utils::packageVersion("CVXR")),
    cvxr_official_source_commit = PINNED_CVXR_SHA,
    cvxr_installed_remote_sha = installed_cvxr_sha,
    cvxr_status_export_verified = "status" %in% getNamespaceExports("CVXR"),
    highs_version = highs_description$Version,
    highs_source = "CRAN archive release 1.12.0-3",
    osqp_version = osqp_description$Version,
    osqp_source = "CRAN release 1.0.0",
    event_coefficients = length(beta),
    pre_coefficients = length(pre),
    post_coefficients = length(post),
    reference_bin = "2022Q4",
    l_vec_sum = sum(l_vec),
    smoothness_grid_log_points_per_quarter = paste(smooth_grid, collapse = "|"),
    relative_magnitude_grid = paste(relative_grid, collapse = "|"),
    conventional_interval_includes_zero = conventional_includes_zero,
    positive_zero_exclusion_breakdown_defined = !conventional_includes_zero,
    first_declared_smoothness_grid_point_including_zero = first_smooth_grid_including_zero,
    first_declared_relative_grid_point_including_zero = first_relative_grid_including_zero,
    grid_breakdown_note = "coarse declared-grid crossing, not an interpolated exact threshold",
    event_vector_sha256 = sha256_file(vector_path),
    event_covariance_sha256 = sha256_file(covariance_path),
    original_result_sha256 = sha256_file(original_path),
    smoothness_result_sha256 = sha256_file(smooth_path),
    relative_magnitude_result_sha256 = sha256_file(relative_path),
    interpretation = "companion dynamic functional; not the nonlinear grouped static coefficient",
    stringsAsFactors = FALSE
  )
}

receipt <- do.call(rbind, receipt_rows)
write.csv(receipt, file.path(output_dir, "HONESTDID_EXECUTION_RECEIPT.csv"),
          row.names = FALSE, na = "")
