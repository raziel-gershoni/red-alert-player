#!/usr/bin/env bash
set -euo pipefail

echo "Stopping red-alert…"
systemctl stop red-alert.service

echo "Starting red-alert…"
systemctl start red-alert.service

echo "Tailing logs (Ctrl+C to stop)…"
journalctl -u red-alert.service -f
