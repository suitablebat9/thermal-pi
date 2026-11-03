"""View the thermal feed directly in an interactive SSH terminal."""
import argparse
import contextlib
import io
import json
import os
import select
import shutil
import subprocess
import sys
import termios
import time
import tty
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image


def request(port, path, data=None):
    payload = None if data is None else json.dumps(data).encode()
    req = Request(f'http://127.0.0.1:{port}/api/{path}', data=payload,
                  headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=1) as response:
        if response.headers.get_content_type() == 'image/jpeg':
            return response.read()
        return json.load(response)


def draw_frame(jpeg, width, height):
    # Each character cell contains two stacked pixels. Use the xterm-256 palette.
    with Image.open(io.BytesIO(jpeg)) as image:
        scale = min(width / image.width, (2 * height) / image.height)
        size = max(1, int(image.width * scale)), max(2, int(image.height * scale) // 2 * 2)
        pixels = np.asarray(image.convert('RGB').resize(size, Image.Resampling.BOX), dtype=int)
    red, green, blue = pixels.transpose(2, 0, 1)
    gray = np.clip(np.rint((red - 8) / 10), 0, 23).astype(int) + 232
    gray[red < 4] = 16
    gray[red > 248] = 231
    colors = np.rint(pixels / 51).astype(int)
    codes = 16 + colors[:,:,0]*36 + colors[:,:,1]*6 + colors[:,:,2]
    codes = np.where((red == green) & (green == blue), gray, codes)
    lines = []
    for upper, lower in zip(codes[::2], codes[1::2]):
        parts = []
        previous = None
        for top, bottom in zip(upper, lower):
            pair = (top, bottom)
            if pair != previous:
                parts.append(f'\033[38;5;{top};48;5;{bottom}m')
                previous = pair
            parts.append('▀')
        lines.append(''.join(parts)+'\033[0m')
    return lines


@contextlib.contextmanager
def connect(demo):
    port = 8082 if demo else 8080
    child = None
    try:
        try:
            status = request(port, 'status')
        except URLError as exc:
            if not isinstance(exc.reason, ConnectionRefusedError):
                raise
            args = [sys.executable, '-m', 'thermal_pi.server', '--port', str(port)]
            if demo:
                args.append('--demo')
            child = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(80):
                if child.poll() is not None:
                    raise RuntimeError('Camera service could not start. Run the foreground server to see its log.')
                time.sleep(.1)
                try:
                    status = request(port, 'status')
                    break
                except URLError:
                    continue
            else:
                raise RuntimeError('Camera service startup timed out.')
        if status.get('demo') != demo:
            raise RuntimeError('Another camera mode is running on this port. Stop it and try again.')
        yield port
    finally:
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


def control(port, key):
    palettes = {'1':'white', '2':'black', '3':'iron', '4':'rainbow'}
    if key in palettes:
        request(port, 'settings', {'palette': palettes[key]})
    elif key == 's':
        request(port, 'save', {})
        return 'Settings saved'
    elif key in ('c','h','l'):
        request(port, 'command', {'action': {'c':'shutter','h':'high','l':'low'}[key]})
        return 'Hardware command queued'
    elif key in ('+','=','-','r','f'):
        settings = request(port, 'status')['settings']
        if key == 'r':
            patch = {'rotation': (settings['rotation'] + 90) % 360}
        elif key == 'f':
            patch = {'flip': not settings['flip']}
        else:
            step = -1 if key == '-' else 1
            patch = {'zoom': max(1, min(8, settings['zoom'] + step))}
        request(port, 'settings', patch)
    return ''


def view(port, demo):
    fd = sys.stdin.fileno()
    before = termios.tcgetattr(fd)
    message = ''
    try:
        tty.setcbreak(fd)
        sys.stdout.write('\033[?1049h\033[?25l')
        while True:
            width, rows = shutil.get_terminal_size()
            width = max(1, width-1)
            header = 'THERMAL PI' + ('  |  DEMO' if demo else '')
            lines = [header, '1-4 palette  +/- zoom  r rotate  f flip  q quit',
                     'c calibrate  h/l gain  s save  |  '+message]
            lines = [line[:width] for line in lines]
            try:
                frame = request(port, 'frame')
                lines += draw_frame(frame, min(width,160), max(1, min(rows-3,80)))
            except HTTPError as exc:
                if exc.code == 404:
                    raise RuntimeError('The running service needs updating. Restart thermal-pi after git pull.')
                error = json.load(exc).get('error',str(exc))
                lines.append(('Camera offline: '+error)[:width])
            output = '\033[H' + '\033[K\r\n'.join(lines[:max(1,rows)]) + '\033[0m\033[K\033[J'
            sys.stdout.write(output)
            sys.stdout.flush()
            if select.select([fd], [], [], .12)[0]:
                key = os.read(fd, 1).decode('ascii', errors='ignore').lower()
                if not key or key in ('q','\x04'):
                    break
                if key in '\r\n':
                    continue
                try:
                    message = control(port, key)
                except HTTPError as exc:
                    message = json.load(exc).get('error', str(exc))
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, before)
        sys.stdout.write('\033[0m\033[?25h\033[?1049l')
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', help='show synthetic thermal video')
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.exit(1, 'Run thermal in an interactive terminal (use ssh -t for a remote command).\n')
    try:
        with connect(args.demo) as port:
            view(port, args.demo)
    except KeyboardInterrupt:
        pass
    except (RuntimeError, OSError, ValueError) as exc:
        parser.exit(1, f'Thermal viewer: {exc}\n')


if __name__ == '__main__':
    main()
