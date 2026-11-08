"""Measure the normal continuous MJPEG feed without decoding it in Python."""
import time
from urllib.request import urlopen
from urllib.error import URLError
from http.client import HTTPException


def feed(player, port, fps, quality, notify, log, seconds=0, stop=None):
    started = time.monotonic()
    sequence = 0
    def active():
        return (player.poll() is None and not (stop and stop.is_set())
                and not (seconds and time.monotonic()-started >= seconds))
    try:
        while active():
            try:
                with urlopen(f'http://127.0.0.1:{port}/stream.mjpg', timeout=2) as response:
                    while active():
                        tick = time.monotonic()
                        line = response.readline(4096)
                        if not line:
                            raise OSError('Video stream disconnected')
                        if not line.strip().startswith(b'--frame'):
                            continue
                        length = None
                        while True:
                            line = response.readline(4096)
                            if not line:
                                raise OSError('Incomplete frame header')
                            if not line.strip():
                                break
                            if line.lower().startswith(b'content-length:'):
                                length = int(line.split(b':', 1)[1])
                        if length is None or not 0 < length <= 10_000_000:
                            raise ValueError('Invalid JPEG frame length')
                        packet = response.read(length)
                        if len(packet) != length:
                            raise OSError('Incomplete video frame')
                        fetched = time.monotonic()
                        player.stdin.write(packet)
                        player.stdin.flush()
                        sequence += 1
                        log.record('frame', sequence=sequence, payload_bytes=length,
                                   request_ms=(fetched-tick)*1000,
                                   player_write_ms=(time.monotonic()-fetched)*1000)
            except BrokenPipeError:
                break
            except (OSError, URLError, HTTPException, ValueError) as exc:
                log.record('error', error=exc)
                if stop:
                    stop.wait(.3)
                else:
                    time.sleep(.3)
    finally:
        log.close()
        try:
            player.stdin.close()
        except OSError:
            pass
