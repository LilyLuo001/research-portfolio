#!/usr/bin/env Rscript

# Add dependency metadata omitted from a completed HonestDiD receipt.
# This script does not refit a model or alter any statistical result file.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("usage: augment_honestdid_receipt.R OUTPUT_DIR")
}

output_dir <- normalizePath(args[[1]], mustWork = TRUE)
receipt_path <- file.path(output_dir, "HONESTDID_EXECUTION_RECEIPT.csv")
if (!file.exists(receipt_path)) {
  stop("HonestDiD execution receipt is missing")
}

if (!requireNamespace("osqp", quietly = TRUE)) {
  stop("osqp is unavailable")
}
osqp_description <- utils::packageDescription("osqp")
if (is.null(osqp_description$Version) || osqp_description$Version != "1.0.0") {
  stop("osqp does not match the verified compatible CRAN 1.0.0 release")
}

receipt <- read.csv(receipt_path, stringsAsFactors = FALSE, check.names = FALSE)
if ("osqp_version" %in% names(receipt) &&
    any(receipt$osqp_version != osqp_description$Version)) {
  stop("existing osqp version metadata conflicts with the execution environment")
}
if ("osqp_source" %in% names(receipt) &&
    any(receipt$osqp_source != "CRAN release 1.0.0")) {
  stop("existing osqp source metadata conflicts with the verified source")
}

receipt$osqp_version <- osqp_description$Version
receipt$osqp_source <- "CRAN release 1.0.0"

preferred <- c(
  "analysis_status", "treatment_contract", "structure", "package",
  "package_version", "official_source_commit", "installed_remote_sha",
  "cvxr_version", "cvxr_official_source_commit", "cvxr_installed_remote_sha",
  "cvxr_status_export_verified", "highs_version", "highs_source",
  "osqp_version", "osqp_source"
)
remaining <- setdiff(names(receipt), preferred)
receipt <- receipt[, c(preferred, remaining), drop = FALSE]
write.csv(receipt, receipt_path, row.names = FALSE, na = "")
cat("PASS_HONESTDID_OSQP_RECEIPT_AUGMENTATION\n")
