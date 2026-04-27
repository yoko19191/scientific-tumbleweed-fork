#!/usr/bin/env bash
set -euo pipefail

# Install CRAN and Bioconductor packages. Run 1_install_base_environment.sh first
# so Ubuntu 22.04 arm64 native build dependencies are already present.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
. "${SCRIPT_DIR}/_common.sh"

require_root_prefix

CRAN_MIRROR="${CRAN_MIRROR:-${R_CRAN_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/CRAN}}"
BIOC_MIRROR="${BIOC_MIRROR:-${R_BIOC_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/bioconductor}}"
R_NCPUS="${R_NCPUS:-$(nproc 2>/dev/null || echo 2)}"
R_INSTALL_FAST="${R_INSTALL_FAST:-1}"
INSTALL_R_ARROW="${INSTALL_R_ARROW:-0}"
INSTALL_SEURAT="${INSTALL_SEURAT:-1}"
CLEAN_R_LOCKS="${CLEAN_R_LOCKS:-1}"

log_section "Check R runtime"
if ! command -v Rscript >/dev/null 2>&1; then
  log_error "Rscript is not available. Run 1_install_base_environment.sh first."
  exit 1
fi
log_info "Using R: $(R --version | sed -n '1p')"

log_section "Install CRAN and Bioconductor packages"
log_info "Using CRAN mirror: $CRAN_MIRROR"
log_info "Using Bioconductor mirror: $BIOC_MIRROR"
"${ROOT_PREFIX[@]}" env \
  CRAN_MIRROR="$CRAN_MIRROR" \
  BIOC_MIRROR="$BIOC_MIRROR" \
  R_NCPUS="$R_NCPUS" \
  R_INSTALL_FAST="$R_INSTALL_FAST" \
  INSTALL_R_ARROW="$INSTALL_R_ARROW" \
  INSTALL_SEURAT="$INSTALL_SEURAT" \
  CLEAN_R_LOCKS="$CLEAN_R_LOCKS" \
  BIOC_VERSION="${BIOC_VERSION:-}" \
  NO_COLOR="${NO_COLOR:-}" \
  Rscript --vanilla - <<'RS'
cran <- Sys.getenv("CRAN_MIRROR", "https://mirrors.tuna.tsinghua.edu.cn/CRAN")
bioc <- Sys.getenv("BIOC_MIRROR", "https://mirrors.tuna.tsinghua.edu.cn/bioconductor")
ncpus <- as.integer(Sys.getenv("R_NCPUS", "2"))
fast_install <- identical(Sys.getenv("R_INSTALL_FAST", "1"), "1")
install_arrow <- identical(Sys.getenv("INSTALL_R_ARROW", "0"), "1")
install_seurat <- identical(Sys.getenv("INSTALL_SEURAT", "1"), "1")
clean_r_locks <- identical(Sys.getenv("CLEAN_R_LOCKS", "1"), "1")
install_opts <- if (fast_install) {
  c("--no-html", "--no-multiarch", "--no-test-load")
} else {
  character()
}
options(repos = c(CRAN = cran), BioC_mirror = bioc, Ncpus = ncpus, timeout = 600)

use_color <- nzchar(Sys.getenv("TERM")) && !nzchar(Sys.getenv("NO_COLOR"))
blue <- if (use_color) "\033[1;34m" else ""
green <- if (use_color) "\033[1;32m" else ""
yellow <- if (use_color) "\033[1;33m" else ""
reset <- if (use_color) "\033[0m" else ""

log_section <- function(title) {
  message("\n", blue, "============================================================", reset)
  message(blue, ">> ", title, reset)
  message(blue, "============================================================", reset)
}

log_info <- function(text) {
  message(blue, "[INFO]", reset, " ", text)
}

log_warn <- function(text) {
  message(yellow, "[WARN]", reset, " ", text)
}

log_done <- function(text) {
  message(green, "[DONE]", reset, " ", text)
}

if (clean_r_locks) {
  lock_dirs <- unlist(lapply(.libPaths(), function(path) {
    if (dir.exists(path)) {
      list.files(path, pattern = "^00LOCK", full.names = TRUE)
    } else {
      character()
    }
  }))
  if (length(lock_dirs)) {
    log_section("Clean stale R package locks")
    log_info(paste("Removing:", paste(lock_dirs, collapse = ", ")))
    unlink(lock_dirs, recursive = TRUE, force = TRUE)
  }
}

install_with_progress <- function(pkgs, installer, label) {
  total <- length(pkgs)
  if (!total) {
    log_info(paste("No", label, "packages need installation."))
    return(invisible(NULL))
  }

  for (idx in seq_along(pkgs)) {
    pkg <- pkgs[[idx]]
    log_section(sprintf("%s package %d/%d: %s", label, idx, total, pkg))
    started_at <- Sys.time()
    installer(pkg)
    elapsed <- round(as.numeric(difftime(Sys.time(), started_at, units = "mins")), 1)
    log_done(sprintf("%s installed in %s min", pkg, elapsed))
  }
}

install_missing_cran <- function(pkgs) {
  missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing)) {
    log_info(paste("Missing CRAN packages:", paste(missing, collapse = ", ")))
    install_with_progress(
      missing,
      function(pkg) {
        install.packages(pkg, repos = cran, Ncpus = ncpus, INSTALL_opts = install_opts)
      },
      "CRAN"
    )
  } else {
    log_info("All requested CRAN packages are already installed.")
  }
}

cran_packages <- c(
  "BiocManager",
  "tidyverse",
  "data.table",
  "dtplyr",
  "readxl",
  "writexl",
  "openxlsx",
  "duckdb",
  "DBI",
  "RSQLite",
  "janitor",
  "skimr",
  "broom",
  "ggplot2",
  "ggpubr",
  "ggrepel",
  "patchwork",
  "cowplot",
  "plotly",
  "htmlwidgets",
  "DT",
  "pheatmap",
  "VennDiagram",
  "UpSetR",
  "igraph",
  "vegan",
  "survival",
  "survminer",
  "lme4",
  "glmnet",
  "knitr",
  "rmarkdown",
  "kableExtra",
  "Rcpp",
  "Matrix",
  "devtools",
  "remotes"
)
if (install_arrow) {
  cran_packages <- c(cran_packages, "arrow")
} else {
  log_info("Skipping R package arrow by default. Set INSTALL_R_ARROW=1 to build it.")
}

log_section("Install CRAN packages")
if (fast_install) {
  log_info("Fast install mode is enabled: skipping HTML docs, multi-arch, and test-load checks.")
} else {
  log_info("Fast install mode is disabled. Set R_INSTALL_FAST=1 to speed up source package installation.")
}
install_missing_cran(cran_packages)

options(BioC_mirror = bioc)
target_bioc_version <- Sys.getenv("BIOC_VERSION", "")
if (nzchar(target_bioc_version)) {
  log_section("Configure Bioconductor version")
  log_info(paste("Requested Bioconductor version:", target_bioc_version))
  tryCatch(
    {
      BiocManager::install(version = target_bioc_version, ask = FALSE, update = TRUE)
    },
    error = function(e) {
      log_warn(paste(
        "Failed to set Bioconductor version",
        target_bioc_version,
        "Using release for current R:",
        BiocManager::version(),
        "Error:",
        conditionMessage(e)
      ))
    }
  )
}

bioc_packages <- c(
  "BiocGenerics",
  "Biostrings",
  "GenomicRanges",
  "IRanges",
  "S4Vectors",
  "GenomicAlignments",
  "SummarizedExperiment",
  "SingleCellExperiment",
  "MultiAssayExperiment",
  "AnnotationDbi",
  "AnnotationHub",
  "BiocFileCache",
  "BiocParallel",
  "DelayedArray",
  "MatrixGenerics",
  "org.Hs.eg.db",
  "org.Mm.eg.db",
  "TxDb.Hsapiens.UCSC.hg38.knownGene",
  "BSgenome.Hsapiens.UCSC.hg38",
  "biomaRt",
  "rtracklayer",
  "VariantAnnotation",
  "Rsamtools",
  "DESeq2",
  "edgeR",
  "limma",
  "scran",
  "scater",
  "scuttle",
  "SCnorm",
  "muscat",
  "fgsea",
  "GSEABase",
  "minfi",
  "ChIPseeker",
  "DiffBind",
  "MotifDb",
  "mixOmics",
  "MOFA2",
  "BayesSpace",
  "tximport",
  "clusterProfiler",
  "enrichplot",
  "ComplexHeatmap",
  "Gviz",
  "karyoploteR",
  "EnhancedVolcano",
  "GSVA",
  "GEOquery"
)
log_section("Install Bioconductor packages")
log_info(paste("Using Bioconductor version:", BiocManager::version()))
missing_bioc_packages <- bioc_packages[
  !vapply(bioc_packages, requireNamespace, logical(1), quietly = TRUE)
]
install_with_progress(
  missing_bioc_packages,
  function(pkg) {
    BiocManager::install(
      pkg,
      ask = FALSE,
      update = FALSE,
      Ncpus = ncpus,
      INSTALL_opts = install_opts
    )
  },
  "Bioconductor"
)

if (install_seurat) {
  log_section("Install Seurat")
  install_missing_cran(c("Seurat", "SeuratObject"))
} else {
  log_info("Skipping Seurat because INSTALL_SEURAT is not 1.")
}

log_done("R package installation complete.")
RS

log_done "R package installation complete."
