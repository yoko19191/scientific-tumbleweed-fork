#!/usr/bin/env bash
set -euo pipefail

# Check the sandbox image for required commands, language packages, and baseline
# configuration. This script does not install anything.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
. "${SCRIPT_DIR}/_common.sh"

PYTHON_BIN="${PYTHON_BIN:-python3}"
APT_MIRROR_HOST="${APT_MIRROR_HOST:-mirrors.tuna.tsinghua.edu.cn}"
PYPI_MIRROR="${PYPI_MIRROR:-https://pypi.tuna.tsinghua.edu.cn/simple}"
NPM_MIRROR="${NPM_MIRROR:-https://registry.npmmirror.com}"
CRAN_MIRROR="${CRAN_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/CRAN}"
BIOC_MIRROR="${BIOC_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/bioconductor}"
R_SITE_LIBRARY="${R_SITE_LIBRARY:-}"
MINIFORGE_HOME="${MINIFORGE_HOME:-${HOME}/miniforge3}"
BIOINFO_ENV_NAME="${BIOINFO_ENV_NAME:-bioinfo}"
BIOINFO_ENV_PREFIX="${BIOINFO_ENV_PREFIX:-${MINIFORGE_HOME}/envs/${BIOINFO_ENV_NAME}}"
BIOINFO_ENV_BIN="${BIOINFO_ENV_BIN:-${BIOINFO_ENV_PREFIX}/bin}"
MAMBA_BIN="${MAMBA_BIN:-${MINIFORGE_HOME}/bin/mamba}"

REQUIRED_MISSING=0
OPTIONAL_MISSING=0

mark_required_missing() {
  REQUIRED_MISSING=$((REQUIRED_MISSING + 1))
}

mark_optional_missing() {
  OPTIONAL_MISSING=$((OPTIONAL_MISSING + 1))
}

need_cmd() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf "%sOK%s       command %-22s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$(command -v "$command_name")"
  else
    printf "%sMISSING%s  command %-22s\n" "$COLOR_RED" "$COLOR_RESET" "$command_name"
    mark_required_missing
  fi
}

need_one_cmd() {
  local label="$1"
  shift
  local command_name

  for command_name in "$@"; do
    if command -v "$command_name" >/dev/null 2>&1; then
      printf "%sOK%s       command %-22s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$label" "$(command -v "$command_name")"
      return 0
    fi
  done

  printf "%sMISSING%s  command %-22s checked: %s\n" "$COLOR_RED" "$COLOR_RESET" "$label" "$*"
  mark_required_missing
}

need_optional_cmd() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf "%sOK%s       optional command %-13s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$(command -v "$command_name")"
  else
    printf "%sOPTIONAL%s optional command %-13s\n" "$COLOR_YELLOW" "$COLOR_RESET" "$command_name"
    mark_optional_missing
  fi
}

need_bioinfo_cmd() {
  local command_name="$1"
  local alternate_command_name="${2:-}"
  local command_path="${BIOINFO_ENV_BIN}/${command_name}"
  local alternate_command_path=""

  if [ -n "$alternate_command_name" ]; then
    alternate_command_path="${BIOINFO_ENV_BIN}/${alternate_command_name}"
  fi

  if [ -x "$command_path" ]; then
    printf "%sOK%s       bioinfo CLI %-21s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$command_path"
  elif [ -n "$alternate_command_path" ] && [ -x "$alternate_command_path" ]; then
    printf "%sOK%s       bioinfo CLI %-21s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$alternate_command_path"
  elif command -v "$command_name" >/dev/null 2>&1; then
    printf "%sOK%s       bioinfo CLI %-21s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$(command -v "$command_name")"
  elif [ -n "$alternate_command_name" ] && command -v "$alternate_command_name" >/dev/null 2>&1; then
    printf "%sOK%s       bioinfo CLI %-21s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$(command -v "$alternate_command_name")"
  else
    printf "%sMISSING%s  bioinfo CLI %-21s checked: %s\n" "$COLOR_RED" "$COLOR_RESET" "$command_name" "$BIOINFO_ENV_BIN"
    mark_required_missing
  fi
}

need_optional_bioinfo_cmd() {
  local command_name="$1"
  local alternate_command_name="${2:-}"
  local command_path="${BIOINFO_ENV_BIN}/${command_name}"
  local alternate_command_path=""

  if [ -n "$alternate_command_name" ]; then
    alternate_command_path="${BIOINFO_ENV_BIN}/${alternate_command_name}"
  fi

  if [ -x "$command_path" ]; then
    printf "%sOK%s       optional bioinfo CLI %-12s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$command_path"
  elif [ -n "$alternate_command_path" ] && [ -x "$alternate_command_path" ]; then
    printf "%sOK%s       optional bioinfo CLI %-12s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$alternate_command_path"
  elif command -v "$command_name" >/dev/null 2>&1; then
    printf "%sOK%s       optional bioinfo CLI %-12s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$(command -v "$command_name")"
  elif [ -n "$alternate_command_name" ] && command -v "$alternate_command_name" >/dev/null 2>&1; then
    printf "%sOK%s       optional bioinfo CLI %-12s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_name" "$(command -v "$alternate_command_name")"
  else
    printf "%sOPTIONAL%s optional bioinfo CLI %-12s checked: %s\n" "$COLOR_YELLOW" "$COLOR_RESET" "$command_name" "$BIOINFO_ENV_BIN"
    mark_optional_missing
  fi
}

resolve_mamba() {
  if [ -x "$MAMBA_BIN" ]; then
    printf "%s" "$MAMBA_BIN"
  elif command -v mamba >/dev/null 2>&1; then
    command -v mamba
  else
    return 1
  fi
}

need_bioinfo_package() {
  local package_name="$1"
  local mamba_bin

  if ! mamba_bin="$(resolve_mamba)"; then
    printf "%sMISSING%s  bioinfo package %-17s mamba not found\n" "$COLOR_RED" "$COLOR_RESET" "$package_name"
    mark_required_missing
    return 0
  fi

  if [ ! -d "$BIOINFO_ENV_PREFIX" ]; then
    printf "%sMISSING%s  bioinfo package %-17s env not found: %s\n" "$COLOR_RED" "$COLOR_RESET" "$package_name" "$BIOINFO_ENV_PREFIX"
    mark_required_missing
    return 0
  fi

  if "$mamba_bin" list -p "$BIOINFO_ENV_PREFIX" "$package_name" 2>/dev/null | awk -v pkg="$package_name" '$1 == pkg { found = 1 } END { exit found ? 0 : 1 }'; then
    printf "%sOK%s       bioinfo package %-17s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$package_name" "$BIOINFO_ENV_PREFIX"
  else
    printf "%sMISSING%s  bioinfo package %-17s %s\n" "$COLOR_RED" "$COLOR_RESET" "$package_name" "$BIOINFO_ENV_PREFIX"
    mark_required_missing
  fi
}

need_optional_bioinfo_package() {
  local package_name="$1"
  local mamba_bin

  if ! mamba_bin="$(resolve_mamba)"; then
    printf "%sOPTIONAL%s optional bioinfo package %-8s mamba not found\n" "$COLOR_YELLOW" "$COLOR_RESET" "$package_name"
    mark_optional_missing
    return 0
  fi

  if [ ! -d "$BIOINFO_ENV_PREFIX" ]; then
    printf "%sOPTIONAL%s optional bioinfo package %-8s env not found: %s\n" "$COLOR_YELLOW" "$COLOR_RESET" "$package_name" "$BIOINFO_ENV_PREFIX"
    mark_optional_missing
    return 0
  fi

  if "$mamba_bin" list -p "$BIOINFO_ENV_PREFIX" "$package_name" 2>/dev/null | awk -v pkg="$package_name" '$1 == pkg { found = 1 } END { exit found ? 0 : 1 }'; then
    printf "%sOK%s       optional bioinfo package %-8s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$package_name" "$BIOINFO_ENV_PREFIX"
  else
    printf "%sOPTIONAL%s optional bioinfo package %-8s %s\n" "$COLOR_YELLOW" "$COLOR_RESET" "$package_name" "$BIOINFO_ENV_PREFIX"
    mark_optional_missing
  fi
}

need_mamba() {
  local mamba_bin

  if mamba_bin="$(resolve_mamba)"; then
    printf "%sOK%s       command %-22s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "mamba" "$mamba_bin"
  else
    printf "%sMISSING%s  command %-22s expected: %s\n" "$COLOR_RED" "$COLOR_RESET" "mamba" "$MAMBA_BIN"
    mark_required_missing
  fi
}

check_python_import() {
  local module="$1"
  local package_hint="${2:-$1}"

  if "$PYTHON_BIN" - "$module" >/dev/null 2>&1 <<'PY'
import importlib
import sys

module = sys.argv[1]
importlib.import_module(module)
PY
  then
    printf "%sOK%s       python import %-24s\n" "$COLOR_GREEN" "$COLOR_RESET" "$module"
  else
    printf "%sMISSING%s  python import %-24s install: %s\n" "$COLOR_RED" "$COLOR_RESET" "$module" "$package_hint"
    mark_required_missing
  fi
}

check_optional_python_import() {
  local module="$1"
  local package_hint="${2:-$1}"

  if "$PYTHON_BIN" - "$module" >/dev/null 2>&1 <<'PY'
import importlib
import sys

module = sys.argv[1]
importlib.import_module(module)
PY
  then
    printf "%sOK%s       optional python import %-15s\n" "$COLOR_GREEN" "$COLOR_RESET" "$module"
  else
    printf "%sOPTIONAL%s optional python import %-15s install: %s\n" "$COLOR_YELLOW" "$COLOR_RESET" "$module" "$package_hint"
    mark_optional_missing
  fi
}

check_r_package() {
  local package="$1"
  if command -v Rscript >/dev/null 2>&1 && R_SITE_LIBRARY="$R_SITE_LIBRARY" Rscript -e "site <- Sys.getenv('R_SITE_LIBRARY', ''); if (nzchar(site)) .libPaths(unique(c(site, .libPaths()))); quit(status = ifelse(requireNamespace('$package', quietly = TRUE), 0, 1))" >/dev/null 2>&1; then
    printf "%sOK%s       R package %-28s\n" "$COLOR_GREEN" "$COLOR_RESET" "$package"
  else
    printf "%sMISSING%s  R package %-28s\n" "$COLOR_RED" "$COLOR_RESET" "$package"
    mark_required_missing
  fi
}

check_optional_r_package() {
  local package="$1"
  if command -v Rscript >/dev/null 2>&1 && R_SITE_LIBRARY="$R_SITE_LIBRARY" Rscript -e "site <- Sys.getenv('R_SITE_LIBRARY', ''); if (nzchar(site)) .libPaths(unique(c(site, .libPaths()))); quit(status = ifelse(requireNamespace('$package', quietly = TRUE), 0, 1))" >/dev/null 2>&1; then
    printf "%sOK%s       optional R package %-19s\n" "$COLOR_GREEN" "$COLOR_RESET" "$package"
  else
    printf "%sOPTIONAL%s optional R package %-19s\n" "$COLOR_YELLOW" "$COLOR_RESET" "$package"
    mark_optional_missing
  fi
}

check_latex_file() {
  local filename="$1"
  if command -v kpsewhich >/dev/null 2>&1 && kpsewhich "$filename" >/dev/null 2>&1; then
    printf "%sOK%s       LaTeX file %-27s\n" "$COLOR_GREEN" "$COLOR_RESET" "$filename"
  else
    printf "%sMISSING%s  LaTeX file %-27s\n" "$COLOR_RED" "$COLOR_RESET" "$filename"
    mark_required_missing
  fi
}

check_file_contains() {
  local file_path="$1"
  local pattern="$2"
  local label="$3"

  if [ -f "$file_path" ] && grep -Eq "$pattern" "$file_path"; then
    printf "%sOK%s       config %-30s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$label" "$file_path"
  else
    printf "%sMISSING%s  config %-30s %s\n" "$COLOR_RED" "$COLOR_RESET" "$label" "$file_path"
    mark_required_missing
  fi
}

check_command_output_contains() {
  local command_label="$1"
  local expected="$2"
  shift 2

  if "$@" 2>/dev/null | grep -Fq "$expected"; then
    printf "%sOK%s       config %-30s contains %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$command_label" "$expected"
  else
    printf "%sMISSING%s  config %-30s expected %s\n" "$COLOR_RED" "$COLOR_RESET" "$command_label" "$expected"
    mark_required_missing
  fi
}

log_section "Check core runtime commands"
need_cmd bash
need_cmd python
need_cmd python3
need_cmd uv
need_cmd pip
need_cmd node
need_cmd npm
need_cmd pnpm
need_cmd yarn
need_cmd R
need_cmd Rscript
need_cmd rig
need_mamba

log_section "Check build and system commands"
need_cmd sudo
need_cmd gcc
need_cmd g++
need_cmd gfortran
need_cmd make
need_cmd cmake
need_cmd ninja
need_cmd autoconf
need_cmd automake
need_cmd libtoolize
need_cmd pkg-config
need_cmd curl
need_cmd wget
need_cmd git
need_cmd jq
need_cmd gpg
need_cmd lsb_release
need_cmd locale
need_cmd unzip
need_cmd zip
need_cmd xz
need_cmd file
need_cmd rg

log_section "Check document and LaTeX commands"
need_cmd pandoc
need_cmd gs
need_cmd libreoffice
need_cmd wkhtmltopdf
need_cmd pdftotext
need_cmd qpdf
need_cmd mutool
need_one_cmd imagemagick magick convert
need_cmd gm
need_cmd inkscape
need_cmd rsvg-convert
need_cmd dot
need_cmd plantuml
need_cmd tesseract
need_cmd ocrmypdf
need_cmd fc-match
need_cmd kpsewhich
need_cmd latexmk
need_cmd xelatex
need_cmd lualatex
need_cmd pdflatex
need_cmd biber

log_section "Check mamba bioinfo CLI commands"
if [ -d "$BIOINFO_ENV_BIN" ]; then
  log_info "Checking bioinformatics CLI tools from: $BIOINFO_ENV_BIN"
else
  log_warn "Bioinformatics environment bin directory is missing: $BIOINFO_ENV_BIN"
fi

log_subsection "Check mamba bioinfo packages"
for package in \
  fastqc fastp trimmomatic multiqc cutadapt seqtk fastq-screen \
  bwa-mem2 star hisat2 bowtie2 minimap2 salmon kallisto \
  samtools picard bedtools deeptools sambamba subread htslib mosdepth qualimap \
  gatk4 bcftools freebayes snpeff vcftools snpsift \
  starsolo alevin-fry bustools \
  macs3 chromvar \
  spades flye hifiasm quast \
  mafft muscle iqtree raxml-ng fasttree mrbayes \
  sra-tools entrez-direct seqkit csvtk parallel snakemake
do
  need_bioinfo_package "$package"
done

log_subsection "Check optional mamba bioinfo packages"
for package in \
  nextflow nf-core cromwell womtool \
  dvc mlflow quarto \
  kraken2 bracken metaphlan humann kaiju mash fastani \
  plink2 eigensoft admixture king \
  prokka bakta eggnog-mapper ensembl-vep
do
  need_optional_bioinfo_package "$package"
done

log_subsection "QC commands"
need_bioinfo_cmd fastqc
need_bioinfo_cmd fastp
need_bioinfo_cmd trimmomatic
need_bioinfo_cmd multiqc
need_bioinfo_cmd cutadapt
need_bioinfo_cmd seqtk
need_bioinfo_cmd fastq_screen fastq-screen

log_subsection "Alignment commands"
need_bioinfo_cmd bwa-mem2
need_bioinfo_cmd bowtie2
need_bioinfo_cmd STAR star
need_bioinfo_cmd hisat2
need_bioinfo_cmd minimap2
need_bioinfo_cmd salmon
need_bioinfo_cmd kallisto

log_subsection "BAM operation commands"
need_bioinfo_cmd samtools
need_bioinfo_cmd picard
need_bioinfo_cmd bedtools
need_bioinfo_cmd bamCoverage
need_bioinfo_cmd sambamba
need_bioinfo_cmd featureCounts
need_bioinfo_cmd tabix
need_bioinfo_cmd bgzip
need_bioinfo_cmd mosdepth
need_bioinfo_cmd qualimap

log_subsection "Variant calling commands"
need_bioinfo_cmd gatk gatk4
need_bioinfo_cmd bcftools
need_bioinfo_cmd freebayes
need_bioinfo_cmd snpEff snpeff
need_bioinfo_cmd SnpSift snpsift
need_bioinfo_cmd vcftools

log_subsection "scRNA-seq commands"
need_bioinfo_cmd alevin-fry
need_optional_bioinfo_cmd bustools

log_subsection "Multi-omics commands"
need_bioinfo_cmd macs3

log_subsection "Genome assembly commands"
need_bioinfo_cmd spades.py spades
need_bioinfo_cmd flye
need_bioinfo_cmd hifiasm
need_bioinfo_cmd quast

log_subsection "Phylogeny commands"
need_bioinfo_cmd mafft
need_bioinfo_cmd muscle
need_bioinfo_cmd iqtree
need_bioinfo_cmd raxml-ng
need_bioinfo_cmd FastTree fasttree
need_bioinfo_cmd mb mrbayes

log_subsection "Common utility commands"
need_bioinfo_cmd fasterq-dump
need_bioinfo_cmd esearch
need_bioinfo_cmd seqkit
need_bioinfo_cmd csvtk
need_bioinfo_cmd parallel
need_bioinfo_cmd snakemake
need_optional_bioinfo_cmd nextflow
need_optional_bioinfo_cmd nf-core
need_optional_bioinfo_cmd cromwell
need_optional_bioinfo_cmd womtool
need_optional_bioinfo_cmd dvc
need_optional_bioinfo_cmd mlflow
need_optional_bioinfo_cmd quarto
need_optional_cmd mmdc

log_subsection "Metagenomics commands"
need_optional_bioinfo_cmd kraken2
need_optional_bioinfo_cmd bracken
need_optional_bioinfo_cmd metaphlan
need_optional_bioinfo_cmd humann
need_optional_bioinfo_cmd kaiju
need_optional_bioinfo_cmd mash
need_optional_bioinfo_cmd fastANI fastani

log_subsection "GWAS and population genetics commands"
need_optional_bioinfo_cmd plink2
need_optional_bioinfo_cmd smartpca
need_optional_bioinfo_cmd admixture
need_optional_bioinfo_cmd king

log_subsection "Genome annotation commands"
need_optional_bioinfo_cmd prokka
need_optional_bioinfo_cmd bakta
need_optional_bioinfo_cmd emapper.py eggnog-mapper
need_optional_bioinfo_cmd vep ensembl-vep

log_section "Check mirror and language configuration"
check_file_contains /etc/apt/sources.list "$APT_MIRROR_HOST" "apt mirror"
check_file_contains /etc/pip.conf "$PYPI_MIRROR" "pip mirror"
check_file_contains /etc/profile.d/sandbox-environment.sh "$PYPI_MIRROR" "Python package environment"
check_file_contains /etc/profile.d/sandbox-environment.sh "$NPM_MIRROR" "Node package environment"
check_file_contains /etc/profile.d/sandbox-environment.sh "$CRAN_MIRROR" "R CRAN environment"
check_file_contains /etc/profile.d/sandbox-environment.sh "$BIOC_MIRROR" "Bioconductor environment"
if command -v npm >/dev/null 2>&1; then
  check_command_output_contains "npm registry" "$NPM_MIRROR" npm config get registry
fi
if command -v Rscript >/dev/null 2>&1; then
  check_command_output_contains "R CRAN mirror" "$CRAN_MIRROR" Rscript -e 'cat(getOption("repos")[["CRAN"]])'
  check_command_output_contains "R Bioconductor mirror" "$BIOC_MIRROR" Rscript -e 'cat(getOption("BioC_mirror"))'
fi

log_section "Check Python packages"
check_python_import requests requests
check_python_import yaml PyYAML
check_python_import duckdb duckdb
check_python_import pyarrow pyarrow
check_python_import polars polars
check_python_import openpyxl openpyxl
check_python_import pandas pandas
check_python_import numpy numpy
check_python_import scipy scipy
check_python_import sklearn scikit-learn
check_python_import statsmodels statsmodels
check_python_import catboost catboost
check_python_import category_encoders category-encoders
check_python_import eli5 eli5
check_python_import feature_engine feature-engine
check_python_import hdbscan hdbscan
check_python_import imblearn imbalanced-learn
check_python_import lightgbm lightgbm
check_python_import lime lime
check_python_import mlxtend mlxtend
check_python_import optuna optuna
check_python_import pingouin pingouin
check_python_import skopt scikit-optimize
check_python_import shap shap
check_python_import umap umap-learn
check_python_import xgboost xgboost
check_python_import yellowbrick yellowbrick
check_python_import pmdarima pmdarima
check_python_import prophet prophet
check_python_import sktime sktime
check_python_import tsfresh tsfresh
check_python_import matplotlib matplotlib
check_python_import seaborn seaborn
check_python_import plotly plotly
check_python_import altair altair
check_python_import bokeh bokeh
check_python_import dash dash
check_python_import holoviews holoviews
check_python_import hvplot hvplot
check_python_import ipywidgets ipywidgets
check_python_import networkx networkx
check_python_import panel panel
check_python_import plotnine plotnine
check_python_import pyvis pyvis
check_python_import streamlit streamlit
check_python_import PIL Pillow
check_python_import fitz PyMuPDF
check_python_import pptx python-pptx
check_python_import svglib svglib
check_python_import reportlab reportlab
check_python_import cairosvg cairosvg
check_python_import mammoth mammoth
check_python_import markdownify markdownify
check_python_import bs4 beautifulsoup4
check_python_import ebooklib ebooklib
check_python_import nbconvert nbconvert
check_python_import curl_cffi curl_cffi
check_python_import pyreadstat pyreadstat
check_python_import tabula tabula-py
check_python_import google.genai google-genai
check_python_import openai openai
check_python_import Bio biopython
check_python_import cyvcf2 cyvcf2
check_python_import GEOparse GEOparse
check_python_import gffutils gffutils
check_python_import pysam pysam
check_python_import pyfaidx pyfaidx
check_python_import pybedtools pybedtools
check_python_import gseapy gseapy
check_python_import HTSeq HTSeq
check_python_import mygene mygene
check_python_import bioservices bioservices
check_python_import goatools goatools
check_python_import gprofiler gprofiler-official
check_python_import anndata anndata
check_python_import scanpy scanpy
check_python_import skbio scikit-bio
check_python_import lifelines lifelines
check_python_import bioframe bioframe
check_python_import pyranges pyranges
check_python_import pyBigWig pyBigWig
check_python_import pysradb pysradb
check_python_import rdkit rdkit
check_python_import allel scikit-allel
check_python_import sgkit sgkit

log_section "Check LaTeX packages and fonts"
check_latex_file article.cls
check_latex_file ctex.sty
check_latex_file amsmath.sty
check_latex_file graphicx.sty
check_latex_file booktabs.sty
check_latex_file hyperref.sty
check_latex_file siunitx.sty
if command -v fc-match >/dev/null 2>&1 && fc-match "Noto Serif CJK SC" >/dev/null 2>&1; then
  printf "%sOK%s       font %-34s\n" "$COLOR_GREEN" "$COLOR_RESET" "Noto Serif CJK SC"
else
  printf "%sMISSING%s  font %-34s\n" "$COLOR_RED" "$COLOR_RESET" "Noto Serif CJK SC"
  mark_required_missing
fi

log_section "Check R packages"
if command -v Rscript >/dev/null 2>&1; then
  log_info "R_SITE_LIBRARY override: ${R_SITE_LIBRARY:-<not set>}"
  R_SITE_LIBRARY="$R_SITE_LIBRARY" Rscript -e "site <- Sys.getenv('R_SITE_LIBRARY', ''); if (nzchar(site)) .libPaths(unique(c(site, .libPaths()))); cat(paste(.libPaths(), collapse = ' | '))" 2>/dev/null | while IFS= read -r line; do
    log_info "R library paths: $line"
  done
fi
for package in \
  tidyverse data.table dplyr dtplyr readr tibble tidyr readxl writexl openxlsx duckdb DBI RSQLite \
  janitor skimr broom ggplot2 ggpubr ggrepel patchwork cowplot plotly \
  htmlwidgets DT pheatmap VennDiagram UpSetR igraph vegan survival \
  survminer lme4 glmnet xgboost lightgbm tidymodels caret e1071 kernlab \
  rpart nnet recipes parsnip workflows tune rsample yardstick vip DALEX \
  shapviz pROC forecast rstatix performance factoextra ggraph tidygraph \
  ggridges ggExtra ggvenn ggtext ggstatsplot esquisse leaflet \
  knitr rmarkdown kableExtra Rcpp Matrix devtools \
  remotes BiocManager BiocGenerics Biostrings GenomicRanges IRanges \
  S4Vectors GenomicAlignments SummarizedExperiment SingleCellExperiment \
  MultiAssayExperiment AnnotationDbi AnnotationHub BiocFileCache \
  BiocParallel DelayedArray MatrixGenerics org.Hs.eg.db org.Mm.eg.db \
  TxDb.Hsapiens.UCSC.hg38.knownGene BSgenome.Hsapiens.UCSC.hg38 biomaRt \
  rtracklayer VariantAnnotation Rsamtools DESeq2 edgeR limma tximport \
  scran scater scuttle SCnorm muscat clusterProfiler enrichplot fgsea \
  GSEABase GSVA minfi ChIPseeker DiffBind MotifDb mixOmics MOFA2 \
  BayesSpace ComplexHeatmap Gviz karyoploteR EnhancedVolcano GEOquery \
  ggtree phyloseq SNPRelate
do
  check_r_package "$package"
done

log_section "Check optional R and Python packages"
check_optional_r_package Seurat
check_optional_r_package SeuratObject
check_optional_r_package arrow
check_optional_r_package catboost
check_optional_r_package prophet
check_optional_python_import xlwt xlwt
check_optional_python_import hail hail

echo
if [ "$REQUIRED_MISSING" -gt 0 ]; then
  log_error "Check failed: $REQUIRED_MISSING required item(s) are missing. Optional missing: $OPTIONAL_MISSING."
  exit 1
fi

log_done "Check complete. Required items are ready. Optional missing: $OPTIONAL_MISSING."
