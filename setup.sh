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

echo "Installing weekly yt-dlp auto-update timer…"
cp /home/raziel/yt-dlp-update.service /etc/systemd/system/yt-dlp-update.service
cp /home/raziel/yt-dlp-update.timer /etc/systemd/system/yt-dlp-update.timer
systemctl daemon-reload
systemctl enable --now yt-dlp-update.timer

echo "(Optional) Install deno JS runtime for robust yt-dlp YouTube extraction:"
echo "  curl -fsSL https://deno.land/install.sh | sudo DENO_INSTALL=/usr/local sh"

echo "=== Done! ==="
echo "Check status: systemctl status red-alert"
echo "View logs:    journalctl -u red-alert -f"
