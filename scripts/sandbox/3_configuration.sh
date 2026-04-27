#!/usr/bin/env bash
set -euo pipefail

# Configure mirrors, usability defaults, and baseline Python/R package settings.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
. "${SCRIPT_DIR}/_common.sh"

require_root_prefix

APT_MIRROR="${APT_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/ubuntu}"
APT_PORTS_MIRROR="${APT_PORTS_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports}"
PYPI_MIRROR="${PYPI_MIRROR:-https://pypi.tuna.tsinghua.edu.cn/simple}"
NPM_MIRROR="${NPM_MIRROR:-https://registry.npmmirror.com}"
CRAN_MIRROR="${CRAN_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/CRAN}"
BIOC_MIRROR="${BIOC_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/bioconductor}"
R_NCPUS="${R_NCPUS:-$(nproc 2>/dev/null || echo 2)}"

export DEBIAN_FRONTEND=noninteractive

codename="$(. /etc/os-release && printf '%s' "${VERSION_CODENAME:-jammy}")"
arch="$(dpkg --print-architecture)"
if [ "$arch" = "arm64" ] || [ "$arch" = "armhf" ]; then
  apt_base="$APT_PORTS_MIRROR"
else
  apt_base="$APT_MIRROR"
fi

log_section "Configure apt mirror"
log_info "Using apt mirror: $apt_base ($codename, $arch)"
"${ROOT_PREFIX[@]}" cp -a /etc/apt/sources.list "/etc/apt/sources.list.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
"${ROOT_PREFIX[@]}" tee /etc/apt/sources.list >/dev/null <<EOF
deb ${apt_base} ${codename} main restricted universe multiverse
deb ${apt_base} ${codename}-updates main restricted universe multiverse
deb ${apt_base} ${codename}-backports main restricted universe multiverse
deb ${apt_base} ${codename}-security main restricted universe multiverse
EOF
apt_update

log_section "Configure Python package mirrors"
log_info "Using PyPI mirror: $PYPI_MIRROR"
"${ROOT_PREFIX[@]}" mkdir -p /etc
"${ROOT_PREFIX[@]}" tee /etc/pip.conf >/dev/null <<EOF
[global]
index-url = ${PYPI_MIRROR}
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
retries = 5
root-user-action = ignore
EOF

log_section "Configure shell environment defaults"
log_info "Writing /etc/profile.d/sandbox-environment.sh"
"${ROOT_PREFIX[@]}" tee /etc/profile.d/sandbox-environment.sh >/dev/null <<EOF
export PIP_INDEX_URL="${PYPI_MIRROR}"
export PIP_TIMEOUT="120"
export PIP_RETRIES="5"
export PIP_ROOT_USER_ACTION="ignore"
export UV_DEFAULT_INDEX="${PYPI_MIRROR}"
export UV_INDEX_URL="${PYPI_MIRROR}"
export npm_config_registry="${NPM_MIRROR}"
export NPM_CONFIG_REGISTRY="${NPM_MIRROR}"
export CRAN_MIRROR="${CRAN_MIRROR}"
export R_CRAN_MIRROR="${CRAN_MIRROR}"
export BIOC_MIRROR="${BIOC_MIRROR}"
export R_BIOC_MIRROR="${BIOC_MIRROR}"
export BIOCONDUCTOR_ONLINE_VERSION_DIAGNOSIS="FALSE"
export R_REMOTES_NO_ERRORS_FROM_WARNINGS="true"
export PYTHONUNBUFFERED="1"
export MAKEFLAGS="-j${R_NCPUS}"
EOF

log_section "Configure npm mirror"
if command -v npm >/dev/null 2>&1; then
  log_info "Using npm mirror: $NPM_MIRROR"
  npm config set registry "$NPM_MIRROR"
  if [ "${EUID}" -eq 0 ]; then
    npm config set --location=global registry "$NPM_MIRROR" || true
  fi
else
  log_warn "npm not found; 6_install_cli_latex.sh can install Node.js and npm later."
fi

write_r_profile() {
  local profile_path="$1"
  "${ROOT_PREFIX[@]}" mkdir -p "$(dirname "$profile_path")"
  "${ROOT_PREFIX[@]}" tee "$profile_path" >/dev/null <<EOF

options(repos = c(CRAN = "${CRAN_MIRROR}"))
options(BioC_mirror = "${BIOC_MIRROR}")
options(Ncpus = ${R_NCPUS})
options(timeout = 600)
EOF
}

log_section "Configure R defaults"
log_info "Using CRAN mirror: $CRAN_MIRROR"
log_info "Using Bioconductor mirror: $BIOC_MIRROR"
write_r_profile /etc/R/Rprofile.site
if command -v R >/dev/null 2>&1; then
  r_home="$(R RHOME)"
  write_r_profile "${r_home}/etc/Rprofile.site"
else
  log_warn "R is not installed yet; run 1_install_base_environment.sh before installing R packages."
fi

log_done "Configuration complete."
