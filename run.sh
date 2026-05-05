#!/usr/bin/env bash
# FishingMail/run.sh [port]
# Starts the FishingMail Flask server. Default port: 80.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FISHMAIL_PORT="${1:-80}" \
FISHMAIL_HOST="0.0.0.0" \
  "$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/app.py" 2>&1 | tee /fishmail.log
