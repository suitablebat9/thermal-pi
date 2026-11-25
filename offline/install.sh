#!/bin/bash
# Install from the local package repository only. Run as root on the Orange Pi.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Run as root (sudo bash install.sh).'; exit 1; }
. /etc/os-release
[ "$ID" = debian ] && [ "${VERSION_ID:-}" = 13 ] && [ "$(dpkg --print-architecture)" = arm64 ] || {
 echo 'This bundle requires Debian 13 (Trixie), ARM64.'; exit 1;
}
if [ -e /root/thermal-pi ]; then
 echo '/root/thermal-pi already exists. Move it aside before installing this snapshot.'
 exit 1
fi
source_dir=$(cd "$(dirname "$0")" && pwd)
cd "$source_dir"
sha256sum -c SHA256SUMS
# Put packages where the unprivileged apt reader can access them.
repo=$(mktemp -d /var/tmp/thermal-offline.XXXXXX)
trap 'rm -rf "$repo"' EXIT
chmod 755 "$repo"
cp -a packages/. "$repo/"
chmod -R a+rX "$repo"
printf 'deb [trusted=yes] file:%s ./\n' "$repo" > "$repo/local.list"
mkdir -p "$repo/lists/partial"
opts=(-o "Dir::Etc::sourcelist=$repo/local.list" -o Dir::Etc::sourceparts=-
      -o "Dir::State::lists=$repo/lists" -o Acquire::Languages=none)
export DEBIAN_FRONTEND=noninteractive
apt-get "${opts[@]}" update
apt-get "${opts[@]}" --no-install-recommends -y install python3-venv python3-numpy python3-pil python3-flask python3-usb libusb-1.0-0 usbutils avahi-daemon libnss-mdns
# Keep an existing checkout/settings if the installer is run a second time.
mkdir /root/thermal-pi
tar -xf thermal-source.tar -C /root/thermal-pi
cd /root/thermal-pi
python3 -m venv --system-site-packages .venv
groupadd -f thermal
usermod -aG thermal root
printf '%s\n' 'SUBSYSTEM=="usb", ATTR{idVendor}=="3474", ATTR{idProduct}=="45c2", GROUP="thermal", MODE="0660"' > /etc/udev/rules.d/70-thermal-p1.rules
udevadm control --reload-rules
udevadm trigger --subsystem-match=usb
chmod +x scripts/thermal
ln -sfn /root/thermal-pi/scripts/thermal /usr/local/bin/thermal
.venv/bin/python -c 'import numpy, PIL, flask, usb; from thermal_pi.server import create_app'
cat > /etc/systemd/system/thermal-pi.service <<'UNIT'
[Unit]
Description=Thermal P1 camera service
After=network.target
[Service]
Type=simple
User=root
SupplementaryGroups=thermal
WorkingDirectory=/root/thermal-pi
ExecStart=/root/thermal-pi/.venv/bin/python -m thermal_pi.server
Restart=on-failure
RestartSec=3
TimeoutStopSec=10
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now thermal-pi
systemctl --no-pager status thermal-pi
systemctl enable --now avahi-daemon
echo 'Installed offline. Reconnect the camera. Use the Mac launcher with root@YOUR_PI_IP.'
