import io
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
from thermal_pi.core import DEFAULTS, Engine, render, validated
from thermal_pi.vendor.p3_camera import FrameMarkerMismatchError


class ThermalOverlayTests(unittest.TestCase):
    def test_range_uses_temperature_and_tracks_transforms(self):
        gray = np.full((120, 160), 80, np.uint8)
        temperatures = np.full(gray.shape, round(283.15*64), np.uint16)
        temperatures[30:60, 40:80] = round(303.15*64)
        settings = dict(DEFAULTS, zoom=2, rotation=90, flip=True, range_on=True)
        image = np.array(Image.open(io.BytesIO(render(gray, settings, temperatures=temperatures))))
        # Top left of the center crop stays top left after clockwise rotation + horizontal flip.
        r,g,b = map(int,image[60,60])
        self.assertGreater(g,r+80)
        self.assertLess(np.ptp(image[400,300]),10)
        marked = np.array(Image.open(io.BytesIO(render(gray,dict(settings,spots=True),temperatures=temperatures))))
        self.assertTrue(np.any(marked[:25,:25] != image[:25,:25]))

    def test_old_settings_and_bad_ranges(self):
        self.assertFalse(validated(DEFAULTS, {'zoom':2})['spots'])
        with self.assertRaises(ValueError):
            validated(DEFAULTS, {'low_c':45,'high_c':40})

    def test_one_bad_frame_keeps_camera_session(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = Engine(config=folder+'/settings')
            gray = np.zeros((120,160), np.uint8)
            with patch('thermal_pi.vendor.p3_camera.P3Camera') as factory:
                camera = factory.return_value
                def fresh():
                    engine.stop.set()
                    return gray, np.zeros_like(gray, dtype=np.uint16)
                frames = iter([None, True])
                def read():
                    if next(frames) is None:
                        raise FrameMarkerMismatchError('interrupted frame')
                    return fresh()
                camera.read_frame_both.side_effect = read
                camera.dev = None
                engine.run()
                camera.connect.assert_called_once()
                self.assertEqual(engine.sequence,1)
