import fcntl
import os
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import unittest

from werkzeug.serving import make_server
from thermal_pi.core import Engine
from thermal_pi.server import create_app


class MenuTest(unittest.TestCase):
    def test_repeated_adjustments_without_enter(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = Engine(True, folder + '/settings.json')
            server = make_server('127.0.0.1', 0, create_app(engine), threaded=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
            process = subprocess.Popen(
                [sys.executable, '-m', 'thermal_pi.menu', '--port', str(server.server_port)],
                env=dict(os.environ, TERM='xterm-256color'), stdin=slave, stdout=slave, stderr=slave)
            try:
                output = bytearray()
                sent = False
                deadline = time.monotonic() + 25
                while process.poll() is None and time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        output.extend(os.read(master, 8192))
                    if not sent and b'Quit' in output:
                        output.clear()
                        os.write(master, b'5++-b6++b2s0')
                        sent = True
                self.assertEqual(process.poll(), 0, bytes(output[-1000:]))
                self.assertEqual(engine.settings['zoom'], 1.25)
                self.assertEqual(engine.settings['rotation'], 180)
                self.assertEqual(engine.settings['palette'], 'black')
                self.assertTrue(engine.path.exists())
                self.assertNotIn(b'\x1b[2J', output)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                os.close(master)
                os.close(slave)
                server.shutdown()
                server.server_close()
