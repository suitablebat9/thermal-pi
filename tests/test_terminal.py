import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time
import unittest
import fcntl
import threading
from werkzeug.serving import make_server
from thermal_pi.core import Engine
from thermal_pi.server import create_app


class TerminalTest(unittest.TestCase):
    def test_demo_keys_and_exit_in_a_terminal(self):
        engine = Engine(demo=True, config=os.devnull + '/unused')
        server = make_server('127.0.0.1', 0, create_app(engine), threaded=True)
        engine.thread.start()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH',24,80,0,0))
        code = 'from thermal_pi.terminal import view; view(%d, True)' % server.server_port
        process = subprocess.Popen([sys.executable, '-c', code], stdin=slave, stdout=slave, stderr=slave)
        def wait_for(predicate):
            output = bytearray()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    output.extend(os.read(master, 65536))
                if predicate(output):
                    return
            self.fail('Terminal output did not reach expected state')
        try:
            wait_for(lambda output: '▀'.encode() in output)
            os.write(master, b'2')
            wait_for(lambda _: engine.status()['settings']['palette'] == 'black')
            os.write(master, b'q')
            wait_for(lambda output: b'\x1b[?1049l' in output)
            self.assertEqual(process.wait(timeout=3), 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)
            server.shutdown()
            server.server_close()
            engine.stop.set()
            engine.thread.join(3)
