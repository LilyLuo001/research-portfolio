#!/usr/bin/env Rscript

# Run only the official pinned HonestDiD implementation on prepared public
# current-contract inputs. Constraint matrices are cross-checked against the
# package's own constructors before any interval is retained.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("usage: run_honestdid_current.R OUTPUT_DIR")
}
output_dir <- normalizePath(args[[1]], mustWork = TRUE)

PINNED_HONESTDID_SHA <- "6813f02ed38f0b63bdca6915604b2eac90491303"
PINNED_CVXR_SHA <- "2fe1dac4d0c903c4a29515bef19c5d3824d09656"
PINNED_HIGHS_VERSION <- "1.12.0-3"
PINNED_OSQP_VERSION <- "1.0.0"
SMOOTH_GRID <- c(0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05)
RELATIVE_GRID <- c(0, 0.5, 1, 1.5, 2)
SEED <- 2026090529
ALPHA <- 0.05
GRID_POINTS <- 1000

required_packages <- c("HonestDiD", "CVXR", "highs", "osqp", "jsonlite")
for (package in required_packages) {
  if (!requireNamespace(package, quietly = TRUE)) {
    stop(paste("required package unavailable:", package))
  }
}
honestdid_description <- utils::packageDescription("HonestDiD")
cvxr_description <- utils::packageDescription("CVXR")
highs_description <- utils::packageDescription("highs")
osqp_description <- utils::packageDescription("osqp")
if (as.character(utils::packageVersion("HonestDiD")) != "0.2.8" ||
    is.null(honestdid_description$RemoteSha) ||
    honestdid_description$RemoteSha != PINNED_HONESTDID_SHA) {
  stop("HonestDiD does not match the pinned official 0.2.8 source commit")
}
if (as.character(utils::packageVersion("CVXR")) != "1.8.2" ||
    is.null(cvxr_description$RemoteSha) ||
    cvxr_description$RemoteSha != PINNED_CVXR_SHA ||
    !"status" %in% getNamespaceExports("CVXR")) {
  stop("CVXR does not match the pinned compatible 1.8.2 source and API")
}
if (is.null(highs_description$Version) ||
    highs_description$Version != PINNED_HIGHS_VERSION) {
  stop("highs does not match pinned compatible 1.12.0-3 release")
}
if (is.null(osqp_description$Version) ||
    osqp_description$Version != PINNED_OSQP_VERSION) {
  stop("osqp does not match pinned compatible 1.0.0 release")
}

sha256_file <- function(path) {
  output <- system2("sha256sum", path, stdout = TRUE, stderr = TRUE)
  status <- attr(output, "status")
  if (length(output) != 1 || (!is.null(status) && status != 0)) {
    stop(paste("sha256sum failed for", path))
  }
  strsplit(output[[1]], "[[:space:]]+")[[1]][[1]]
}

required_inputs <- c(
  "ANALYSIS_MANIFEST.csv", "EVENT_VECTORS.csv", "EVENT_COVARIANCES.csv",
  "CONVENTIONAL_FUNCTIONALS.csv", "SENSITIVITY_GRID.csv",
  "CONSTRAINT_MATRIX_CATALOG.csv", "SMOOTHNESS_CONSTRAINT_MATRIX.csv",
  "RELATIVE_CONSTRAINT_MATRICES.csv"
)
preparation_path <- file.path(output_dir, "PREPARATION_RECEIPT.json")
preparation <- jsonlite::fromJSON(preparation_path, simplifyVector = FALSE)
if (preparation$status != "PASS_CURRENT_CONTRACT_HONESTDID_INPUT_PREPARATION") {
  stop("preparation receipt is not passing")
}
for (filename in required_inputs) {
  path <- file.path(output_dir, filename)
  if (!file.exists(path) || sha256_file(path) != preparation$output_hashes[[filename]]) {
    stop(paste("prepared input authentication failed for", filename))
  }
}

manifest <- read.csv(file.path(output_dir, "ANALYSIS_MANIFEST.csv"),
                     stringsAsFactors = FALSE, check.names = FALSE)
vectors <- read.csv(file.path(output_dir, "EVENT_VECTORS.csv"),
                    stringsAsFactors = FALSE, check.names = FALSE)
covariances <- read.csv(file.path(output_dir, "EVENT_COVARIANCES.csv"),
                        stringsAsFactors = FALSE, check.names = FALSE)
catalog <- read.csv(file.path(output_dir, "CONSTRAINT_MATRIX_CATALOG.csv"),
                    stringsAsFactors = FALSE, check.names = FALSE)
smooth_sparse <- read.csv(file.path(output_dir, "SMOOTHNESS_CONSTRAINT_MATRIX.csv"),
                          stringsAsFactors = FALSE, check.names = FALSE)
relative_sparse <- read.csv(file.path(output_dir, "RELATIVE_CONSTRAINT_MATRICES.csv"),
                            stringsAsFactors = FALSE, check.names = FALSE)

if (nrow(manifest) != 4 || length(unique(manifest$analysis_id)) != 4) {
  stop("analysis inventory differs")
}

matrix_from_sparse <- function(frame, matrix_id, rows, columns) {
  selected <- frame[frame$matrix_id == matrix_id, , drop = FALSE]
  if (nrow(selected) == 0) stop(paste("empty sparse matrix", matrix_id))
  if (any(selected$matrix_row < 1 | selected$matrix_row > rows) ||
      any(selected$coefficient_index < 1 | selected$coefficient_index > columns)) {
    stop(paste("sparse matrix index outside dimensions", matrix_id))
  }
  if (any(duplicated(selected[, c("matrix_row", "coefficient_index")]))) {
    stop(paste("duplicate sparse matrix cell", matrix_id))
  }
  matrix <- base::matrix(0, nrow = rows, ncol = columns)
  matrix[cbind(selected$matrix_row, selected$coefficient_index)] <- selected$value
  matrix
}

capture_official <- function(expression) {
  warnings <- character()
  started <- proc.time()[[3]]
  value <- withCallingHandlers(
    expression,
    warning = function(condition) {
      warnings <<- c(warnings, conditionMessage(condition))
      invokeRestart("muffleWarning")
    }
  )
  list(value = value, elapsed_seconds = proc.time()[[3]] - started,
       warnings = warnings)
}

original_rows <- list()
smooth_rows <- list()
relative_rows <- list()
execution_rows <- list()
matrix_rows <- list()
create_A_SD <- getFromNamespace(".create_A_SD", "HonestDiD")
create_A_RM <- getFromNamespace(".create_A_RM", "HonestDiD")

for (index in seq_len(nrow(manifest))) {
  info <- manifest[index, , drop = FALSE]
  analysis_id <- info$analysis_id[[1]]
  num_pre <- as.integer(info$pre_periods[[1]])
  num_post <- as.integer(info$post_periods[[1]])
  vector <- vectors[vectors$analysis_id == analysis_id, , drop = FALSE]
  vector <- vector[order(vector$coefficient_index), , drop = FALSE]
  if (nrow(vector) != num_pre + num_post ||
      !identical(vector$coefficient_index, seq_len(nrow(vector)))) {
    stop(paste("event vector order differs for", analysis_id))
  }
  if (!all(vector$role[seq_len(num_pre)] == "pre") ||
      !all(vector$role[num_pre + seq_len(num_post)] == "post")) {
    stop(paste("pre/post roles differ for", analysis_id))
  }
  covariance_long <- covariances[covariances$analysis_id == analysis_id, , drop = FALSE]
  sigma <- base::matrix(NA_real_, nrow = nrow(vector), ncol = nrow(vector))
  sigma[cbind(covariance_long$row_index, covariance_long$column_index)] <-
    covariance_long$covariance
  if (any(!is.finite(sigma)) || max(abs(sigma - t(sigma))) > 1e-12) {
    stop(paste("event covariance invalid for", analysis_id))
  }
  l_vec <- vector$l_vec_post_functional_weight[num_pre + seq_len(num_post)]
  if (any(l_vec < 0) || abs(sum(l_vec) - 1) > 1e-12 ||
      any(vector$l_vec_post_functional_weight[seq_len(num_pre)] != 0)) {
    stop(paste("post-only l_vec invalid for", analysis_id))
  }

  smooth_catalog <- catalog[catalog$analysis_id == analysis_id &
                            catalog$restriction_family == "DeltaSD", , drop = FALSE]
  if (nrow(smooth_catalog) != 1) stop("smoothness matrix catalog differs")
  prepared_smooth <- matrix_from_sparse(
    smooth_sparse, smooth_catalog$matrix_id[[1]],
    as.integer(smooth_catalog$rows[[1]]), as.integer(smooth_catalog$columns[[1]]))
  official_smooth <- create_A_SD(numPrePeriods = num_pre,
                                 numPostPeriods = num_post,
                                 postPeriodMomentsOnly = FALSE)
  smooth_difference <- max(abs(prepared_smooth - official_smooth))
  if (!identical(dim(prepared_smooth), dim(official_smooth)) ||
      smooth_difference > 1e-12) {
    stop(paste("prepared smoothness matrix differs from official package for", analysis_id))
  }
  matrix_rows[[length(matrix_rows) + 1]] <- data.frame(
    analysis_id = analysis_id, restriction_family = "DeltaSD",
    compared_matrices = 1L, maximum_absolute_difference = smooth_difference,
    status = "PASS_OFFICIAL_MATRIX_PARITY", stringsAsFactors = FALSE)

  relative_catalog <- catalog[catalog$analysis_id == analysis_id &
                              catalog$restriction_family == "DeltaRM", , drop = FALSE]
  expected_relative <- length(RELATIVE_GRID) * num_pre * 2
  if (nrow(relative_catalog) != expected_relative) {
    stop(paste("relative matrix catalog differs for", analysis_id))
  }
  relative_max_difference <- 0
  for (matrix_index in seq_len(nrow(relative_catalog))) {
    matrix_info <- relative_catalog[matrix_index, , drop = FALSE]
    prepared_relative <- matrix_from_sparse(
      relative_sparse, matrix_info$matrix_id[[1]],
      as.integer(matrix_info$rows[[1]]), as.integer(matrix_info$columns[[1]]))
    max_positive <- tolower(as.character(matrix_info$max_positive[[1]])) == "true"
    official_relative <- create_A_RM(
      numPrePeriods = num_pre, numPostPeriods = num_post,
      Mbar = as.numeric(matrix_info$Mbar[[1]]), s = as.integer(matrix_info$s[[1]]),
      max_positive = max_positive, dropZero = TRUE)
    if (!identical(dim(prepared_relative), dim(official_relative))) {
      stop(paste("relative matrix dimensions differ for", matrix_info$matrix_id[[1]]))
    }
    difference <- max(abs(prepared_relative - official_relative))
    relative_max_difference <- max(relative_max_difference, difference)
    if (difference > 1e-12) {
      stop(paste("prepared relative matrix differs from official package for",
                 matrix_info$matrix_id[[1]]))
    }
  }
  matrix_rows[[length(matrix_rows) + 1]] <- data.frame(
    analysis_id = analysis_id, restriction_family = "DeltaRM",
    compared_matrices = expected_relative,
    maximum_absolute_difference = relative_max_difference,
    status = "PASS_OFFICIAL_MATRIX_PARITY", stringsAsFactors = FALSE)

  common <- list(
    betahat = vector$estimate, sigma = sigma,
    numPrePeriods = num_pre, numPostPeriods = num_post,
    l_vec = l_vec, alpha = ALPHA
  )
  original <- capture_official(do.call(HonestDiD::constructOriginalCS, common))
  smooth <- capture_official(do.call(
    HonestDiD::createSensitivityResults,
    c(common, list(method = "FLCI", Mvec = SMOOTH_GRID,
                   parallel = FALSE, seed = SEED))))
  relative <- capture_official(do.call(
    HonestDiD::createSensitivityResults_relativeMagnitudes,
    c(common, list(bound = "deviation from parallel trends", method = "C-LF",
                   Mbarvec = RELATIVE_GRID, gridPoints = GRID_POINTS,
                   parallel = FALSE, seed = SEED))))

  outputs <- list(original = original, smoothness = smooth, relative = relative)
  for (name in names(outputs)) {
    result <- as.data.frame(outputs[[name]]$value)
    if (nrow(result) == 0 || !all(c("lb", "ub") %in% names(result)) ||
        any(!is.finite(result$lb)) || any(!is.finite(result$ub)) ||
        any(result$lb > result$ub)) {
      stop(paste("official result invalid for", analysis_id, name))
    }
    execution_rows[[length(execution_rows) + 1]] <- data.frame(
      analysis_id = analysis_id, official_function = name,
      returned_rows = nrow(result), finite_interval_rows = sum(is.finite(result$lb) & is.finite(result$ub)),
      elapsed_seconds = outputs[[name]]$elapsed_seconds,
      warning_count = length(outputs[[name]]$warnings),
      warning_text = paste(outputs[[name]]$warnings, collapse = " | "),
      call_status = "RETURNED_FINITE_OFFICIAL_RESULT",
      underlying_optimizer_status_available = FALSE,
      stringsAsFactors = FALSE)
    result$analysis_id <- analysis_id
    result$structure <- info$structure[[1]]
    result$calibration_window <- info$calibration_window[[1]]
    result$target <- "dynamic_P_equal_observed_post_month"
    if (name == "original") original_rows[[length(original_rows) + 1]] <- result
    if (name == "smoothness") smooth_rows[[length(smooth_rows) + 1]] <- result
    if (name == "relative") relative_rows[[length(relative_rows) + 1]] <- result
  }
}

original_path <- file.path(output_dir, "OFFICIAL_ORIGINAL_RESULTS.csv")
smooth_path <- file.path(output_dir, "OFFICIAL_SMOOTHNESS_RESULTS.csv")
relative_path <- file.path(output_dir, "OFFICIAL_RELATIVE_MAGNITUDE_RESULTS.csv")
execution_path <- file.path(output_dir, "OFFICIAL_EXECUTION_LOG.csv")
matrix_path <- file.path(output_dir, "OFFICIAL_MATRIX_PARITY.csv")
write.csv(do.call(rbind, original_rows), original_path, row.names = FALSE, na = "")
write.csv(do.call(rbind, smooth_rows), smooth_path, row.names = FALSE, na = "")
write.csv(do.call(rbind, relative_rows), relative_path, row.names = FALSE, na = "")
write.csv(do.call(rbind, execution_rows), execution_path, row.names = FALSE, na = "")
write.csv(do.call(rbind, matrix_rows), matrix_path, row.names = FALSE, na = "")

output_files <- c(
  "OFFICIAL_ORIGINAL_RESULTS.csv", "OFFICIAL_SMOOTHNESS_RESULTS.csv",
  "OFFICIAL_RELATIVE_MAGNITUDE_RESULTS.csv", "OFFICIAL_EXECUTION_LOG.csv",
  "OFFICIAL_MATRIX_PARITY.csv"
)
receipt <- list(
  schema_version = "yax-gate4-honestdid-official-execution-receipt-v1",
  status = "PASS_OFFICIAL_CURRENT_CONTRACT_HONESTDID_EXECUTION",
  created_utc = format(Sys.time(), tz = "UTC", usetz = TRUE),
  analysis_count = nrow(manifest),
  official_package = list(
    name = "HonestDiD", version = as.character(utils::packageVersion("HonestDiD")),
    source_commit = PINNED_HONESTDID_SHA,
    installed_remote_sha = honestdid_description$RemoteSha
  ),
  dependencies = list(
    CVXR = list(version = as.character(utils::packageVersion("CVXR")),
                source_commit = PINNED_CVXR_SHA,
                installed_remote_sha = cvxr_description$RemoteSha,
                status_export_verified = "status" %in% getNamespaceExports("CVXR")),
    highs = list(version = highs_description$Version),
    osqp = list(version = osqp_description$Version)
  ),
  parameters = list(alpha = ALPHA, seed = SEED,
                    smoothness_grid = SMOOTH_GRID,
                    relative_magnitude_grid = RELATIVE_GRID,
                    relative_test_inversion_grid_points = GRID_POINTS),
  matrix_parity = list(tolerance = 1e-12,
                       all_pass = all(do.call(rbind, matrix_rows)$status ==
                                      "PASS_OFFICIAL_MATRIX_PARITY")),
  optimizer_disclosure = paste(
    "The official high-level functions returned finite intervals. Their returned",
    "objects do not expose every underlying optimizer status; no unobserved status",
    "is represented as independently verified."),
  prepared_input_hashes = preparation$output_hashes,
  output_hashes = stats::setNames(
    lapply(file.path(output_dir, output_files), sha256_file), output_files)
)
jsonlite::write_json(receipt, file.path(output_dir, "OFFICIAL_EXECUTION_RECEIPT.json"),
                     pretty = TRUE, auto_unbox = TRUE, digits = NA)

