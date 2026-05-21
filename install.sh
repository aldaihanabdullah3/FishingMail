#!/usr/bin/env bash
# FishingMail/install.sh
# Copies app files to /opt/fishingmail, builds a venv there, and registers
# FishingMail as a systemd service that starts automatically on boot.
# Run once as root from any location.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/fishingmail"
SERVICE_FILE="/etc/systemd/system/fishingmail.service"
ENV_FILE="/etc/fishingmail/fishingmail.conf"

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

# ── TLS certificate prompt ───────────────────────────────────────────────────
TLS_CERT=""
TLS_KEY=""
FISHMAIL_PORT=80

echo ""
read -r -p "TLS certificate path (leave blank to skip HTTPS): " TLS_CERT
if [[ -n "$TLS_CERT" ]]; then
    read -r -p "TLS key path: " TLS_KEY
    if [[ ! -f "$TLS_CERT" ]]; then
        echo "  warning : cert not found at '$TLS_CERT' — falling back to HTTP on port 80" >&2
        TLS_CERT=""
        TLS_KEY=""
    elif [[ ! -f "$TLS_KEY" ]]; then
        echo "  warning : key not found at '$TLS_KEY' — falling back to HTTP on port 80" >&2
        TLS_CERT=""
        TLS_KEY=""
    else
        mkdir -p /etc/fishingmail/certs
        mv "$TLS_CERT" /etc/fishingmail/certs/cert.pem
        mv "$TLS_KEY"  /etc/fishingmail/certs/key.pem
        chmod 600 /etc/fishingmail/certs/key.pem
        TLS_CERT=/etc/fishingmail/certs/cert.pem
        TLS_KEY=/etc/fishingmail/certs/key.pem
        FISHMAIL_PORT=443
        echo "  certs   : copied to /etc/fishingmail/certs/"
    fi
fi
echo ""

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
