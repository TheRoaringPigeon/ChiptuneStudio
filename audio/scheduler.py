"""
Sequencer — look-ahead step scheduler (mirrors Chris Wilson's pattern).

The scheduler runs a daemon thread that wakes every 25 ms and schedules any
notes whose step falls within the next 100 ms lookahead window.

Cross-thread UI updates use SequencerSignals(QObject) with Qt queued connections.
"""

from __future__ import annotations

import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal

from audio.engine import AudioEngine, SAMPLE_RATE
from audio.synth import render_note
from models.schemas import ChannelState

LOOKAHEAD_S   = 0.100   # 100 ms look-ahead
SCHEDULE_HZ   = 0.025   # wake every 25 ms


class SequencerSignals(QObject):
    step_changed = pyqtSignal(int)   # emitted from audio thread → Qt queued to UI


class Sequencer:
    """
    Not a QObject — runs a daemon thread.
    Communicates with UI via SequencerSignals (queued cross-thread signals).
    """

    def __init__(self, engine: AudioEngine) -> None:
        self.engine = engine
        self.signals = SequencerSignals()

        self.bpm: int = 120
        self.total_steps: int = 16
        self.loop_start: int = 0
        self.loop_end: int = 15
        self.channels: list[ChannelState] = []

        self._playing = False
        self._thread: threading.Thread | None = None
        self._current_step: int = 0
        self._next_step_sample: int = 0   # absolute sample when _current_step fires

    # ── Public API ─────────────────────────────────────────────────────────────

    def play(self) -> None:
        if self._playing:
            return
        self._playing = True
        self._current_step = self.loop_start
        self._next_step_sample = self.engine.current_sample
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._playing = False
        # Thread checks _playing and exits naturally

    # ── Private loop (daemon thread) ──────────────────────────────────────────

    def _step_duration_samples(self) -> int:
        """Samples per step = (60 / BPM) / 4 * SR  (16th-note steps)."""
        step_s = (60.0 / max(1, self.bpm)) / 4.0
        return int(step_s * SAMPLE_RATE)

    def _loop(self) -> None:
        while self._playing:
            self._schedule()
            time.sleep(SCHEDULE_HZ)

    def _schedule(self) -> None:
        lookahead_samples = int(LOOKAHEAD_S * SAMPLE_RATE)
        horizon = self.engine.current_sample + lookahead_samples

        while self._next_step_sample < horizon and self._playing:
            step = self._current_step
            self._fire_step(step, self._next_step_sample)

            # Advance
            step_dur = self._step_duration_samples()
            self._next_step_sample += step_dur

            # Advance step (loop within loop region)
            next_step = step + 1
            if next_step > self.loop_end:
                next_step = self.loop_start
            self._current_step = next_step

            # Notify UI (queued cross-thread)
            self.signals.step_changed.emit(step)

    def _fire_step(self, step_idx: int, start_sample: int) -> None:
        step_dur_s = (60.0 / max(1, self.bpm)) / 4.0

        for ch in list(self.channels):  # snapshot so UI mutations don't corrupt iteration
            if ch.muted:
                continue
            if step_idx >= len(ch.steps):
                continue
            step = ch.steps[step_idx]
            if not step.active:
                continue

            samples = render_note(
                waveform_type=ch.waveform_type,
                midi_pitch=step.pitch,
                duration_s=step_dur_s * 0.9,   # slight gap
                volume=ch.volume,
                pan=ch.pan,
                velocity=step.velocity,
                params=ch.synth_params,
            )
            self.engine.schedule_note(samples, start_sample)
