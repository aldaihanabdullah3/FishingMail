#!/usr/bin/env bash
# FishingMail/install.sh [--cert CERT_PATH --key KEY_PATH]
#
# Copies app files to /opt/fishingmail, builds a venv there, and registers
# FishingMail as a systemd service that starts automatically on boot.
# Run once as root from any location.
#
# Options:
#   --cert PATH   Path to PEM certificate file (enables HTTPS on port 443)
#   --key  PATH   Path to PEM private key file (required with --cert)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/fishingmail"
SERVICE_FILE="/etc/systemd/system/fishingmail.service"
ENV_FILE="/etc/fishingmail/fishingmail.conf"

# ── Argument parsing ──────────────────────────────────────────────────────────
TLS_CERT=""
TLS_KEY=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --cert) TLS_CERT="$2"; shift 2 ;;
        --key)  TLS_KEY="$2";  shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

[[ $EUID -eq 0 ]] || { echo "Run as root" >&2; exit 1; }

echo "=== FishingMail install ==="
echo "  source  : $SCRIPT_DIR"
echo "  target  : $INSTALL_DIR"

# ── System packages ──────────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv

# ── Copy app files to /opt/fishingmail ───────────────────────────────────────
mkdir -p "$INSTALL_DIR"
find "$SCRIPT_DIR" -mindepth 1 -maxdepth 1 \
    ! -name 'venv' \
    ! -name 'fishmail.db' \
    ! -name '__pycache__' \
    ! -name '.git' \
    -exec cp -r {} "$INSTALL_DIR/" \;

# ── Python venv + app dependencies ───────────────────────────────────────────
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

# ── TLS certificate handling ──────────────────────────────────────────────────
FISHMAIL_PORT=80
if [[ -n "$TLS_CERT" || -n "$TLS_KEY" ]]; then
    if [[ ! -f "$TLS_CERT" ]]; then
        echo "error: cert not found at '$TLS_CERT'" >&2; exit 1
    fi
    if [[ ! -f "$TLS_KEY" ]]; then
        echo "error: key not found at '$TLS_KEY'" >&2; exit 1
    fi
    mkdir -p /etc/fishingmail/certs
    mv "$TLS_CERT" /etc/fishingmail/certs/cert.pem
    mv "$TLS_KEY"  /etc/fishingmail/certs/key.pem
    chmod 600 /etc/fishingmail/certs/key.pem
    TLS_CERT=/etc/fishingmail/certs/cert.pem
    TLS_KEY=/etc/fishingmail/certs/key.pem
    FISHMAIL_PORT=443
    echo "  certs   : moved to /etc/fishingmail/certs/"
fi

# ── Runtime configuration — edit this file to tune the server ────────────────
# Only write defaults if the file doesn't already exist, so re-running
# install.sh after an upgrade doesn't clobber operator customisations.
mkdir -p /etc/fishingmail
mkdir -p /var/log/fishingmail
if [[ ! -f "$ENV_FILE" ]]; then
    {
        echo "# FishingMail service configuration"
        echo "# Edit then run: systemctl restart fishingmail"
        echo ""
        echo "FISHMAIL_PORT=$FISHMAIL_PORT"
        echo "FISHMAIL_HOST=0.0.0.0"
        echo "FISHMAIL_RECIPIENT=j.anderson@meridian-corp.home"
        echo "FISHMAIL_INTERVAL_MIN=60"
        echo "FISHMAIL_INTERVAL_MAX=180"
        echo "FISHMAIL_SEED_EMAILS=8"
        echo ""
        if [[ -n "$TLS_CERT" ]]; then
            echo "FISHMAIL_TLS_CERT=$TLS_CERT"
            echo "FISHMAIL_TLS_KEY=$TLS_KEY"
        else
            echo "# Uncomment and set both to enable HTTPS"
            echo "#FISHMAIL_TLS_CERT=/etc/fishingmail/certs/cert.pem"
            echo "#FISHMAIL_TLS_KEY=/etc/fishingmail/certs/key.pem"
        fi
    } > "$ENV_FILE"
    echo "  config  : $ENV_FILE (written)"
else
    echo "  config  : $ENV_FILE (existing file preserved)"
fi

# ── systemd service unit ──────────────────────────────────────────────────────
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=FishingMail Phishing Simulation Server
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/fishingmail/fishingmail.log
StandardError=append:/var/log/fishingmail/fishingmail.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fishingmail.service
systemctl restart fishingmail.service

echo ""
echo "=== FishingMail install complete ==="
echo "  installed: $INSTALL_DIR"
echo "  config  : $ENV_FILE"
echo "  service : fishingmail.service (enabled, running)"
echo ""
echo "  Manage:"
echo "    systemctl status fishingmail"
echo "    systemctl stop|start|restart fishingmail"
echo "    journalctl -fu fishingmail"
echo "    tail -f /var/log/fishingmail/fishingmail.log"
echo ""
echo "  To reconfigure: edit $ENV_FILE then restart the service"
