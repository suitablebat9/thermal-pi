"""Flush-per-request CSV measurements of the actual field viewer workload."""
import csv
import math
import select
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


class LinkLog:
    columns = ['utc', 'elapsed_s', 'status', 'sequence', 'sequence_gap',
               'payload_bytes', 'request_ms', 'decode_ms', 'player_write_ms',
               'frame_gap_ms', 'frames_total', 'payload_bytes_total',
               'average_fps', 'average_payload_kbps', 'target_fps',
               'jpeg_quality', 'demo', 'error', 'distance_ft', 'distance_m', 'segment_id',
               'segment_elapsed_s', 'segment_fps', 'segment_payload_kbps']

    def __init__(self, path, fps, quality, demo=False, distance_m=None):
        self.lock = threading.RLock()
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Never overwrite an earlier field test.
        self.stream = self.path.open('x', newline='')
        self.writer = csv.DictWriter(self.stream, fieldnames=self.columns)
        self.writer.writeheader()
        self.started = time.monotonic()
        self.segment_started = self.started
        self.segment_id = 0
        self.segment_frames = self.segment_bytes = 0
        self.last_frame = self.sequence = None
        self.frames = self.received = 0
        self.fps, self.quality, self.demo = fps, quality, demo
        self.distance_m = distance_m
        self.record('start')

    def record(self, status, sequence=None, payload_bytes=0, request_ms=0,
               decode_ms=0, player_write_ms=0, error=''):
        with self.lock:
            if not self.stream.closed:
                self._record(status, sequence, payload_bytes, request_ms, decode_ms, player_write_ms, error)

    def _record(self, status, sequence=None, payload_bytes=0, request_ms=0,
                decode_ms=0, player_write_ms=0, error=""):
        now = time.monotonic()
        elapsed = max(now-self.started, 1e-9)
        segment_elapsed = max(now-self.segment_started, 1e-9)
        gap = skipped = ''
        if status == 'frame':
            gap = '' if self.last_frame is None else round((now-self.last_frame)*1000, 3)
            skipped = '' if self.sequence is None or sequence <= self.sequence else sequence-self.sequence-1
            self.last_frame, self.sequence = now, sequence
            self.frames += 1
            self.received += payload_bytes
            self.segment_frames += 1
            self.segment_bytes += payload_bytes
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
            distance_m='' if self.distance_m is None else round(self.distance_m, 4),
            segment_id=self.segment_id, segment_elapsed_s=round(segment_elapsed, 6),
            segment_fps=round(self.segment_frames/segment_elapsed, 3),
            segment_payload_kbps=round(self.segment_bytes*8/segment_elapsed/1000, 3)))
        self.stream.flush()

    def set_distance(self, distance_m):
        if distance_m < 0 or not math.isfinite(distance_m):
            raise ValueError('Distance must be a finite nonnegative number.')
        with self.lock:
            if self.stream.closed:
                return
            self.record('distance_end')
            self.distance_m = distance_m
            self.segment_id += 1
            self.segment_started = time.monotonic()
            self.segment_frames = self.segment_bytes = 0
            self.record('distance_change')

    def close(self):
        with self.lock:
            if not self.stream.closed:
                self.record('end')
                self.stream.close()


def distance_controls(log, stop, stream, notify=print):
    """Read local distance updates even while network requests time out."""
    while not stop.is_set():
        ready, _, _ = select.select([stream], [], [], .2)
        if not ready:
            continue
        line = stream.readline()
        if not line:
            return
        value = line.strip().lower()
        if value in ('q', 'quit'):
            stop.set()
            return
        if not value:
            continue
        try:
            if value.endswith('ft'):
                meters = float(value[:-2].strip()) * .3048
            elif value.endswith('m'):
                meters = float(value[:-1].strip())
            else:
                meters = float(value) * .3048
            log.set_distance(meters)
            notify(f'Distance now {meters/.3048:g} ft / {meters:g} m (same CSV).')
        except ValueError:
            notify('Enter a nonnegative distance, e.g. 300 (feet), 300ft, or 100m. Enter q to stop.')
