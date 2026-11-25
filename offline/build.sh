#!/bin/bash
# Run from this repository on a Mac/Linux machine with internet and Docker ARM64.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
out=${1:-"$HOME/thermal-pi-offline"}
mkdir -p "$out/bundle/packages"
out=$(cd "$out" && pwd)
git -C "$root" archive HEAD -o "$out/bundle/thermal-source.tar"
cp "$root/offline/install.sh" "$out/bundle/install.sh"
git -C "$root" rev-parse HEAD > "$out/bundle/SOURCE_COMMIT"
docker run --rm --platform linux/arm64 -v "$out/bundle:/bundle" debian:trixie-slim bash -euxc '
 export DEBIAN_FRONTEND=noninteractive
 apt-get update
 apt-get install -y --no-install-recommends dpkg-dev
 touch /tmp/empty-status
 mkdir -p /bundle/packages/partial
 apt-get -o Dir::State::status=/tmp/empty-status -o Dir::Cache::archives=/bundle/packages --download-only --no-install-recommends -y install python3-venv python3-numpy python3-pil python3-flask python3-usb libusb-1.0-0 usbutils avahi-daemon libnss-mdns
 cd /bundle/packages
 dpkg-scanpackages --multiversion . /dev/null > Packages
 rm -rf partial lock
 cd /bundle
 sha256sum thermal-source.tar SOURCE_COMMIT install.sh packages/Packages packages/*.deb > SHA256SUMS
'
COPYFILE_DISABLE=1 tar -czf "$out/thermal-pi-offline-debian13-arm64.tar.gz" -C "$out" bundle
shasum -a 256 "$out/thermal-pi-offline-debian13-arm64.tar.gz" > "$out/thermal-pi-offline-debian13-arm64.tar.gz.sha256"
cp "$root/offline/send.sh" "$out/install-on-pi.sh"
echo "Ready: $out/thermal-pi-offline-debian13-arm64.tar.gz"
