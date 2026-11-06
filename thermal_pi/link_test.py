"""Flush-per-request CSV measurements of the actual field viewer workload."""
import csv
import time
from datetime import datetime, timezone
from pathlib import Path


class LinkLog:
    columns = ['utc', 'elapsed_s', 'status', 'sequence', 'sequence_gap',
               'payload_bytes', 'request_ms', 'decode_ms', 'player_write_ms',
               'frame_gap_ms', 'frames_total', 'payload_bytes_total',
               'average_fps', 'average_payload_kbps', 'target_fps',
               'jpeg_quality', 'demo', 'error', 'distance_ft', 'distance_m']

    def __init__(self, path, fps, quality, demo=False, distance_m=None):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Never overwrite an earlier field test.
        self.stream = self.path.open('x', newline='')
        self.writer = csv.DictWriter(self.stream, fieldnames=self.columns)
        self.writer.writeheader()
        self.started = time.monotonic()
        self.last_frame = self.sequence = None
        self.frames = self.received = 0
        self.fps, self.quality, self.demo = fps, quality, demo
        self.distance_m = distance_m
        self.record('start')

    def record(self, status, sequence=None, payload_bytes=0, request_ms=0,
               decode_ms=0, player_write_ms=0, error=''):
        now = time.monotonic()
        elapsed = max(now-self.started, 1e-9)
        gap = skipped = ''
        if status == 'frame':
            gap = '' if self.last_frame is None else round((now-self.last_frame)*1000, 3)
            skipped = '' if self.sequence is None or sequence <= self.sequence else sequence-self.sequence-1
            self.last_frame, self.sequence = now, sequence
            self.frames += 1
            self.received += payload_bytes
        self.writer.writerow(dict(
            utc=datetime.now(timezone.utc).isoformat(), elapsed_s=round(elapsed, 6),
            status=status, sequence=sequence, sequence_gap=skipped,
            payload_bytes=payload_bytes, request_ms=round(request_ms, 3),
            decode_ms=round(decode_ms, 3), player_write_ms=round(player_write_ms, 3),
            frame_gap_ms=gap, frames_total=self.frames, payload_bytes_total=self.received,
            average_fps=round(self.frames/elapsed, 3),
            average_payload_kbps=round(self.received*8/elapsed/1000, 3),
            target_fps=self.fps, jpeg_quality=self.quality, demo=self.demo, error=str(error),
            distance_ft='' if self.distance_m is None else round(self.distance_m/0.3048, 4),
            distance_m='' if self.distance_m is None else round(self.distance_m, 4)))
        self.stream.flush()

    def close(self):
        if not self.stream.closed:
            self.record('end')
            self.stream.close()
