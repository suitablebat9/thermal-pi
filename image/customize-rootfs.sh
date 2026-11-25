#!/bin/bash
# Executed as root inside the mounted ARM64 Armbian root filesystem.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-venv python3-numpy python3-pil python3-flask python3-usb libusb-1.0-0 usbutils git avahi-daemon libnss-mdns openssh-server network-manager systemd-resolved
python3 -m venv --system-site-packages /opt/thermal-pi/.venv
groupadd -f thermal
id thermal-camera >/dev/null 2>&1 || useradd --system --gid thermal --home-dir /var/lib/thermal-pi --create-home --shell /usr/sbin/nologin thermal-camera
cat > /etc/udev/rules.d/70-thermal-p1.rules <<'RULE'
SUBSYSTEM=="usb", ATTR{idVendor}=="3474", ATTR{idProduct}=="45c2", GROUP="thermal", MODE="0660"
RULE
cat > /etc/systemd/system/thermal-pi.service <<'UNIT'
[Unit]
Description=Thermal P1 camera service
After=network.target
[Service]
Type=simple
User=thermal-camera
SupplementaryGroups=thermal
WorkingDirectory=/opt/thermal-pi
ExecStart=/opt/thermal-pi/.venv/bin/python -m thermal_pi.server --config /var/lib/thermal-pi/settings.json
Restart=on-failure
RestartSec=3
TimeoutStopSec=10
[Install]
WantedBy=multi-user.target
UNIT
systemctl enable thermal-pi avahi-daemon ssh NetworkManager systemd-resolved
mkdir -p /etc/NetworkManager/conf.d
printf '[main]\ndns=systemd-resolved\n' > /etc/NetworkManager/conf.d/thermal-dns.conf
ln -sfn /opt/thermal-pi /etc/skel/thermal-pi
ln -sfn /opt/thermal-pi /root/thermal-pi
ln -sfn /opt/thermal-pi/scripts/thermal /usr/local/bin/thermal
chmod +x /opt/thermal-pi/scripts/thermal
# Give normal first-login users access to the same path the Mac launcher uses.
cat > /etc/profile.d/thermal-pi.sh <<'PROFILE'
if [ -n "${HOME:-}" ] && [ ! -e "$HOME/thermal-pi" ] && [ -w "$HOME" ]; then
    ln -s /opt/thermal-pi "$HOME/thermal-pi"
fi
PROFILE
printf 'thermal-orange\n' > /etc/hostname
sed -i 's/127\.0\.1\.1.*/127.0.1.1 thermal-orange/' /etc/hosts
apt-get clean
# Each flashed board gets its own machine identity and SSH host keys.
rm -f /etc/ssh/ssh_host_*
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id
cat > /etc/systemd/system/thermal-hostkeys.service <<'UNIT'
[Unit]
Description=Generate unique SSH host keys on first boot
Before=ssh.service
ConditionPathExists=!/etc/ssh/ssh_host_ed25519_key
[Service]
Type=oneshot
ExecStart=/usr/bin/ssh-keygen -A
[Install]
WantedBy=multi-user.target
UNIT
systemctl enable thermal-hostkeys
cd /opt/thermal-pi
.venv/bin/python -c 'import numpy, PIL, flask, usb; from thermal_pi.server import create_app'
