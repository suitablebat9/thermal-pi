# Validation record

## Completed locally

- The original six automated tests pass: settings validation; atomic save/reload; palette and rotation output; demo MJPEG decoding and queued gain simulation; stale/disconnected status; local-request restrictions.
- Ran the actual HTTP demo service and inspected its browser image and demo warning.
- Exercised the persistent terminal menu against the running service: black-hot selection, saving, and exit while service remained live.
- Both installation scripts pass Bash syntax validation.
- USB driver comes from the pinned upstream commit with a local read deadline.

Environment: macOS, Python 3.15, dependency ranges from requirements.txt. This is not evidence of Raspberry Pi or camera hardware compatibility.

The seventh test runs the terminal viewer in an 80-column, 24-row pseudo-terminal, receives a real HTTP demo frame, changes the palette with the 2 key, and verifies that q restores the shell. A separate launch check verified automatic demo service startup and exit. Physical USB capture and SSH bandwidth on the Pi remain unmeasured.

Temperature tests cover aligned highlights after zoom/rotation/flip, spot drawing, saved-settings compatibility, and recovery from one malformed frame without reopening the camera. Hardware shutter duration and absolute temperature accuracy still need measurement.

## Pending on Pi 3B+ / Raspberry Pi OS Lite 64-bit

1. Run installer; verify USB identity and access as the regular user after login.
2. Start real capture and verify image orientation and image content.
3. Exercise all palettes, zoom and rotation while viewing over SSH.
4. Confirm shutter command completes and subsequent frames resume.
5. Verify high/low gain changes on the actual P1 firmware.
6. Unplug/replug camera: viewer must hide old video and capture must recover.
7. Save settings, reboot with service enabled, and verify preferences restored.
8. Close the SSH menu and reconnect; camera service should remain running.
9. Measure end-to-end latency, frame rate, CPU load, temperature and power stability over at least 15 minutes.

Use bench power first. No payload, flight range, hotspot, or compass-interference tests have been performed. The Flask development server is used intentionally for this localhost-only bench prototype; reassess serving/streaming architecture before wider deployment.

The Mac window path was exercised with the demo service and a real ffplay process. The player decoded successive changing 640 × 480 JPEG frames. Remote SSH transport and physical P1 performance still need a test on the target Pi.

Mac emulator playback requests one JPEG at a time at up to four frames per second. A local ffplay integration check decoded successive frames, applied black hot during playback, and read live status afterward. Retesting this change over the authenticated QEMU SSH connection is pending.
