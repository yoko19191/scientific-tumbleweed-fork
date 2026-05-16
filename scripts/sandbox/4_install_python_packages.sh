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
export CC="${CC:-gcc}"
export CXX="${CXX:-g++}"

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
  catboost
  category-encoders
  eli5
  feature-engine
  hdbscan
  imbalanced-learn
  lightgbm
  lime
  mlxtend
  optuna
  pingouin
  scikit-optimize
  shap
  umap-learn
  xgboost
  yellowbrick
  pmdarima
  prophet
  sktime
  tsfresh
  altair
  bokeh
  dash
  holoviews
  hvplot
  ipywidgets
  statsmodels
  scikit-learn
  matplotlib
  networkx
  panel
  plotnine
  seaborn
  plotly
  pyvis
  streamlit
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
  cyvcf2
  GEOparse
  gffutils
  pysam
  pyfaidx
  pybedtools
  gseapy
  HTSeq
  mygene
  bioservices
  goatools
  gprofiler-official
  anndata
  scanpy
  scikit-bio
  lifelines
  bioframe
  pyranges
  pyBigWig
  pysradb
  rdkit
  scikit-allel
  sgkit
)

optional_python_packages=(
  hail
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
  log_info "Installing optional Python packages when compatible."
  for package in "${optional_python_packages[@]}"; do
    uv pip install --system --upgrade "$package" || log_warn "Optional Python package failed and was skipped: $package"
  done
else
  log_warn "uv not found; using pip."
  "$PYTHON_BIN" -m pip install --upgrade "${python_packages[@]}"
  log_info "Installing optional Python packages when compatible."
  for package in "${optional_python_packages[@]}"; do
    "$PYTHON_BIN" -m pip install --upgrade "$package" || log_warn "Optional Python package failed and was skipped: $package"
  done
fi

log_done "Python package installation complete."
