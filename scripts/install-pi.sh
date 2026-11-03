#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $(uname -s) != Linux ]]; then echo 'Run this on the Raspberry Pi.'; exit 1; fi
sudo apt-get update
sudo apt-get install -y python3-venv python3-numpy python3-pil python3-flask python3-usb libusb-1.0-0 usbutils
python3 -m venv --system-site-packages .venv
sudo groupadd -f thermal
sudo usermod -aG thermal "$(id -un)"
printf '%s\n' 'SUBSYSTEM=="usb", ATTR{idVendor}=="3474", ATTR{idProduct}=="45c2", GROUP="thermal", MODE="0660"' | sudo tee /etc/udev/rules.d/70-thermal-p1.rules >/dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=usb
chmod +x scripts/thermal
sudo ln -sfn "$PWD/scripts/thermal" /usr/local/bin/thermal
echo 'Installed. Log out and back in for USB permissions; reconnect the camera.'
echo 'Then run: thermal (or thermal --demo without a camera)'
