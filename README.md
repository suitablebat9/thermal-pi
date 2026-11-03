# Thermal Pi — P1 bench-test viewer

A headless Thermal Master P1 service for Raspberry Pi OS Lite 64-bit, a persistent numbered SSH control menu, and a clean Mac browser viewer. First version: **hardware testing on the Pi 3B+ and P1 is still required**. This is a bench prototype, not a flight-qualified video system.

## What works in this version

- Software palettes: white hot, black hot, iron, rainbow (our palettes, not exact manufacturer app replicas).
- Digital crop/zoom 1–8×, clockwise rotation, horizontal flip after rotation.
- Queued P1 shutter calibration and high/low gain via upstream driver. Only one worker owns USB access. Commands expire after two seconds; status shows completion/failure.
- Save preferences explicitly; saved gain is reapplied on camera reconnect.
- Automatic capture retry after disconnect, latest-frame-only storage, visible stale/disconnected status.
- Clearly marked synthetic demo mode. No camera required.
- Localhost-only HTTP service reached through SSH. No cloud account or internet needed during use.

No automatic gain (upstream protocol does not implement it), temperature measurements, manufacturer AI enhancement, recording, motor/gimbal control, or hotspot configuration yet. The underlying driver has temperature-related code, but this application deliberately does not present unverified temperature readings.

## 1. Flash and connect

Use Raspberry Pi Imager to install a current Raspberry Pi OS Lite **64-bit** release. Configure hostname `thermalpi`, your own username, SSH (preferably public-key authentication), and your home Wi-Fi. Do not assume the username is `pi`. Boot with a reliable power supply.

On your Mac, replace `YOUR_USER` below:

```sh
ssh YOUR_USER@thermalpi.local
```

If `.local` does not resolve, use the Pi's IP address. Connect the P1 to a Pi USB-A port with a **data-capable** USB-C adapter/cable.

## 2. Install on the Pi

Obtain this repository in `~/thermal-pi` (clone it from GitHub, or copy the extracted folder from your Mac with `scp -r thermal-pi YOUR_USER@thermalpi.local:~/`). Then, on the Pi:

```sh
cd ~/thermal-pi
bash scripts/install-pi.sh
exit
```

Log back in and unplug/replug the camera. Installation creates a virtual environment using Raspberry Pi OS packages, a narrowly scoped USB rule for P1 `3474:45c2`, and a `thermal` group. Internet is needed for initial package installation. No full desktop or virtual webcam kernel module is required.

## 3. First camera test

In one SSH terminal on the Pi:

```sh
cd ~/thermal-pi
.venv/bin/python -m thermal_pi.server
```

This foreground process stops when that session ends; use the boot service below for persistent operation. For a camera-free test, add `--demo`.

In a **second terminal on your Mac**, establish the viewer tunnel and SSH session:

```sh
ssh -o ExitOnForwardFailure=yes -L 8080:127.0.0.1:8080 YOUR_USER@thermalpi.local
```

Within that SSH session, run:

```sh
cd ~/thermal-pi
.venv/bin/python -m thermal_pi.menu
```

Open **http://127.0.0.1:8080** in your Mac browser. The tunnel must remain open. Press Fullscreen for an image-only view; status appears if the feed becomes stale. The menu stays open: type a number, then Enter. `s` saves settings, Enter refreshes status, `0` exits just the menu. A queued hardware command is not yet confirmed: press Enter to inspect completion.

If Mac port 8080 is occupied, use `-L 8081:127.0.0.1:8080` and browse to port 8081. The menu on the Pi still uses port 8080.

The raw MJPEG feed is `/stream.mjpg`; external players using it must implement their own stale-frame indication. The included browser checks health every 500 ms and hides images after a two-second capture gap. Demo images are marked in the image itself.

## 4. Start automatically at boot

Stop the foreground server with Ctrl-C before enabling the service:

```sh
cd ~/thermal-pi
bash scripts/enable-service.sh
```

After this, you only establish the SSH tunnel and run the menu. Closing the menu or SSH connection does not stop the boot service.

```sh
sudo systemctl status thermal-pi --no-pager
journalctl -u thermal-pi -n 60 --no-pager
sudo systemctl restart thermal-pi
sudo systemctl disable --now thermal-pi
```

The service uses the repository at its installed path: do not move/delete that folder without reinstalling the service. It runs as your user, not root. Preferences live in `~/.config/thermal-pi/settings.json`. Invalid saved settings cause a startup error rather than silently changing them; rename that file to reset defaults.

## Try the demo on your Mac

From this repository, with Python 3.10+ installed:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m thermal_pi.server --demo
```

In another terminal in the same folder:

```sh
.venv/bin/python -m thermal_pi.menu
```

Open http://127.0.0.1:8080. No SSH tunnel is needed for a local Mac demo. Real camera mode is intended for Linux; Mac demo does not require libusb.

## Troubleshooting

- `lsusb` should show `3474:45c2`. A different ID needs investigation; do not blindly change the rule.
- Permission denied: reconnect camera, log out/in, and check `id` includes `thermal`.
- No camera: verify cable carries data, Pi power, USB connection, and that no other viewer owns the camera.
- Browser unavailable: keep the SSH tunnel running, check service status and local port conflicts.
- Capture errors: preserve the logs; report Pi OS version, USB ID, and symptoms. Never put SSH private keys/passwords in GitHub.
- Hardware commands are reverse-engineered upstream functions and need verification on your camera firmware. No claim of full manufacturer-app parity.

## Design and future direct connection

The Pi owns USB capture and applies display processing, then serves JPEG frames over HTTP. SSH transports this to the Mac; the terminal menu uses a small local JSON API. The server keeps only the most recent frame, although HTTP/TCP/network buffering can still introduce latency. MJPEG prioritizes a simple working prototype, not optimized radio bandwidth. Test latency and CPU usage before considering H.264/WebRTC or flight use.

Later, the Pi can host its own password-protected Wi-Fi access point so the Mac connects without a router or internet. That still uses Wi-Fi radio. Direct Ethernet is another bench option. No networking changes are made by these scripts. Range, interference, power, total payload, and thermal performance remain untested.

## Tests

```sh
.venv/bin/python -m unittest discover -s tests -v
```

See TESTING.md for current evidence and the hardware acceptance checklist.

## Upstream and license

Apache-2.0; see LICENSE and NOTICE. Only the USB driver is vendored from:
https://github.com/skywalker1905/thermal-camera-viewer

Pinned upstream commit: `512b46e7d0701c05bfecc5cb096061c5967be860`.
Vendored path: `thermal_pi/vendor/p3_camera.py`, unchanged. It derives from Joshua V. Dillon and contributors' https://github.com/jvdillon/p3-ir-camera. The Qt GUI and virtual webcam layer are not needed. Application code in the other files is new. Check upstream changes deliberately rather than silently downloading a new driver at startup.

The Pi installer uses OS-managed dependency versions for ARM compatibility. `requirements.txt` defines supported ranges for local demos; this is not a reproducible lock of every future OS package version.
