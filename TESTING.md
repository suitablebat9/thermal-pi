# Validation record

## Completed locally

- Six automated tests pass: settings validation; atomic save/reload; palette and rotation output; demo MJPEG decoding and queued gain simulation; stale/disconnected status; local-request restrictions.
- Ran the actual HTTP demo service and inspected its browser image and demo warning.
- Exercised the persistent terminal menu against the running service: black-hot selection, saving, and exit while service remained live.
- Both installation scripts pass Bash syntax validation.
- USB driver preserved unchanged from the pinned upstream commit.

Environment: macOS, Python 3.15, dependency ranges from requirements.txt. This is not evidence of Raspberry Pi or camera hardware compatibility.

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
