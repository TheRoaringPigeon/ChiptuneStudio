"""
StepGrid — custom-painted step sequencer row.

Each step is a 38×38 px square; 3px gap; every 4th step gets an extra 6px gap.
States: default, active (green), playing (cyan), locked (hatched), selected (yellow).

Pitch editing:
  • Hover over any step → widget grabs keyboard focus.
  • Press a–g        → assign that natural note at octave 4, activate the step.
  • Scroll wheel     → shift the hovered step up/down one octave (±12 semitones).
  • Note name (e.g. "C4") is drawn on every active step.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush,
)
from PyQt6.QtWidgets import QWidget

from models.schemas import StepState
from ui import theme

STEP_W     = 38
STEP_H     = 38
GAP        = 3
BEAT_EXTRA = 6   # extra gap every 4 steps

# ── Note helpers ──────────────────────────────────────────────────────────────

NOTE_NAMES   = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_KEYS    = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
DEFAULT_OCT  = 4   # note-key presses land on octave 4 (C4 = MIDI 60)


def midi_to_name(pitch: int) -> str:
    pitch  = max(0, min(127, pitch))
    name   = NOTE_NAMES[pitch % 12]
    octave = (pitch // 12) - 1
    return f"{name}{octave}"


# ── Layout helpers (also imported by sequencer_view / timeline_ruler) ─────────

def _step_x(idx: int) -> int:
    beats = idx // 4
    return idx * (STEP_W + GAP) + beats * BEAT_EXTRA


def _total_width(n: int) -> int:
    if n <= 0:
        return 0
    return _step_x(n - 1) + STEP_W + GAP


# ── Widget ────────────────────────────────────────────────────────────────────

class StepGrid(QWidget):
    step_toggled = pyqtSignal(int, bool)   # (step_index, new_active)

    def __init__(self, steps: list[StepState], channel_index: int,
                 pitched: bool = True, parent=None):
        super().__init__(parent)
        self._steps         = steps
        self._channel_index = channel_index
        self._pitched       = pitched   # False for noise / unpitched channels
        self._playhead: int = -1
        self._locked_ranges: list[list[int]] = []
        self._selected: set[int]  = set()
        self._hovered_step: int | None = None

        # Vestigial drag state (kept so external code that reads these doesn't break)
        self._drag_start: int | None = None
        self._drag_selecting = False

        self.setFixedHeight(STEP_H + 8)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._update_width()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_playhead(self, idx: int) -> None:
        self._playhead = idx
        self.update()

    def set_locked_ranges(self, ranges: list) -> None:
        self._locked_ranges = [list(r) for r in ranges]
        self.update()

    def set_selected(self, selected: set[int]) -> None:
        self._selected = set(selected)
        self.update()

    def resize_steps(self, new_count: int, steps: list[StepState]) -> None:
        self._steps = steps
        self._update_width()
        self.update()

    # ── Sizing ────────────────────────────────────────────────────────────────

    def _update_width(self) -> None:
        w = _total_width(len(self._steps))
        self.setMinimumWidth(w)
        self.setFixedWidth(w)

    def sizeHint(self) -> QSize:
        return QSize(_total_width(len(self._steps)), STEP_H + 8)

    # ── Hit testing ───────────────────────────────────────────────────────────

    def _step_at(self, x: int) -> int | None:
        for i in range(len(self._steps)):
            sx = _step_x(i)
            if sx <= x < sx + STEP_W:
                return i
        return None

    def _is_locked(self, idx: int) -> bool:
        for r in self._locked_ranges:
            if len(r) >= 2 and r[0] <= idx <= r[1]:
                return True
        return False

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def enterEvent(self, ev) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().enterEvent(ev)

    def leaveEvent(self, ev) -> None:
        if self._hovered_step is not None:
            self._hovered_step = None
            self.update()
        super().leaveEvent(ev)

    def mousePressEvent(self, ev) -> None:
        # Press is consumed by the SequencerView event filter; this fires only
        # when no filter is installed (e.g. in isolation tests).
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._step_at(ev.position().x())
        if idx is None:
            return
        if not self._is_locked(idx):
            self._steps[idx].active = not self._steps[idx].active
            self.step_toggled.emit(idx, self._steps[idx].active)
            self.update()

    def mouseMoveEvent(self, ev) -> None:
        idx = self._step_at(ev.position().x())
        if idx != self._hovered_step:
            self._hovered_step = idx
            self.update()

    def mouseReleaseEvent(self, ev) -> None:
        self._drag_start     = None
        self._drag_selecting = False

    # ── Keyboard — note assignment ─────────────────────────────────────────────

    def keyPressEvent(self, ev) -> None:
        idx = self._hovered_step
        if idx is not None and self._pitched:
            key = ev.text().lower()
            if key in NOTE_KEYS:
                semitone = NOTE_KEYS[key]
                pitch    = (DEFAULT_OCT + 1) * 12 + semitone   # e.g. C4 = 60
                self._steps[idx].pitch = pitch
                if not self._steps[idx].active and not self._is_locked(idx):
                    self._steps[idx].active = True
                    self.step_toggled.emit(idx, True)
                self.update()
                return
        super().keyPressEvent(ev)

    # ── Scroll wheel — octave shift ────────────────────────────────────────────

    def wheelEvent(self, ev) -> None:
        idx = self._hovered_step
        if idx is not None and self._pitched:
            delta = ev.angleDelta().y()
            if delta > 0:
                self._steps[idx].pitch = min(127, self._steps[idx].pitch + 12)
            elif delta < 0:
                self._steps[idx].pitch = max(0,   self._steps[idx].pitch - 12)
            self.update()
            ev.accept()
            return
        super().wheelEvent(ev)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, step in enumerate(self._steps):
            rect     = QRect(_step_x(i), 4, STEP_W, STEP_H)
            playing  = (i == self._playhead)
            locked   = self._is_locked(i)
            selected = (i in self._selected)
            hovered  = (i == self._hovered_step)
            self._draw_step(p, rect, step, playing, locked, selected, hovered)

        p.end()

    def _draw_step(
        self,
        p: QPainter,
        rect: QRect,
        step: StepState,
        playing: bool,
        locked: bool,
        selected: bool,
        hovered: bool,
    ) -> None:
        active = step.active

        # ── Fill colour ───────────────────────────────────────────────────────
        if selected:
            fill   = QColor(theme.YELLOW)
            border = QColor(theme.YELLOW)
        elif playing and active:
            fill   = QColor(theme.CYAN)
            border = QColor(theme.CYAN)
        elif playing:
            fill   = QColor("#1a3a44")
            border = QColor(theme.CYAN)
        elif active:
            fill   = QColor(theme.GREEN)
            border = QColor(theme.GREEN)
        else:
            fill   = QColor(theme.BG_INPUT)
            border = QColor(theme.BORDER)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(rect, 3, 3)

        # ── Glow ──────────────────────────────────────────────────────────────
        if active or playing or selected:
            gc = QColor(border)
            gc.setAlpha(60)
            pen = QPen(gc)
            pen.setWidth(3)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 4, 4)

        # ── Border ────────────────────────────────────────────────────────────
        pen = QPen(border)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 3, 3)

        # ── Hover highlight (inactive steps only) ─────────────────────────────
        if hovered and not active and not selected:
            hc = QColor(theme.FG_DIM)
            hc.setAlpha(160)
            pen = QPen(hc)
            pen.setWidth(2)
            p.setPen(pen)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 3, 3)

        # ── Note name on active steps (pitched channels only) ────────────────
        if active and self._pitched:
            label = midi_to_name(step.pitch)
            # Dark text on bright fill; lighter on cyan (playing)
            txt_color = QColor("#003322") if not playing else QColor("#003344")
            if selected:
                txt_color = QColor("#554400")
            p.setPen(QPen(txt_color))
            p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        # ── Locked hatching ───────────────────────────────────────────────────
        if locked:
            hatch = QColor("#888888")
            hatch.setAlpha(120)
            pen = QPen(hatch)
            pen.setWidth(1)
            p.setPen(pen)
            spacing = 6
            for offset in range(-rect.height(), rect.width(), spacing):
                x1 = rect.left() + offset
                x2 = rect.left() + offset + rect.height()
                p.drawLine(
                    max(x1, rect.left()), rect.top(),
                    min(x2, rect.right()), rect.bottom(),
                )
