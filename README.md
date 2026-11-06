# Thermal Pi — P1 bench-test viewer

A headless Thermal Master P1 service for Raspberry Pi OS Lite 64-bit, a persistent numbered SSH control menu, and a clean Mac browser viewer. First version: **hardware testing on the Pi 3B+ and P1 is still required**. This is a bench prototype, not a flight-qualified video system.

## One command on your Mac

Type `thermal-pi` in Mac Terminal. On first use, enter your usual Pi SSH address, SSH port, and camera mode. The Mac remembers those choices. The numbered controls open first. Press **v** to open the video window. You can close the window and use **v** again. Press **0** on the main screen to end the session. Run `thermal-pi --setup` when you move from the emulator to the physical Pi.

On another Mac, install the shortcut from your Mac checkout by linking `scripts/thermal-view` to a directory on your PATH. For example, with Homebrew:

```sh
ln -s "$PWD/scripts/thermal-view" "$(brew --prefix)/bin/thermal-pi"
```

The Pi needs the version containing `thermal_pi.window_session`. If you installed an earlier version, run `cd ~/thermal-pi && git pull --ff-only` on the Pi once.

## Field link testing

On a Mac that already has the launcher, install its optional image dependencies once from the checkout with `bash scripts/install-mac-field.sh`. Update the Pi checkout and restart any active boot service first. Run `thermal-pi --field`, connect normally, and press **v**. Field mode defaults to the P1’s 25 fps target and JPEG quality 85, matching the normal camera encoder. Demo playback defaults to 4 fps. Display frames pass from the Mac receiver to its local player without a second JPEG encode. An alternative for a struggling link is `thermal-pi --field --fps 4 --quality 45`. Adjust fps from 1–25 and quality from 25–90. The original `thermal-pi` command still uses its previous stream format.

The Pi sends a native-size JPEG (160×120 before crop/rotation) and a small header with the readings and marker positions. The Mac enlarges it and draws the scale and labels. Monochrome palettes use a one-channel JPEG when the green overlay is off. Each request picks up the newest frame, skips a duplicate, and allows only one outstanding request. A slow link lowers delivered frame rate. Every five seconds the menu reports delivered fps and video payload kb/s, excluding SSH, network headers and retransmissions.

For a 1,000-foot test, start close with both devices on the ground and the DJI link active. Compare clear and tree-obstructed paths in steps, with the Pi and ground antenna at representative heights. Record delivered fps, stalls, and the time for a palette change at each stop. This mode needs an existing two-way IP link between Mac and Pi; it changes bandwidth use, not radio range.

## Temperature overlays and calibration pauses

Press **t** on the main controls screen. **i** toggles a green highlight for pixels in the selected temperature range (initially 20–40 °C). **m** independently toggles red hottest and blue coldest spots and their readings in the visible image. Select the lower or upper bound with **1 / 2**, adjust with **+ / -** (one degree) or **[ / ]** (ten degrees). **u** switches °C / °F. **s** saves preferences and **b** returns. **g** independently toggles a vertical temperature scale. When enabled, the palette spans the coolest to hottest valid pixel in the current view, with labels in the selected unit. A uniform scene shows a single temperature. All overlays start off. Readings use the P1's temperature plane. Demo temperatures are synthetic.

Brief gaps can occur when the shutter closes. Capture skips isolated interrupted frames and reconnects after repeated failures. Overlays update with each fresh frame. To update the physical Pi, stop the current viewer, run `cd ~/thermal-pi && git pull --ff-only` in a Pi SSH session, and restart the boot service if active (`sudo systemctl try-restart thermal-pi`). Start `thermal-pi` again on the Mac.

## Open a video window on your Mac

The Mac launcher opens the camera's JPEG stream in an **ffplay window** and keeps the numbered control menu in Terminal. The SSH connection carries both. Each thermal sensor pixel comes from the P1's native 160 × 120 image. The Pi scales that image for display. Double-click the player for fullscreen. Enter 0 in the menu or close the player to end the session.

On the Pi, update the installed copy with `cd ~/thermal-pi && git pull --ff-only`. On your Mac, clone this repo or update your Mac checkout. The launcher needs Python 3, SSH, and ffplay on your Mac. If ffplay is missing, install it with `brew install ffmpeg`.

From the **Mac checkout** run:

```sh
./scripts/thermal-view YOUR_USER@thermalpi.local
```

For an emulator, add `--demo` and use your usual SSH address and port. For example, if you normally run `ssh -p 2222 YOUR_USER@localhost`, use:

```sh
./scripts/thermal-view --demo -p 2222 YOUR_USER@localhost
```

The remote checkout is expected at `~/thermal-pi`. The launcher starts the service if needed and reuses a running service of the same mode. A terminal-only preview is also available below.

## Watch directly in your SSH terminal

After installation, log into the Pi in Mac Terminal and type `thermal`. In the emulator, type `thermal --demo`. The terminal becomes the viewer. Use a UTF-8 terminal with 256-color support. Video resolution follows the size of the terminal in rows and columns, so a larger window shows more detail. The existing browser viewer provides the full JPEG image.

Press **1** for white hot, **2** for black hot, **3** for iron, or **4** for rainbow. Keys take effect immediately. Use **+ / -** for zoom, **r** for rotation, **f** to flip, **c** to calibrate, **h / l** for high or low gain, **s** to save settings, and **q** to quit. The viewer restores your shell on exit. It attaches to an existing camera service or starts a temporary one for this session. Demo uses port 8082 and real capture uses 8080.

**Updating an existing Git clone on the Pi** takes one setup step:

```sh
cd ~/thermal-pi && git pull --ff-only && sudo ln -sfn "$PWD/scripts/thermal" /usr/local/bin/thermal
```

If the boot service was active, run `sudo systemctl restart thermal-pi` once to load the new viewer endpoint. If you were running the older foreground server manually, stop it with Ctrl-C first. For a ZIP installation, replace the source files from the updated download, run `chmod +x scripts/thermal` from the project folder, and create the same symlink. Fresh installs create the command automatically.

From a Mac you can also connect and launch in one step with `ssh -t YOUR_USER@thermalpi.local thermal`. Substitute your usual Pi address and SSH port.

## What works in this version

- Software palettes: white hot, black hot, iron, rainbow (our palettes, not exact manufacturer app replicas).
- Digital crop/zoom 1–8×, clockwise rotation, horizontal flip after rotation.
- Queued P1 shutter calibration and high/low gain via upstream driver. Only one worker owns USB access. Commands expire after two seconds; status shows completion/failure.
- Save preferences explicitly; saved gain is reapplied on camera reconnect.
- Automatic capture retry after disconnect, latest-frame-only storage, visible stale/disconnected status.
- Clearly marked synthetic demo mode. No camera required.
- Localhost-only HTTP service reached through SSH. No cloud account or internet needed during use.

No automatic gain (upstream protocol does not implement it), manufacturer AI enhancement, recording, motor/gimbal control, or hotspot configuration yet. Overlay readings are camera-reported estimates; accuracy has not been checked against a reference.

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

Open **http://127.0.0.1:8080** in your Mac browser. The tunnel must remain open. Press Fullscreen for an image-only view; status appears if the feed becomes stale. Press a number once. Zoom, rotation, and gain have their own screens. Use +/− or the left/right arrows repeatedly for zoom and rotation, then b or Esc to go back. `s` saves settings, r refreshes status, `0` exits just the menu. A queued hardware command is not yet confirmed: press r to inspect completion.

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

## Test the actual video link and save CSV

On the Mac, run:

```sh
thermal-pi --test
```

This uses your saved Pi connection, opens the video window automatically, and logs
one row per video request to `~/thermal-pi-logs/thermal-<timestamp>.csv`.
Press **q in the video window** or **Ctrl-C in the terminal** to stop. Each row is
flushed immediately so an interrupted test preserves completed measurements.
The test uses the same native frame endpoint, SSH tunnel, Mac enlargement, and
ffplay pipeline as `thermal-pi --field`. Real-camera defaults remain 25 FPS and
JPEG quality 85. Saved palette, zoom and temperature overlays are preserved.
To change camera settings, use the regular menu and save them before testing.
Demo mode is labelled in the CSV and cannot establish real camera performance.

For a five-minute run with a chosen filename:

```sh
thermal-pi --test --seconds 300 --csv ~/Desktop/thermal-near.csv
```

To label a stationary test with the distance from the ground AP to the Pi:

```sh
thermal-pi --test --distance-ft 300 --seconds 60
```

Use `--distance-m 100` instead for meters. Every row includes both numeric
`distance_ft` and `distance_m` columns, converted automatically. Without a
distance option, these cells are blank (unknown, not zero). This is a manually
entered, fixed distance for the whole run; the script does not read DJI telemetry
or track movement. Hold roughly the same distance during each run, stop, then
start a new run with the next distance. Use a consistent measurement method,
ideally straight-line separation between the AP and Pi.

For a distance-versus-performance graph, collect the `status=end` row from each
CSV and plot `distance_ft` (or `distance_m`) against `average_fps` or
`average_payload_kbps`. These averages cover the entire run, including outages.
Use frame rows' `frame_gap_ms` to investigate stalls. Keep test duration, camera
settings and scene complexity comparable across runs. Repeated runs at each
distance help show variation.

Existing CSV files are never overwritten. An explicit destination also works,
for example `thermal-pi suitablebat9@192.168.1.50 --test` (use your actual Pi IP).
No Pi update is needed if its current field viewer already works.

CSV columns include UTC time, elapsed seconds, frame sequence, bytes received,
request duration, Mac decode/enlargement duration, local player-write duration,
frame delivery gap, cumulative frames/bytes, average FPS and video payload kb/s.
Rows marked `no_new_frame` mean the server had no newer frame; `error` rows
record timeouts or HTTP failures. `end` contains the whole-run averages.
`sequence_gap` counts camera frames not fetched between successful requests;
it is **not packet loss**, since pacing and processing also skip source frames.
Request time includes server processing and transfer, not just radio latency.
Delivery means handed to the player, not confirmed displayed on screen.
Bandwidth is JPEG plus frame metadata, excluding HTTP, SSH and Wi-Fi overhead.
These measurements describe the actual viewing workload, not maximum link capacity
or camera-to-screen latency. A timed run may finish slightly late while an
in-progress request or player write completes.

For comparable range tests, keep FPS, quality, palette and overlays the same.
Start with a nearby baseline, then repeat at increasing distances with the
camera looking at a similarly detailed, moving scene. Use descriptive filenames
for location/distance. Connect the Mac by Ethernet to the BrosTrend and the Pi
to its test SSID so the measurements use that link rather than your home Wi-Fi.
Check for falling FPS, long frame gaps and errors relative to the baseline.

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
Vendored path: `thermal_pi/vendor/p3_camera.py`, with a bounded USB frame-read deadline. It derives from Joshua V. Dillon and contributors' https://github.com/jvdillon/p3-ir-camera. The Qt GUI and virtual webcam layer are not needed. Application code in the other files is new. Check upstream changes deliberately rather than silently downloading a new driver at startup.

The Pi installer uses OS-managed dependency versions for ARM compatibility. `requirements.txt` defines supported ranges for local demos; this is not a reproducible lock of every future OS package version.
