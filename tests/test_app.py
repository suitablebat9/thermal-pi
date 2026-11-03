import io
import json
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from PIL import Image
from thermal_pi.core import Engine, DEFAULTS, render, validated
from thermal_pi.server import create_app

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = Engine(True, str(Path(self.tmp.name)/'settings.json'))
        self.client = create_app(self.engine).test_client()
    def tearDown(self):
        self.engine.stop.set()
        if self.engine.thread.is_alive():
            self.engine.thread.join(3)
        self.tmp.cleanup()
    def wait_live(self):
        self.engine.thread.start()
        end=time.monotonic()+3
        while not self.engine.status()['connected'] and time.monotonic()<end:
            time.sleep(.02)
        self.assertTrue(self.engine.status()['connected'])
    def test_validation(self):
        for patch in ({'zoom':0},{'zoom':float('nan')},{'rotation':45},{'flip':'yes'},{'palette':'bad'},{'unknown':1}):
            self.assertEqual(self.client.post('/api/settings',json=patch).status_code,400)
        self.assertEqual(self.client.post('/api/settings',json={'gain':'low'}).status_code,400)
    def test_save_restore(self):
        self.client.post('/api/settings',json={'palette':'black','rotation':90,'zoom':2})
        self.assertEqual(self.client.post('/api/save',json={}).status_code,200)
        loaded=Engine(True,str(self.engine.path))
        self.assertEqual(loaded.settings,self.engine.settings)
    def test_orientation_palette(self):
        frame=np.tile(np.arange(160,dtype='uint8'),(120,1))
        white=Image.open(io.BytesIO(render(frame,DEFAULTS)))
        black=Image.open(io.BytesIO(render(frame,dict(DEFAULTS,palette='black'))))
        rotated=Image.open(io.BytesIO(render(frame,dict(DEFAULTS,rotation=90))))
        self.assertEqual(rotated.size,(480,640))
        self.assertLess(sum(white.getpixel((0,0))),sum(black.getpixel((0,0))))
    def test_live_stream_and_hardware_queue(self):
        self.wait_live()
        response=self.client.get('/stream.mjpg',buffered=False)
        chunk=next(response.response)
        self.assertIn(b'Content-Type: image/jpeg',chunk)
        Image.open(io.BytesIO(chunk.split(b'\r\n\r\n',1)[1][:-2])).verify()
        response.close()
        self.assertEqual(self.client.post('/api/command',json={'action':'low'}).status_code,202)
        end=time.monotonic()+2
        while self.engine.status()['settings']['gain']!='low' and time.monotonic()<end:
            time.sleep(.02)
        self.assertEqual(self.engine.status()['settings']['gain'],'low')
        self.assertIn('Simulated',self.engine.status()['command'])
    def test_stale_and_disconnected(self):
        self.assertFalse(self.engine.status()['connected'])
        self.assertEqual(self.client.post('/api/command',json={'action':'shutter'}).status_code,400)
        self.engine.updated=time.monotonic()-3
        self.engine.error=None
        self.assertFalse(self.engine.status()['connected'])
    def test_local_request_boundary(self):
        self.assertEqual(self.client.post('/api/save',json={},headers={'Origin':'https://other.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/status',headers={'Host':'other.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/save',data='{}').status_code,403)

if __name__=='__main__': unittest.main()
