import io
import json
import tempfile
import time
import unittest

import numpy as np
from PIL import Image

from thermal_pi.core import DEFAULTS, Engine
from thermal_pi.field import decode
from thermal_pi.server import create_app


class FieldTest(unittest.TestCase):
    def test_native_transfer_and_local_overlays(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = Engine(config=folder+'/settings')
            frame = np.tile(np.arange(160,dtype=np.uint8),(120,1))
            temp = (18000 + frame.astype(np.uint16)*8)
            settings = dict(DEFAULTS, rotation=90, scale=True, range_on=True, spots=True)
            engine.latest = (frame, settings, False, temp)
            engine.updated, engine.error, engine.sequence = time.monotonic(), None, 12
            client = create_app(engine).test_client()
            response = client.get('/api/field-frame')
            self.assertEqual(response.status_code,200)
            info, payload = response.data.split(b'\n',1)
            meta = json.loads(info)
            self.assertEqual(Image.open(io.BytesIO(payload)).size,(120,160))
            self.assertEqual(len(meta['marks']),2)
            self.assertIsNotNone(meta['limits'])
            self.assertEqual(decode(response.data).size,(480,640))
            self.assertIsNone(engine._jpeg)
            self.assertEqual(client.get('/api/field-frame?after=12').status_code,204)
            engine.updated -= 6
            self.assertEqual(client.get('/api/field-frame').status_code,503)
