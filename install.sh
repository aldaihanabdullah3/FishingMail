#!/usr/bin/env bash
# FishingMail/install.sh
# Installs Python deps for the Flask mail server into this directory.
# Run once as root after files have been pushed to the container.
# No paths are hardcoded — everything lands next to this script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[[ $EUID -eq 0 ]] || { echo "Run as root" >&2; exit 1; }

echo "=== FishingMail install (dir: $SCRIPT_DIR) ==="

# ── System packages ──────────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv

# ── Python venv + app dependencies — installed next to the app ───────────────
python3 -m venv "$SCRIPT_DIR/venv"
"$SCRIPT_DIR/venv/bin/pip" install --quiet --upgrade pip
"$SCRIPT_DIR/venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "=== FishingMail install complete ==="
echo "  python : $SCRIPT_DIR/venv/bin/python"
echo "  dir    : $SCRIPT_DIR"
