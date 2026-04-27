#!/usr/bin/env bash
set -euo pipefail

# Install Python packages for scientific analysis, documents, AI clients, and
# bioinformatics workflows.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
. "${SCRIPT_DIR}/_common.sh"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PYPI_MIRROR="${PYPI_MIRROR:-https://pypi.tuna.tsinghua.edu.cn/simple}"

export PIP_INDEX_URL="$PYPI_MIRROR"
export UV_DEFAULT_INDEX="$PYPI_MIRROR"
export UV_INDEX_URL="$PYPI_MIRROR"
export PIP_ROOT_USER_ACTION="${PIP_ROOT_USER_ACTION:-ignore}"

python_packages=(
  requests
  PyYAML
  duckdb
  pyarrow
  polars
  openpyxl
  pandas
  numpy
  scipy
  altair
  bokeh
  statsmodels
  scikit-learn
  matplotlib
  seaborn
  plotly
  Pillow
  PyMuPDF
  python-pptx
  reportlab
  svglib
  cairosvg
  mammoth
  markdownify
  beautifulsoup4
  ebooklib
  nbconvert
  curl_cffi
  google-genai
  openai
  pyreadstat
  xlwt
  tabula-py
  adjustText
  upsetplot
  venn
  wordcloud
  missingno
  biopython
  pysam
  pyfaidx
  pybedtools
  gseapy
  mygene
  bioservices
  goatools
  gprofiler-official
  anndata
  scanpy
  scikit-bio
  lifelines
  bioframe
  pyBigWig
)

log_section "Install Python package tooling"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  log_error "Python interpreter not found: $PYTHON_BIN"
  exit 1
fi

log_info "Using Python: $PYTHON_BIN"
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
if ! command -v uv >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --upgrade uv
fi

log_section "Install Python packages"
log_info "Using PyPI mirror: $PYPI_MIRROR"
if command -v uv >/dev/null 2>&1; then
  log_info "Using uv for system package installation."
  uv pip install --system --upgrade "${python_packages[@]}"
else
  log_warn "uv not found; using pip."
  "$PYTHON_BIN" -m pip install --upgrade "${python_packages[@]}"
fi

log_done "Python package installation complete."
