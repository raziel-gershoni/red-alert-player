#!/bin/bash
# Follow red-alert service logs (Ctrl+C to stop)
sudo journalctl -u red-alert -f
