#!/usr/bin/env bash
set -euo pipefail

# Install Node package managers, document tooling, LaTeX, and scientific CLI
# tools. The base compilers and native libraries should come from script 1.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
. "${SCRIPT_DIR}/_common.sh"

require_root_prefix

NPM_MIRROR="${NPM_MIRROR:-https://registry.npmmirror.com}"
NODE_MAJOR="${NODE_MAJOR:-20}"
INSTALL_NODESOURCE="${INSTALL_NODESOURCE:-1}"
MINIFORGE_HOME="${MINIFORGE_HOME:-${HOME}/miniforge3}"
BIOINFO_ENV_NAME="${BIOINFO_ENV_NAME:-bioinfo}"
BIOINFO_ENV_PREFIX="${BIOINFO_ENV_PREFIX:-${MINIFORGE_HOME}/envs/${BIOINFO_ENV_NAME}}"
BIOINFO_PYTHON_VERSION="${BIOINFO_PYTHON_VERSION:-3.11}"
MAMBA_BIN="${MAMBA_BIN:-${MINIFORGE_HOME}/bin/mamba}"

export DEBIAN_FRONTEND=noninteractive
export npm_config_registry="$NPM_MIRROR"

document_cli_packages=(
  pandoc
  ghostscript
  fontconfig
  libreoffice
  libreoffice-writer
  libreoffice-calc
  libreoffice-impress
  libreoffice-java-common
  default-jre
  wkhtmltopdf
  poppler-utils
  qpdf
  mupdf-tools
  imagemagick
  graphicsmagick
  inkscape
  librsvg2-bin
  graphviz
  plantuml
  tesseract-ocr
  ocrmypdf
  ffmpeg
)

latex_packages=(
  texlive-base
  texlive-latex-base
  texlive-latex-recommended
  texlive-latex-extra
  texlive-fonts-recommended
  texlive-science
  texlive-xetex
  texlive-luatex
  texlive-lang-chinese
  latexmk
  biber
  fonts-noto-cjk
  fonts-noto-color-emoji
  fonts-liberation
)

npm_global_packages=(
  pnpm
  yarn
  @mermaid-js/mermaid-cli
)

bioinfo_qc_packages=(
  fastqc
  fastp
  trimmomatic
  multiqc
  cutadapt
  seqtk
  fastq-screen
)

bioinfo_alignment_packages=(
  bwa-mem2
  star
  hisat2
  bowtie2
  minimap2
  salmon
  kallisto
)

bioinfo_bam_packages=(
  samtools
  picard
  bedtools
  deeptools
  sambamba
  subread
  htslib
  mosdepth
  qualimap
)

bioinfo_variant_packages=(
  gatk4
  bcftools
  freebayes
  snpeff
  vcftools
  snpsift
)

bioinfo_scrna_packages=(
  starsolo
  alevin-fry
  bustools
)

bioinfo_multiomics_packages=(
  macs3
  chromvar
)

bioinfo_assembly_packages=(
  spades
  flye
  hifiasm
  quast
)

bioinfo_phylogeny_packages=(
  mafft
  muscle
  iqtree
  raxml-ng
  fasttree
  mrbayes
)

bioinfo_common_packages=(
  sra-tools
  entrez-direct
  seqkit
  csvtk
  parallel
  snakemake
)

bioinfo_workflow_optional_packages=(
  nextflow
  nf-core
  cromwell
  womtool
  dvc
  mlflow
  quarto
)

bioinfo_metagenomics_packages=(
  kraken2
  bracken
  metaphlan
  humann
  kaiju
  mash
  fastani
)

bioinfo_gwas_packages=(
  plink2
  eigensoft
  admixture
  king
)

bioinfo_annotation_packages=(
  prokka
  bakta
  eggnog-mapper
)

bioinfo_optional_packages=(
  ensembl-vep
)

node_major_version() {
  node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0
}

install_node_runtime() {
  log_section "Install Node.js runtime"
  if command -v node >/dev/null 2>&1 && [ "$(node_major_version)" -ge 18 ]; then
    log_info "Node.js $(node -v) is available."
    return 0
  fi

  if [ "$INSTALL_NODESOURCE" = "1" ]; then
    log_info "Installing Node.js ${NODE_MAJOR}.x from NodeSource."
    "${ROOT_PREFIX[@]}" apt-get install -y --no-install-recommends ca-certificates curl gnupg
    curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | "${ROOT_PREFIX[@]}" bash -
    "${ROOT_PREFIX[@]}" apt-get install -y --no-install-recommends nodejs
  else
    log_warn "INSTALL_NODESOURCE is not 1; installing Ubuntu nodejs/npm packages."
    "${ROOT_PREFIX[@]}" apt-get install -y --no-install-recommends nodejs npm
  fi

  if command -v node >/dev/null 2>&1 && [ "$(node_major_version)" -ge 18 ]; then
    log_done "Node.js $(node -v) is ready."
  else
    log_warn "Node.js is missing or older than 18. Some JavaScript tools may not work."
  fi
}

install_node_package_managers() {
  log_section "Configure npm and install package managers"
  if ! command -v npm >/dev/null 2>&1; then
    log_warn "npm is not available; skipping pnpm/yarn installation."
    return 0
  fi

  log_info "Using npm mirror: $NPM_MIRROR"
  npm config set registry "$NPM_MIRROR"
  if [ "${EUID}" -eq 0 ]; then
    npm config set --location=global registry "$NPM_MIRROR" || true
  fi

  npm install -g "${npm_global_packages[@]}"
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

ensure_bioinfo_env() {
  local mamba_bin="$1"

  log_section "Prepare mamba bioinfo environment"
  log_info "Using mamba: $mamba_bin"
  log_info "Using bioinfo env: $BIOINFO_ENV_PREFIX"

  if [ ! -d "$BIOINFO_ENV_PREFIX" ]; then
    "$mamba_bin" create -y -p "$BIOINFO_ENV_PREFIX" "python=${BIOINFO_PYTHON_VERSION}"
  fi
}

mamba_install_group() {
  local mamba_bin="$1"
  local label="$2"
  shift 2

  log_section "Install bioinfo CLI: $label"
  "$mamba_bin" install -y -p "$BIOINFO_ENV_PREFIX" -c bioconda -c conda-forge "$@"
}

mamba_install_optional_group() {
  local mamba_bin="$1"
  local label="$2"
  local package
  shift 2

  log_section "Install optional bioinfo CLI: $label"
  for package in "$@"; do
    "$mamba_bin" install -y -p "$BIOINFO_ENV_PREFIX" -c bioconda -c conda-forge "$package" || log_warn "Optional mamba package failed and was skipped: $package"
  done
}

install_bioinfo_cli_environment() {
  local mamba_bin

  if ! mamba_bin="$(resolve_mamba)"; then
    log_error "mamba is not available. Install Miniforge under $MINIFORGE_HOME or set MAMBA_BIN."
    exit 1
  fi

  ensure_bioinfo_env "$mamba_bin"
  mamba_install_group "$mamba_bin" "QC" "${bioinfo_qc_packages[@]}"
  mamba_install_group "$mamba_bin" "Alignment" "${bioinfo_alignment_packages[@]}"
  mamba_install_group "$mamba_bin" "BAM operations" "${bioinfo_bam_packages[@]}"
  mamba_install_group "$mamba_bin" "Variant calling" "${bioinfo_variant_packages[@]}"
  mamba_install_group "$mamba_bin" "scRNA-seq" "${bioinfo_scrna_packages[@]}"
  mamba_install_group "$mamba_bin" "Multi-omics" "${bioinfo_multiomics_packages[@]}"
  mamba_install_group "$mamba_bin" "Genome assembly" "${bioinfo_assembly_packages[@]}"
  mamba_install_group "$mamba_bin" "Phylogeny" "${bioinfo_phylogeny_packages[@]}"
  mamba_install_group "$mamba_bin" "Common utilities" "${bioinfo_common_packages[@]}"
  mamba_install_optional_group "$mamba_bin" "Workflow engines" "${bioinfo_workflow_optional_packages[@]}"
  mamba_install_optional_group "$mamba_bin" "Metagenomics" "${bioinfo_metagenomics_packages[@]}"
  mamba_install_optional_group "$mamba_bin" "GWAS and population genetics" "${bioinfo_gwas_packages[@]}"
  mamba_install_optional_group "$mamba_bin" "Genome annotation" "${bioinfo_annotation_packages[@]}"
  mamba_install_optional_group "$mamba_bin" "Variant annotation" "${bioinfo_optional_packages[@]}"
}

log_section "Install CLI and LaTeX environment"
apt_update
install_node_runtime
install_node_package_managers
apt_install_required "Install document CLI tools" "${document_cli_packages[@]}"
apt_install_required "Install practical LaTeX environment" "${latex_packages[@]}"
install_bioinfo_cli_environment

log_section "Refresh font cache"
if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f || true
else
  log_warn "fc-cache is not available; skipping font cache refresh."
fi

log_done "CLI and LaTeX installation complete."
