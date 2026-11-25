#!/bin/bash
# Run on the Mac. The destination should be root@the-board-IP.
set -euo pipefail
if [ "$#" -ne 1 ] || [[ "$1" != root@* ]] || [[ "$1" =~ [[:space:]] ]]; then
 echo "Usage: bash $0 root@YOUR_PI_IP"; exit 1
fi
folder=$(cd "$(dirname "$0")" && pwd)
archive="$folder/thermal-pi-offline-debian13-arm64.tar.gz"
[ -f "$archive" ] || { echo "Bundle not found: $archive"; exit 1; }
scp "$archive" "$1:/root/thermal-pi-offline-debian13-arm64.tar.gz"
ssh -t "$1" 'mkdir -p /root/thermal-offline && tar -xzf /root/thermal-pi-offline-debian13-arm64.tar.gz -C /root/thermal-offline && bash /root/thermal-offline/bundle/install.sh'
