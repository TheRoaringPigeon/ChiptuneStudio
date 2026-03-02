"""
AudioEngine — sounddevice OutputStream wrapper.

The audio callback runs on a high-priority audio thread. All scheduling must
be done from other threads via schedule_note(); the callback just mixes.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100
CHANNELS = 2
DTYPE = "float32"


@dataclass
class NoteEvent:
    samples: np.ndarray   # (N, 2) float32
    start_sample: int     # absolute stream position to begin mixing
    read_pos: int = 0     # next unread sample index within `samples`


class AudioEngine:
    def __init__(self) -> None:
        self._stream: sd.OutputStream | None = None
        self._events: list[NoteEvent] = []
        self._lock = threading.Lock()
        self._position: int = 0  # absolute sample counter

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._stream is not None:
            return
        self._position = 0
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=256,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
        with self._lock:
            self._events.clear()

    def schedule_note(self, samples: np.ndarray, start_sample: int) -> None:
        """Thread-safe: enqueue a pre-rendered note for playback."""
        event = NoteEvent(samples=samples, start_sample=start_sample)
        with self._lock:
            self._events.append(event)

    @property
    def current_sample(self) -> int:
        return self._position

    # ── Callback (audio thread) ───────────────────────────────────────────────

    def _callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time,       # noqa: ANN001
        status,     # noqa: ANN001
    ) -> None:
        outdata.fill(0.0)
        buf_start = self._position
        buf_end = buf_start + frames

        finished: list[NoteEvent] = []

        with self._lock:
            for event in self._events:
                note_start = event.start_sample
                note_end = note_start + len(event.samples)

                # Not yet reached
                if note_start >= buf_end:
                    continue
                # Already finished
                if note_end <= buf_start:
                    finished.append(event)
                    continue

                # Overlap region
                out_begin = max(note_start, buf_start) - buf_start
                out_end   = min(note_end,   buf_end)   - buf_start

                src_begin = event.read_pos
                src_len   = out_end - out_begin
                src_end   = src_begin + src_len

                outdata[out_begin:out_begin + src_len] += event.samples[src_begin:src_end]
                event.read_pos += src_len

                if note_end <= buf_end:
                    finished.append(event)

            for ev in finished:
                try:
                    self._events.remove(ev)
                except ValueError:
                    pass

        # Soft clip to [-1, 1]
        np.clip(outdata, -1.0, 1.0, out=outdata)
        self._position += frames
