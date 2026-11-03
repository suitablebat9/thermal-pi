"""Single camera owner, bounded latest-frame storage, and display processing."""
import io
import json
import logging
import os
from pathlib import Path
import queue
import threading
import time

import numpy as np
from PIL import Image, ImageDraw

DEFAULTS = dict(palette='white', zoom=1, rotation=0, flip=False, gain='high')
PALETTES = ('white', 'black', 'iron', 'rainbow')


def validated(current, patch):
    if not isinstance(patch, dict) or set(patch) - set(DEFAULTS):
        raise ValueError('Unknown settings')
    result = dict(current, **patch)
    if result['palette'] not in PALETTES:
        raise ValueError('Invalid palette')
    if type(result['zoom']) not in (int, float) or not 1 <= result['zoom'] <= 8:
        raise ValueError('Zoom must be 1–8')
    if type(result['rotation']) is not int or result['rotation'] not in (0, 90, 180, 270):
        raise ValueError('Rotation must be 0, 90, 180, or 270')
    if type(result['flip']) is not bool or result['gain'] not in ('low', 'high'):
        raise ValueError('Invalid flip or gain')
    return result


def render(frame, settings, demo=False):
    gray = np.asarray(frame, dtype=np.uint8)
    h, w = gray.shape
    ch, cw = max(1, int(h/settings['zoom'])), max(1, int(w/settings['zoom']))
    gray = gray[(h-ch)//2:(h-ch)//2+ch, (w-cw)//2:(w-cw)//2+cw]
    gray = np.rot90(gray, -(settings['rotation']//90))
    if settings['flip']:
        gray = np.fliplr(gray)
    anchors = {
        'white': [(0,0,0),(255,255,255)],
        'black': [(255,255,255),(0,0,0)],
        'iron': [(0,0,0),(70,0,100),(190,30,40),(255,170,0),(255,255,230)],
        'rainbow': [(0,0,100),(0,120,255),(0,220,80),(255,230,0),(255,0,0)],
    }[settings['palette']]
    table = np.stack([np.interp(np.arange(256), np.linspace(0,255,len(anchors)),
                               np.array(anchors)[:,i]) for i in range(3)], axis=1).astype('uint8')
    im = Image.fromarray(table[gray])
    target = (480,640) if settings['rotation'] in (90,270) else (640,480)
    im = im.resize(target, Image.Resampling.NEAREST)
    if demo:
        ImageDraw.Draw(im).text((12,12), 'DEMO - simulated camera', fill=(255,80,80), stroke_width=1, stroke_fill=(0,0,0))
    out = io.BytesIO()
    im.save(out, format='JPEG', quality=85)
    return out.getvalue()


class Engine:
    def __init__(self, demo=False, config=None):
        self.demo = demo
        self.path = Path(config or '~/.config/thermal-pi/settings.json').expanduser()
        self.settings = DEFAULTS.copy()
        if self.path.exists():
            self.settings = validated(self.settings, json.loads(self.path.read_text()))
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.commands = queue.Queue(maxsize=8)
        self.jpeg = None
        self.updated = 0
        self.sequence = 0
        self.error = 'Starting'
        self.command_status = 'No hardware command submitted'
        self.thread = threading.Thread(target=self.run, daemon=True)

    def status(self):
        with self.lock:
            age = time.monotonic()-self.updated if self.updated else None
            return dict(settings=self.settings.copy(), demo=self.demo,
                        connected=age is not None and age < 2 and not self.error,
                        age_seconds=age, error=self.error, command=self.command_status)

    def update(self, patch):
        if 'gain' in patch:
            raise ValueError('Use hardware command for gain')
        with self.lock:
            self.settings = validated(self.settings, patch)
            return self.settings.copy()

    def save(self):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.settings, indent=2)+'\n')
            os.replace(temp, self.path)

    def command(self, action):
        if action not in ('shutter','low','high'):
            raise ValueError('Unknown hardware command')
        with self.lock:
            if not self.status()['connected']:
                raise ValueError('Camera is not connected')
            try:
                self.commands.put_nowait((action, time.monotonic()))
            except queue.Full:
                raise ValueError('Command queue full')
            self.command_status = f'Queued: {action}'

    def run(self):
        camera = None
        while not self.stop.is_set():
            try:
                if not self.demo and camera is None:
                    from .vendor.p3_camera import P3Camera, get_model_config, GainMode
                    camera = P3Camera(config=get_model_config('p1'))
                    camera.connect()
                    camera.init()
                    camera.start_streaming()
                    camera.set_gain_mode(GainMode.HIGH if self.settings['gain']=='high' else GainMode.LOW)
                try:
                    action, submitted = self.commands.get_nowait()
                except queue.Empty:
                    action = None
                if action:
                    if time.monotonic()-submitted > 2:
                        with self.lock:
                            self.command_status = f'Expired: {action}; retry'
                    else:
                        if camera:
                            if action == 'shutter':
                                camera.trigger_shutter()
                            else:
                                camera.set_gain_mode(GainMode.HIGH if action=='high' else GainMode.LOW)
                        with self.lock:
                            if action in ('high','low'):
                                self.settings['gain'] = action
                            self.command_status = f'{"Simulated" if self.demo else "Completed"}: {action}'
                if self.demo:
                    y,x = np.mgrid[:120,:160]
                    phase = time.monotonic()
                    frame = np.clip(35+x/3+180*np.exp(-((x-80-35*np.sin(phase))**2+(y-60)**2)/200),0,255).astype('uint8')
                    # Demo label is burned into the synthetic image, including the raw feed.
                    im = Image.fromarray(frame)
                    ImageDraw.Draw(im).text((3,3),'DEMO',fill=255)
                    frame = np.array(im)
                else:
                    frame, _ = camera.read_frame_both()
                    if frame is None:
                        raise RuntimeError('Camera returned no image')
                with self.lock:
                    settings = self.settings.copy()
                jpeg = render(frame, settings, demo=self.demo)
                with self.lock:
                    self.jpeg, self.updated = jpeg, time.monotonic()
                    self.sequence += 1
                    self.error = None
                if self.demo:
                    self.stop.wait(1/15)
            except Exception as exc:
                logging.exception('Capture failed; retrying')
                with self.lock:
                    self.error = str(exc)
                    self.jpeg = None
                    self.command_status = 'Capture error; pending commands discarded'
                    while not self.commands.empty():
                        self.commands.get_nowait()
                if camera:
                    try:
                        import usb.util
                        dev = camera.dev
                        try:
                            camera.disconnect()
                        finally:
                            if dev is not None:
                                usb.util.dispose_resources(dev)
                    except Exception:
                        logging.exception('Camera cleanup failed')
                    camera = None
                self.stop.wait(2)
        if camera:
            import usb.util
            dev = camera.dev
            try:
                camera.disconnect()
            finally:
                if dev is not None:
                    usb.util.dispose_resources(dev)
