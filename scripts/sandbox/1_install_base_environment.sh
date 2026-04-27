#!/usr/bin/env bash
set -euo pipefail

# Install the base Ubuntu, Python, R, and native build environment. Keep heavy
# CLI tools, LaTeX, and language packages in later scripts.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
. "${SCRIPT_DIR}/_common.sh"

require_root_prefix

PYTHON_BIN="${PYTHON_BIN:-python3}"
R_VERSION_SPEC="${R_VERSION_SPEC:-release}"

export DEBIAN_FRONTEND=noninteractive

base_packages=(
  ca-certificates
  curl
  wget
  git
  jq
  unzip
  zip
  xz-utils
  file
  sudo
  gnupg
  lsb-release
  apt-transport-https
  software-properties-common
  locales
  tzdata
  ripgrep
  less
  tree
  rsync
  vim-tiny
)

build_packages=(
  build-essential
  gcc
  g++
  gfortran
  pkg-config
  cmake
  make
  ninja-build
  autoconf
  automake
  libtool
)

python_packages=(
  python3
  python3-pip
  python3-dev
  python3-venv
  python-is-python3
  libffi-dev
  libsqlite3-dev
)

native_dev_packages=(
  libcurl4-openssl-dev
  libssl-dev
  libxml2-dev
  libxslt1-dev
  libuv1-dev
  libcairo2-dev
  libpng-dev
  libjpeg-dev
  libtiff-dev
  libfreetype6-dev
  libfontconfig1-dev
  libharfbuzz-dev
  libfribidi-dev
  libpango1.0-dev
  libgdk-pixbuf-2.0-dev
  libxt-dev
  libblas-dev
  liblapack-dev
  libbz2-dev
  liblzma-dev
  zlib1g-dev
  libgit2-dev
  libglpk-dev
  libgsl-dev
  libhdf5-dev
  h5utils
  libudunits2-dev
  libgeos-dev
  libproj-dev
  libgdal-dev
  libnetcdf-dev
  libgmp3-dev
  libmpfr-dev
  libssh2-1-dev
  libpcre2-dev
  libreadline-dev
  libicu-dev
  libboost-all-dev
  fonts-noto-cjk
  fonts-noto-color-emoji
  fonts-liberation
)

optional_native_dev_packages=(
  libtiff5-dev
  libbam-dev
  libhts-dev
)

install_rig() {
  if command -v rig >/dev/null 2>&1; then
    log_info "rig is already available: $(command -v rig)"
    return 0
  fi

  log_subsection "Install rig"
  "${ROOT_PREFIX[@]}" curl -L https://rig.r-pkg.org/deb/rig.gpg -o /etc/apt/trusted.gpg.d/rig.gpg
  echo "deb http://rig.r-pkg.org/deb rig main" | "${ROOT_PREFIX[@]}" tee /etc/apt/sources.list.d/rig.list >/dev/null
  "${ROOT_PREFIX[@]}" apt-get update
  "${ROOT_PREFIX[@]}" apt-get install -y --no-install-recommends r-rig
}

install_r_runtime() {
  log_subsection "Install R runtime"
  if ! command -v rig >/dev/null 2>&1; then
    install_rig
  fi

  if command -v Rscript >/dev/null 2>&1; then
    log_info "R is already available: $(R --version | sed -n '1p')"
    return 0
  fi

  if "${ROOT_PREFIX[@]}" rig add "$R_VERSION_SPEC"; then
    "${ROOT_PREFIX[@]}" rig default "$R_VERSION_SPEC" || true
  else
    log_warn "rig could not install R ${R_VERSION_SPEC}; falling back to Ubuntu r-base packages."
    "${ROOT_PREFIX[@]}" apt-get install -y --no-install-recommends r-base r-base-dev
  fi

  if ! command -v Rscript >/dev/null 2>&1; then
    log_error "Rscript is not available after R installation."
    exit 1
  fi

  log_done "Using R: $(R --version | sed -n '1p')"
}

log_section "Install base Ubuntu environment"
apt_update
apt_install_required "Install base shell utilities" "${base_packages[@]}"
apt_install_required "Install compilers and build tools" "${build_packages[@]}"
apt_install_required "Install Python runtime and headers" "${python_packages[@]}"
apt_install_required "Install native development libraries for Python and R packages" "${native_dev_packages[@]}"
apt_install_optional "Install optional native libraries when available" "${optional_native_dev_packages[@]}"

log_section "Configure locales and fonts"
if command -v locale-gen >/dev/null 2>&1; then
  "${ROOT_PREFIX[@]}" sed -i \
    -e 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' \
    -e 's/^# *zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' \
    /etc/locale.gen
  "${ROOT_PREFIX[@]}" locale-gen
  "${ROOT_PREFIX[@]}" update-locale LANG="${LANG:-en_US.UTF-8}" || true
else
  log_warn "locale-gen is not available; skipping locale generation."
fi

if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f || true
else
  log_warn "fc-cache is not available yet; LaTeX/CLI script will refresh font cache later."
fi

log_section "Install Python package manager"
ensure_command "$PYTHON_BIN" "python3" >/dev/null
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
if ! command -v uv >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --upgrade uv
fi
log_done "Python base environment is ready."

log_section "Install R base runtime"
install_r_runtime

log_done "Base environment installation complete."
