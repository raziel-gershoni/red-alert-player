#!/usr/bin/env bash
set -euo pipefail

echo "=== Red Alert Player — Setup ==="

echo "Installing rpi_ws281x…"
pip3 install rpi_ws281x --break-system-packages

echo "Installing systemd service…"
cp /home/raziel/red-alert.service /etc/systemd/system/red-alert.service
systemctl daemon-reload
systemctl enable red-alert.service
systemctl start red-alert.service

echo "=== Done! ==="
echo "Check status: systemctl status red-alert"
echo "View logs:    journalctl -u red-alert -f"
