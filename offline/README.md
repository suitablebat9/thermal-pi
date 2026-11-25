# Offline install on standard Armbian Debian 13 ARM64

This is an installation bundle for a **normal OS image**, not a disk image.
The Mac downloads the software and Debian packages. The Orange Pi only needs
an SSH connection to the Mac, for example through Ethernet; it needs no internet.

Build on a Mac with internet and a running Docker ARM64 engine:

```sh
bash offline/build.sh
```

The default output is `~/thermal-pi-offline/thermal-pi-offline-debian13-arm64.tar.gz`.
It contains an application source snapshot, required Debian packages including
their dependency closure, a local apt repository and a checksum manifest.
Debian package versions reflect the Debian 13 repositories at build time.

On the Mac, substitute the board's actual IP address:

```sh
PI=root@YOUR_PI_IP
scp ~/thermal-pi-offline/thermal-pi-offline-debian13-arm64.tar.gz "$PI:/root/"
ssh -t "$PI" 'mkdir -p /root/thermal-offline && tar -xzf /root/thermal-pi-offline-debian13-arm64.tar.gz -C /root/thermal-offline && bash /root/thermal-offline/bundle/install.sh'
```

The installer checks Debian 13 and ARM64, verifies all files and uses only its
local package repository. It may upgrade Debian libraries to satisfy packaged
dependencies. Existing Armbian repositories are not changed. It refuses to
replace `/root/thermal-pi` if that directory already exists.

It installs the app in `/root/thermal-pi`, creates its Python environment and
camera permissions, enables `thermal-pi.service` and enables Avahi for local
hostname discovery. This setup follows the root login the board currently uses.
Reconnect the camera after installation. The app is a source snapshot without a
`.git` directory; future updates require another bundle or a separate checkout.

On the Mac run `thermal-pi --setup`, use `root@YOUR_PI_IP`, leave the SSH port
blank and select real-camera mode. Then run `thermal-pi` normally.

Validation runs package installation with Docker networking disabled and checks
the app against the installed ARM64 Python libraries. Real USB access and systemd
service startup must be confirmed on the physical board.
