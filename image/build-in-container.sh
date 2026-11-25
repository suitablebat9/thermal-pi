#!/bin/bash
# Run in a privileged ARM64 Linux container. Operates only on regular image files.
set -euo pipefail
base=/images/build/verified-base.img.xz
out=/images/ThermalPi_Orangepizero3w_Debian13.img
expected=$(cut -d ' ' -f1 /images/build/base.img.xz.sha)
printf '%s  %s\n' "$expected" "$base" | sha256sum -c -
xz -dc "$base" > "$out"
# Verify layout before changing the root partition; preserve board bootloader.
sfdisk --json "$out" > /images/build/partition-before.json
start=$(python3 - <<'PY'
import json
p=json.load(open('/images/build/partition-before.json'))['partitiontable']
assert p['label']=='dos' and p['sectorsize']==512
assert len(p['partitions'])==1 and p['partitions'][0]['type']=='83'
print(p['partitions'][0]['start'])
PY
)
truncate -s 4G "$out"
printf '%s,,83\n' "$start" | sfdisk --no-reread -N 1 "$out"
loop=$(losetup --find --show --offset "$((start*512))" "$out")
mkdir -p /target
cleanup() {
 set +e
 for target in /target/dev/pts /target/dev /target/proc /target/sys /target; do umount "$target" 2>/dev/null; done
 losetup -d "$loop"
}
trap cleanup EXIT
set +e
e2fsck -fy "$loop"
result=$?
set -e
[ "$result" -le 1 ]
resize2fs "$loop"
mount "$loop" /target
mkdir -p /target/opt/thermal-pi
tar -xf /images/build/thermal-source.tar -C /target/opt/thermal-pi
cp /source/image/customize-rootfs.sh /target/tmp/thermal-customize.sh
cp /target/etc/resolv.conf /images/build/original-resolv.conf 2>/dev/null || true
rm -f /target/etc/resolv.conf
cp /etc/resolv.conf /target/etc/resolv.conf
mount --bind /dev /target/dev
mount -t devpts devpts /target/dev/pts
mount -t proc proc /target/proc
mount -t sysfs sysfs /target/sys
# Prevent package scripts from trying to start services in the build container.
printf '#!/bin/sh\nexit 101\n' > /target/usr/sbin/policy-rc.d
chmod +x /target/usr/sbin/policy-rc.d
chroot /target /bin/bash /tmp/thermal-customize.sh
cp /images/build/manifest.txt /target/etc/thermal-pi-image.txt
chroot /target /bin/bash -c 'cd /opt/thermal-pi && .venv/bin/python -m unittest discover -s tests -p test_app.py -v'
rm /target/tmp/thermal-customize.sh /target/usr/sbin/policy-rc.d
rm /target/etc/resolv.conf
ln -s /run/systemd/resolve/stub-resolv.conf /target/etc/resolv.conf
sync
cleanup
trap - EXIT
# Validate the final filesystem after all writes have completed.
loop=$(losetup --find --show --offset "$((start*512))" "$out")
e2fsck -fn "$loop"
losetup -d "$loop"
xz -T2 -3 -k "$out"
cd /images
sha256sum "$(basename "$out").xz" > "$(basename "$out").xz.sha256"
echo "Image completed: $out.xz"
