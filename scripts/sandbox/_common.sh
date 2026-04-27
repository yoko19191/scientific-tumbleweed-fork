#!/usr/bin/env bash

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  COLOR_BLUE=$'\033[1;34m'
  COLOR_GREEN=$'\033[1;32m'
  COLOR_YELLOW=$'\033[1;33m'
  COLOR_RED=$'\033[1;31m'
  COLOR_DIM=$'\033[2m'
  COLOR_RESET=$'\033[0m'
else
  COLOR_BLUE=""
  COLOR_GREEN=""
  COLOR_YELLOW=""
  COLOR_RED=""
  COLOR_DIM=""
  COLOR_RESET=""
fi

SANDBOX_SEPARATOR="============================================================"
SANDBOX_SUBSEPARATOR="------------------------------------------------------------"

log_section() {
  printf "\n%s%s%s\n" "$COLOR_BLUE" "$SANDBOX_SEPARATOR" "$COLOR_RESET"
  printf "%s>> %s%s\n" "$COLOR_BLUE" "$1" "$COLOR_RESET"
  printf "%s%s%s\n" "$COLOR_BLUE" "$SANDBOX_SEPARATOR" "$COLOR_RESET"
}

log_subsection() {
  printf "\n%s-- %s --%s\n" "$COLOR_BLUE" "$1" "$COLOR_RESET"
  printf "%s%s%s\n" "$COLOR_DIM" "$SANDBOX_SUBSEPARATOR" "$COLOR_RESET"
}

log_info() {
  printf "%s[INFO]%s %s\n" "$COLOR_BLUE" "$COLOR_RESET" "$1"
}

log_warn() {
  printf "%s[WARN]%s %s\n" "$COLOR_YELLOW" "$COLOR_RESET" "$1"
}

log_error() {
  printf "%s[ERROR]%s %s\n" "$COLOR_RED" "$COLOR_RESET" "$1" >&2
}

log_done() {
  printf "%s[DONE]%s %s\n" "$COLOR_GREEN" "$COLOR_RESET" "$1"
}

require_root_prefix() {
  ROOT_PREFIX=()
  if [ "${EUID}" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
      ROOT_PREFIX=(sudo)
    else
      log_error "This script needs root privileges. Re-run as root or install sudo."
      exit 1
    fi
  fi
}

apt_update() {
  log_subsection "Update apt metadata"
  "${ROOT_PREFIX[@]}" apt-get update
}

apt_install_required() {
  local label="$1"
  shift

  log_subsection "$label"
  "${ROOT_PREFIX[@]}" apt-get install -y --no-install-recommends "$@"
}

apt_install_optional() {
  local label="$1"
  shift
  local package
  local installable_packages=()

  log_subsection "$label"
  for package in "$@"; do
    if apt-cache show "$package" >/dev/null 2>&1; then
      installable_packages+=("$package")
      log_info "Optional apt package is available: $package"
    else
      log_warn "Optional apt package is unavailable and will be skipped: $package"
    fi
  done

  if [ "${#installable_packages[@]}" -gt 0 ]; then
    "${ROOT_PREFIX[@]}" apt-get install -y --no-install-recommends "${installable_packages[@]}"
  else
    log_warn "No optional apt packages are available for this section."
  fi
}

ensure_command() {
  local command_name="$1"
  local install_hint="${2:-}"

  if command -v "$command_name" >/dev/null 2>&1; then
    log_info "$command_name is available: $(command -v "$command_name")"
    return 0
  fi

  if [ -n "$install_hint" ]; then
    log_error "$command_name is not available. Install hint: $install_hint"
  else
    log_error "$command_name is not available."
  fi
  return 1
}
