#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
root=$(pwd)
if [[ "$root" == *' '* || "$root" == *'%'* ]]; then echo 'Use a project path without spaces or percent signs.'; exit 1; fi
if [[ ! -x .venv/bin/python ]]; then echo 'Run install-pi.sh first.'; exit 1; fi
sudo tee /etc/systemd/system/thermal-pi.service >/dev/null <<UNIT
[Unit]
Description=Thermal P1 camera service
After=network.target
[Service]
Type=simple
User=$(id -un)
SupplementaryGroups=thermal
WorkingDirectory=$root
ExecStart=$root/.venv/bin/python -m thermal_pi.server
Restart=on-failure
RestartSec=3
TimeoutStopSec=10
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now thermal-pi.service
sudo systemctl --no-pager status thermal-pi.service
