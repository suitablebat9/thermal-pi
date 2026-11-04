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


def feed(player, port, fps, quality, notify):
    url = f'http://127.0.0.1:{port}/api/field-frame?quality={quality}'
    sequence = -1
    started = time.monotonic()
    frames = received = 0
    try:
        while player.poll() is None:
            tick = time.monotonic()
            try:
                with urlopen(f'{url}&after={sequence}', timeout=2) as response:
                    if response.status == 204:
                        time.sleep(1/fps)
                        continue
                    packet = response.read()
                    sequence = int(response.headers['X-Frame-Sequence'])
                picture = decode(packet)
                received += len(packet)
                frames += 1
            except (URLError, TimeoutError) as exc:
                if isinstance(exc, HTTPError) and exc.code == 404:
                    notify('Update the Pi and restart its camera service for field mode.')
                    return
                picture = Image.new('RGB', (640,480), '#17171a')
                ImageDraw.Draw(picture).text((20,25), 'NO LIVE VIDEO - reconnecting', fill='white')
                time.sleep(.3)
            picture.save(player.stdin, format='JPEG', quality=90)
            player.stdin.flush()
            elapsed = time.monotonic()-started
            if elapsed >= 5:
                notify(f'Field: {frames/elapsed:.1f} fps | {8*received/elapsed/1000:.0f} kb/s video payload')
                started, frames, received = time.monotonic(), 0, 0
            time.sleep(max(0, 1/fps-(time.monotonic()-tick)))
    except (BrokenPipeError, OSError):
        pass
    finally:
        try:
            player.stdin.close()
        except OSError:
            pass
