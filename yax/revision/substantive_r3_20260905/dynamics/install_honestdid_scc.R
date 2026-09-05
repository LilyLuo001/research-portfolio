#!/usr/bin/env Rscript

# Install the official HonestDiD implementation into project storage at the
# source revision recorded before the corrected R3 dynamic estimates are run.

library_path <- Sys.getenv("R_LIBS_USER", unset = "")
if (library_path == "") {
  stop("R_LIBS_USER must name a project-storage library")
}
dir.create(library_path, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(library_path, .libPaths()))
if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes", repos = "https://cloud.r-project.org", lib = library_path)
}
local_version <- function(package) {
  description_path <- file.path(library_path, package, "DESCRIPTION")
  if (!file.exists(description_path)) {
    return("")
  }
  as.character(read.dcf(description_path, fields = "Version")[[1]])
}
PINNED_HIGHS_VERSION <- "1.12.0-3"
if (local_version("highs") != PINNED_HIGHS_VERSION) {
  remotes::install_version(
    "highs", version = PINNED_HIGHS_VERSION,
    repos = "https://cloud.r-project.org", lib = library_path,
    dependencies = NA, upgrade = "never"
  )
}
if ("highs" %in% loadedNamespaces()) {
  unloadNamespace("highs")
}
highs_description <- utils::packageDescription("highs", lib.loc = library_path)
if (is.null(highs_description$Version) || highs_description$Version !=
    PINNED_HIGHS_VERSION) {
  stop("highs does not match pinned compatible CRAN version")
}
PINNED_OSQP_VERSION <- "1.0.0"
if (local_version("osqp") != PINNED_OSQP_VERSION) {
  remotes::install_version(
    "osqp", version = PINNED_OSQP_VERSION,
    repos = "https://cloud.r-project.org", lib = library_path,
    dependencies = NA, upgrade = "never"
  )
}
if ("osqp" %in% loadedNamespaces()) {
  unloadNamespace("osqp")
}
osqp_description <- utils::packageDescription("osqp", lib.loc = library_path)
if (is.null(osqp_description$Version) || osqp_description$Version !=
    PINNED_OSQP_VERSION) {
  stop("osqp does not match pinned compatible CRAN version")
}
PINNED_CVXR_SHA <- "2fe1dac4d0c903c4a29515bef19c5d3824d09656"
remotes::install_github(
  paste0("cvxgrp/CVXR@", PINNED_CVXR_SHA),
  lib = library_path,
  dependencies = NA,
  upgrade = "never"
)
if (!requireNamespace("CVXR", quietly = TRUE)) {
  stop("CVXR installation did not produce a loadable package")
}
cvxr_description <- utils::packageDescription("CVXR")
if (as.character(utils::packageVersion("CVXR")) != "1.8.2" ||
    is.null(cvxr_description$RemoteSha) ||
    cvxr_description$RemoteSha != PINNED_CVXR_SHA ||
    !"status" %in% getNamespaceExports("CVXR")) {
  stop("CVXR does not match pinned 1.8.2 source with exported status API")
}
remotes::install_github(
  "asheshrambachan/HonestDiD@6813f02ed38f0b63bdca6915604b2eac90491303",
  lib = library_path,
  dependencies = NA,
  upgrade = "never"
)
if (!requireNamespace("HonestDiD", quietly = TRUE)) {
  stop("HonestDiD installation did not produce a loadable package")
}
cat("CVXR", as.character(utils::packageVersion("CVXR")), cvxr_description$RemoteSha, "\n")
cat("highs", highs_description$Version, "\n")
cat("osqp", osqp_description$Version, "\n")
cat("HonestDiD", as.character(utils::packageVersion("HonestDiD")), "\n")
