#!/usr/bin/env bash
set -e
set -o pipefail

# One-command installer for wifi_dcs
# Installs system tools (nmap, arp-scan, fping) and Python deps (psutil, Flask)
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/AROMAL642/wifi_dcs/main/install.sh | bash
# or after cloning:
#   bash install.sh

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info() { echo "[INFO] $*"; }
success() { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

# Detect package manager (Debian/Ubuntu preferred)
PKG=""
if command -v apt-get >/dev/null 2>&1; then
  PKG="apt-get"
elif command -v apt >/dev/null 2>&1; then
  PKG="apt"i

if [[ -z "$PKG" ]]; then
  warn "No apt/apt-get detected. Please install nmap, arp-scan, fping manually via your package manager. Continuing with Python deps only."
else
  info "Installing system packages (root/sudo required): nmap, arp-scan, fping"
  if command -v sudo >/dev/null 2>&1; then
    sudo $PKG update -y
    sudo $PKG install -y nmap arp-scan fping
  else
    $PKG update -y
    $PKG install -y nmap arp-scan fping
  fi
  success "System tools installed (or already present)."
fi

# Install Python deps
need_cmd python3
if ! command -v pip >/dev/null 2>&1 && ! command -v pip3 >/dev/null 2>&1; then
  fail "pip/pip3 not found. Install python3-pip first."
fi
PIP="pip3"
command -v pip3 >/dev/null 2>&1 || PIP="pip"

info "Installing Python dependencies from requirements..."
$PIP install --upgrade pip
$PIP install -r "$REPO_DIR/module1_discovery/requirements.txt"
$PIP install -r "$REPO_DIR/module4_ui/requirements.txt"
success "Python deps installed."

info "Done. You can now run workers/masters/UI per the README."
