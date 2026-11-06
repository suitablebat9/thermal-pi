"""Mac receiver for paced native thermal frames."""
import io
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from PIL import Image, ImageDraw
from .core import enlarge_picture


def decode(packet):
    metadata, encoded = packet.split(b'\n', 1)
    with Image.open(io.BytesIO(encoded)) as native:
        return enlarge_picture(native.convert('RGB'), json.loads(metadata))


def feed(player, port, fps, quality, notify, log=None, seconds=0, stop=None):
    url = f'http://127.0.0.1:{port}/api/field-frame?quality={quality}'
    sequence = -1
    started = time.monotonic()
    test_started = started
    frames = received = 0
    try:
        while player.poll() is None:
            if stop is not None and stop.is_set():
                break
            if seconds and time.monotonic()-test_started >= seconds:
                break
            tick = time.monotonic()
            try:
                with urlopen(f'{url}&after={sequence}', timeout=2) as response:
                    if response.status == 204:
                        if log:
                            log.record('no_new_frame', request_ms=(time.monotonic()-tick)*1000)
                        time.sleep(max(0, 1/fps-(time.monotonic()-tick)))
                        continue
                    packet = response.read()
                    sequence = int(response.headers['X-Frame-Sequence'])
                fetched = time.monotonic()
                picture = decode(packet)
                decoded = time.monotonic()
                live = True
                received += len(packet)
                frames += 1
            except (URLError, TimeoutError, ValueError, OSError) as exc:
                live = False
                if log:
                    log.record('error', request_ms=(time.monotonic()-tick)*1000, error=exc)
                if isinstance(exc, HTTPError) and exc.code == 404:
                    notify('Update the Pi and restart its camera service for field mode.')
                    return
                picture = Image.new('RGB', (640,480), '#17171a')
                ImageDraw.Draw(picture).text((20,25), 'NO LIVE VIDEO - reconnecting', fill='white')
                time.sleep(.3)
            writing = time.monotonic()
            picture.save(player.stdin, format='PPM')
            player.stdin.flush()
            if log and live:
                log.record('frame', sequence=sequence, payload_bytes=len(packet),
                           request_ms=(fetched-tick)*1000, decode_ms=(decoded-fetched)*1000,
                           player_write_ms=(time.monotonic()-writing)*1000)
            elapsed = time.monotonic()-started
            if elapsed >= 5:
                notify(f'Field: {frames/elapsed:.1f} fps | {8*received/elapsed/1000:.0f} kb/s video payload')
                started, frames, received = time.monotonic(), 0, 0
            time.sleep(max(0, 1/fps-(time.monotonic()-tick)))
    except (BrokenPipeError, OSError):
        pass
    finally:
        if log:
            log.close()
        try:
            player.stdin.close()
        except OSError:
            pass
