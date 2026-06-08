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

echo "Installing deno JS runtime (helps yt-dlp solve YouTube JS challenges)…"
npm install -g deno || echo "  (deno install skipped — install manually if YouTube extraction degrades)"

echo "=== Done! ==="
echo "Check status: systemctl status red-alert"
echo "View logs:    journalctl -u red-alert -f"
