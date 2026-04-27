#!/usr/bin/env bash
set -euo pipefail

# Clean caches and temporary files after building the sandbox image.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
. "${SCRIPT_DIR}/_common.sh"

require_root_prefix

log_section "Clean apt caches"
"${ROOT_PREFIX[@]}" apt-get autoremove -y --purge || true
"${ROOT_PREFIX[@]}" apt-get clean || true
"${ROOT_PREFIX[@]}" rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb

log_section "Clean Python, uv, npm, and R caches"
rm -rf \
  "${HOME}/.cache/pip" \
  "${HOME}/.cache/uv" \
  "${HOME}/.npm" \
  "${HOME}/.cache/R" \
  "${HOME}/.local/share/Trash" \
  /tmp/* \
  /var/tmp/* \
  2>/dev/null || true

if command -v pip >/dev/null 2>&1; then
  pip cache purge >/dev/null 2>&1 || true
fi

if command -v uv >/dev/null 2>&1; then
  uv cache clean >/dev/null 2>&1 || true
fi

if command -v npm >/dev/null 2>&1; then
  npm cache clean --force >/dev/null 2>&1 || true
fi

"${ROOT_PREFIX[@]}" rm -rf \
  /root/.cache/pip \
  /root/.cache/uv \
  /root/.npm \
  /root/.cache/R \
  /usr/local/share/.cache \
  /var/cache/fontconfig/* \
  2>/dev/null || true

log_section "Remove Python bytecode caches"
"${ROOT_PREFIX[@]}" find /usr /opt /home -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
"${ROOT_PREFIX[@]}" find /usr /opt /home -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

log_section "Remove package-manager logs"
"${ROOT_PREFIX[@]}" rm -rf /var/log/apt/* /var/log/dpkg.log /var/log/alternatives.log 2>/dev/null || true

log_done "Environment cleanup complete."
