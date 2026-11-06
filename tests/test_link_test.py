import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from PIL import Image
from thermal_pi.field import feed
from thermal_pi.link_test import LinkLog


class Response:
    def __init__(self, status, packet=b'', sequence=1):
        self.status, self.packet = status, packet
        self.headers = {'X-Frame-Sequence': str(sequence)}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self.packet


class Player:
    def __init__(self):
        self.stdin = io.BytesIO()
        self.calls = 0

    def poll(self):
        self.calls += 1
        return None if self.calls <= 4 else 0


class LinkTest(unittest.TestCase):
    def test_real_feed_logs_frames_duplicates_outages_and_recovery(self):
        from thermal_pi.core import DEFAULTS, native_picture
        import numpy as np
        native, meta = native_picture(np.zeros((120,160), dtype=np.uint8), DEFAULTS, demo=True)
        encoded = io.BytesIO()
        native.save(encoded, format='JPEG', quality=85)
        packet = json.dumps(meta).encode()+b'\n'+encoded.getvalue()
        responses = [Response(200, packet, 10), Response(204),
                     URLError('link unavailable'), Response(200, packet, 15)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'test.csv'
            log = LinkLog(path, 25, 85, True)
            with patch('thermal_pi.field.urlopen', side_effect=responses), patch('thermal_pi.field.time.sleep'):
                feed(Player(), 1234, 25, 85, lambda message: None, log)
            with path.open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([r['status'] for r in rows],
                             ['start','frame','no_new_frame','error','frame','end'])
            self.assertEqual(rows[-1]['frames_total'], '2')
            self.assertEqual(int(rows[-1]['payload_bytes_total']), len(packet)*2)
            self.assertEqual(rows[-2]['sequence_gap'], '4')
            self.assertIn('link unavailable', rows[3]['error'])
            self.assertGreater(float(rows[-1]['average_payload_kbps']), 0)
            self.assertTrue(log.stream.closed)
            with self.assertRaises(FileExistsError):
                LinkLog(path, 25, 85)
