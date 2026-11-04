"""Single camera owner, bounded latest-frame storage, and display processing."""
import io
import json
import logging
import math
from functools import lru_cache
import os
from pathlib import Path
import queue
import threading
import time

import numpy as np
from PIL import Image, ImageDraw

DEFAULTS = dict(palette='white', zoom=1, rotation=0, flip=False, gain='high',
                range_on=False, spots=False, scale=False, low_c=20, high_c=40, unit='C')
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
    if any(type(result[key]) is not bool for key in ('range_on', 'spots', 'scale')):
        raise ValueError('Overlay switches must be on or off')
    if result['unit'] not in ('C', 'F'):
        raise ValueError('Temperature unit must be C or F')
    if any(type(result[k]) not in (int, float) or not math.isfinite(result[k])
           for k in ('low_c', 'high_c')) or not -273.15 <= result['low_c'] < result['high_c'] <= 750:
        raise ValueError('Range needs a lower bound below its upper bound (-273.15 to 750 C)')
    return result


def visible_pixels(gray, settings):
    h, w = gray.shape
    ch, cw = max(1, int(h/settings['zoom'])), max(1, int(w/settings['zoom']))
    gray = gray[(h-ch)//2:(h-ch)//2+ch, (w-cw)//2:(w-cw)//2+cw]
    gray = np.rot90(gray, -(settings['rotation']//90))
    return np.fliplr(gray) if settings['flip'] else gray


@lru_cache(maxsize=4)
def palette_table(palette):
    anchors = {
        'white': [(0,0,0),(255,255,255)],
        'black': [(255,255,255),(0,0,0)],
        'iron': [(0,0,0),(70,0,100),(190,30,40),(255,170,0),(255,255,230)],
        'rainbow': [(0,0,100),(0,120,255),(0,220,80),(255,230,0),(255,0,0)],
    }[palette]
    return np.stack([np.interp(np.arange(256), np.linspace(0,255,len(anchors)),
                               np.array(anchors)[:,i]) for i in range(3)], axis=1).astype('uint8')
def display_temp(celsius, unit):
    return celsius * 1.8 + 32 if unit == 'F' else celsius


def draw_scale(image, palette, limits, unit):
    low, high = limits
    # Keep labels alongside the ramp and out of the bottom overlay caption.
    x, y = image.width - 80, 38
    height = 128
    gradient = np.linspace(255, 0, height).round().astype(np.uint8)
    if high == low:
        gradient.fill(128)
    bar = Image.fromarray(palette[gradient][:, None, :]).resize((12, height), Image.Resampling.NEAREST)
    image.paste(bar, (x, y))
    draw = ImageDraw.Draw(image)
    draw.rectangle((x-1, y-1, x+12, y+height), outline='#888888')
    stops = (0.5,) if high == low else (0, 0.5, 1)
    for fraction in stops:
        value = display_temp(high + fraction * (low-high), unit)
        draw.text((x+17, y+round(fraction*(height-1))-5), f'{value:.1f} {unit}',
                  fill='white', stroke_width=2, stroke_fill='black')


def native_picture(frame, settings, demo=False, temperatures=None):
    gray = visible_pixels(np.asarray(frame, dtype=np.uint8), settings)
    palette = palette_table(settings['palette'])
    colors = palette[gray]
    overlays = settings['range_on'] or settings['spots'] or settings['scale']
    limits = None
    temp = valid = None
    if overlays and temperatures is not None:
        raw = visible_pixels(temperatures, settings)
        valid = (raw != 0) & (raw != 65535)
        temp = raw.astype(np.float32) / 64 - 273.15
        if settings['scale'] and valid.any():
            readings = temp[valid]
            low, high = float(readings.min()), float(readings.max())
            limits = low, high
            # Assign scene and legend colors from the same temperature mapping.
            indices = np.full(gray.shape, 128, dtype=np.uint8)
            if high > low:
                indices[valid] = np.rint((readings-low) * (255 / (high-low))).astype(np.uint8)
            colors = palette[indices]
            colors[~valid] = (45, 45, 45)
        if settings['range_on']:
            mask = valid & (temp >= settings['low_c']) & (temp <= settings['high_c'])
            colors[mask] = colors[mask] // 3 + np.array([0, 165, 70], dtype=np.uint8)
    info = dict(size=(480,640) if settings['rotation'] in (90,270) else (640,480),
                palette=settings['palette'], limits=limits, unit=settings['unit'],
                labels=[], marks=[], demo=demo)
    if overlays:
        unit = settings['unit']
        labels = info['labels']
        if temp is None or not valid.any():
            labels.append('Temperature data unavailable')
        else:
            if settings['range_on']:
                low = display_temp(settings['low_c'], unit)
                high = display_temp(settings['high_c'], unit)
                labels.append(f'Green: {low:.1f} to {high:.1f} {unit}')
            if settings['spots']:
                for name, color, func, replace in [('HOT', '#ff533f', np.argmax, -np.inf),
                                                   ('COLD', '#39bbff', np.argmin, np.inf)]:
                    y, x = np.unravel_index(func(np.where(valid, temp, replace)), temp.shape)
                    info['marks'].append((float((x+.5)/temp.shape[1]), float((y+.5)/temp.shape[0]), name, color))
                    labels.append(f'{name} {display_temp(temp[y,x], unit):.1f} {unit}')
    return Image.fromarray(colors), info


def enlarge_picture(native, info):
    im = native.resize(tuple(info['size']), Image.Resampling.NEAREST)
    if info['limits'] is not None:
        draw_scale(im, palette_table(info['palette']), info['limits'], info['unit'])
    draw = ImageDraw.Draw(im)
    for x, y, name, color in info['marks']:
        px, py = int(x*im.width), int(y*im.height)
        radius = 8 if name == 'HOT' else 5
        box = (px-radius,py-radius,px+radius,py+radius)
        draw.ellipse(box, outline='black', width=3)
        draw.ellipse(box, outline=color, width=2)
    if info['labels']:
        labels = info['labels']
        draw.text((5, im.height-17), '   '.join(labels), fill='white', stroke_width=2, stroke_fill='black')
    if info['demo']:
        ImageDraw.Draw(im).text((12,12), 'DEMO - simulated camera', fill=(255,80,80), stroke_width=1, stroke_fill=(0,0,0))
    return im


def render(frame, settings, demo=False, temperatures=None):
    im = enlarge_picture(*native_picture(frame, settings, demo, temperatures))
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
        self.latest = None
        self._jpeg = None
        self.updated = 0
        self.sequence = 0
        self.error = 'Starting'
        self.command_status = 'No hardware command submitted'
        self.thread = threading.Thread(target=self.run, daemon=True)

    @property
    def jpeg(self):
        # Legacy viewers request an enlarged JPEG; a field-only session never builds it.
        with self.lock:
            if self.latest is not None and self._jpeg is None:
                self._jpeg = render(*self.latest)
            return self._jpeg

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
        bad_reads = 0
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
                    temperatures = ((15 + frame.astype(np.float32) / 8 + 273.15) * 64).astype(np.uint16)
                    # Demo label is burned into the synthetic image, including the raw feed.
                    im = Image.fromarray(frame)
                    ImageDraw.Draw(im).text((3,3),'DEMO',fill=255)
                    frame = np.array(im)
                else:
                    from usb.core import USBTimeoutError
                    from .vendor.p3_camera import FrameMarkerMismatchError
                    try:
                        frame, temperatures = camera.read_frame_both()
                        if frame is None:
                            raise FrameMarkerMismatchError('Incomplete P1 frame')
                    except (FrameMarkerMismatchError, USBTimeoutError, TimeoutError) as exc:
                        bad_reads += 1
                        if bad_reads >= 8:
                            raise RuntimeError('P1 stream failed to resynchronize') from exc
                        if bad_reads == 1:
                            logging.info('Skipped interrupted P1 frame: %s', exc)
                        continue
                    bad_reads = 0
                with self.lock:
                    settings = self.settings.copy()
                with self.lock:
                    self.latest = (frame, settings, self.demo, temperatures)
                    self._jpeg = None
                    self.updated = time.monotonic()
                    self.sequence += 1
                    self.error = None
                if self.demo:
                    self.stop.wait(1/15)
            except Exception as exc:
                logging.exception('Capture failed; retrying')
                with self.lock:
                    self.error = str(exc)
                    self.latest = self._jpeg = None
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
                bad_reads = 0
                self.stop.wait(2)
        if camera:
            import usb.util
            dev = camera.dev
            try:
                camera.disconnect()
            finally:
                if dev is not None:
                    usb.util.dispose_resources(dev)
