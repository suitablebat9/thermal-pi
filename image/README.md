# Thermal Pi image for Orange Pi Zero 3W

This is a custom derivative of the stable Armbian 26.8.1 Debian 13 Minimal
image, vendor kernel 6.6.98, for **Orange Pi Zero 3W only**.
It preserves the base bootloader and installs the thermal app and Python/USB
packages before flashing. No internet download is needed to install the thermal
app after boot. Wi-Fi and account setup are still required.

## Flash and first boot

1. Open Armbian Imager, choose a local/custom image and select
   `ThermalPi_Orangepizero3w_Debian13.img.xz`.
2. Select the SD card, flash and allow verification to complete.
3. Boot the Zero 3W with reliable power. Complete Armbian's standard first-login
   account setup. For an initial headless connection, use wired Ethernet if your
   board/adapter supports it; otherwise use a monitor/keyboard or serial console
   to configure Wi-Fi. This generic image contains no Wi-Fi passwords or personal
   account credentials. It retains Armbian's first-login flow.
4. To join Wi-Fi from a local terminal, run `sudo nmtui`, choose Activate a
   connection, and select the network. Confirm it has an address with `ip -br a`.
5. Plug in the P1 camera. The `thermal-pi` service starts automatically.
6. On the Mac run `thermal-pi --setup`, enter
   `YOUR_USERNAME@thermal-orange.local` (or the board's IP), leave the SSH port
   blank and choose real-camera mode. Then use `thermal-pi` as usual.

Armbian's first-login process may change the hostname; if the name doesn't
resolve, use the actual IP and check `hostname` on the board.

## Image layout

- App snapshot and virtual environment: `/opt/thermal-pi`
- Compatibility symlink: `~/thermal-pi` for newly created/login users
- Dedicated service account: `thermal-camera` (no interactive login)
- Persistent settings: `/var/lib/thermal-pi/settings.json`
- Service: `thermal-pi.service`, localhost port 8080
- Local hostname: `thermal-orange.local` via Avahi
- Software provenance: `/etc/thermal-pi-image.txt`
- SSH host keys and machine identity are generated separately on each board.

Check status with `systemctl status thermal-pi --no-pager` and logs with
`journalctl -u thermal-pi -n 50 --no-pager`. Confirm the USB camera with `lsusb`.
The app is a source snapshot, so `git pull` does not update this image's app.
A newer image can be built from a newer source snapshot. Do not run the standard
Pi installer over this layout without accounting for the service account and
settings paths.

## Build record and reproduction

The local build uses an ARM64 privileged Linux Docker container on the Mac.
`build-in-container.sh` only edits regular disk-image files, never an SD card.
Docker's privileged access is used to attach a loop device and mount the image.
The build expands the partition/filesystem to 4 GiB; Armbian's normal first-boot
resize support is retained for larger SD cards.

Inputs in `/images/build`:

- `verified-base.img.xz`: official stable base image
- `base.img.xz.sha`: official SHA256 checksum
- `thermal-source.tar`: `git archive HEAD` of the selected thermal-pi commit
- `manifest.txt`: base version/hash, source revision and build timestamp

Mount the source checkout read-only as `/source`, an output directory as
`/images`, and run `bash /source/image/build-in-container.sh` inside an ARM64
Debian container with `fdisk`, `e2fsprogs`, `xz-utils`, `ca-certificates` and
`python3` installed. The script verifies the download, requires exactly one
Linux MBR partition, preserves its starting offset, installs dependencies in a
chroot, enables services and runs application tests. A final read-only filesystem
check precedes compression. Output includes `.img.xz` and a SHA256 sidecar.
Build package installation needs internet. Debian package versions are not locked,
so later builds can differ even when the app and base image are identical.

Sources:
- https://armbian.com/boards/orangepizero3w
- https://docs.armbian.com/getting-started/writing-the-image/

This build has not been boot-tested on a physical Orange Pi Zero 3W. Chroot and
filesystem checks cannot establish Wi-Fi, bootloader or USB-camera reliability.
