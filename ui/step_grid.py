"""
StepGrid — custom-painted step sequencer row.

Each step is a 38×38 px square; 3px gap; every 4th step gets an extra 6px gap.
States: default, active (green), playing (cyan), locked (hatched), selected (yellow).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient
)
from PyQt6.QtWidgets import QWidget

from models.schemas import StepState
from ui import theme

STEP_W    = 38
STEP_H    = 38
GAP       = 3
BEAT_EXTRA = 6   # extra gap every 4 steps (beat boundary)


def _step_x(idx: int) -> int:
    """Left edge of step `idx`."""
    beats = idx // 4
    return idx * (STEP_W + GAP) + beats * BEAT_EXTRA


def _total_width(n: int) -> int:
    if n <= 0:
        return 0
    return _step_x(n - 1) + STEP_W + GAP


class StepGrid(QWidget):
    step_toggled = pyqtSignal(int, bool)   # (step_index, new_active)

    def __init__(self, steps: list[StepState], channel_index: int, parent=None):
        super().__init__(parent)
        self._steps = steps
        self._channel_index = channel_index
        self._playhead: int = -1
        self._locked_ranges: list[list[int]] = []
        self._selected: set[int] = set()
        self._drag_start: int | None = None
        self._drag_selecting = False

        self.setFixedHeight(STEP_H + 8)
        self.setMouseTracking(True)
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

    def mousePressEvent(self, ev) -> None:
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._step_at(ev.position().x())
        if idx is None:
            return
        self._drag_start = idx
        self._drag_selecting = False

        if not self._is_locked(idx):
            self._steps[idx].active = not self._steps[idx].active
            self.step_toggled.emit(idx, self._steps[idx].active)
            self.update()

    def mouseMoveEvent(self, ev) -> None:
        if self._drag_start is None:
            return
        idx = self._step_at(ev.position().x())
        if idx is not None and idx != self._drag_start:
            self._drag_selecting = True

    def mouseReleaseEvent(self, ev) -> None:
        self._drag_start = None
        self._drag_selecting = False

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, step in enumerate(self._steps):
            x = _step_x(i)
            y = 4
            rect = QRect(x, y, STEP_W, STEP_H)

            playing  = (i == self._playhead)
            locked   = self._is_locked(i)
            selected = (i in self._selected)

            self._draw_step(p, rect, step.active, playing, locked, selected)

        p.end()

    def _draw_step(
        self,
        p: QPainter,
        rect: QRect,
        active: bool,
        playing: bool,
        locked: bool,
        selected: bool,
    ) -> None:
        # Determine colour
        if selected:
            fill = QColor(theme.YELLOW)
            border = QColor(theme.YELLOW)
        elif playing and active:
            fill = QColor(theme.CYAN)
            border = QColor(theme.CYAN)
        elif playing:
            fill = QColor("#1a3a44")
            border = QColor(theme.CYAN)
        elif active:
            fill = QColor(theme.GREEN)
            border = QColor(theme.GREEN)
        else:
            fill = QColor(theme.BG_INPUT)
            border = QColor(theme.BORDER)

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(rect, 3, 3)

        # Glow effect for active/playing
        if active or playing or selected:
            glow_color = QColor(border)
            glow_color.setAlpha(60)
            pen = QPen(glow_color)
            pen.setWidth(3)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 4, 4)

        # Border
        pen = QPen(border)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 3, 3)

        # Locked hatching
        if locked:
            hatch_color = QColor("#888888")
            hatch_color.setAlpha(120)
            pen = QPen(hatch_color)
            pen.setWidth(1)
            p.setPen(pen)
            r = rect
            spacing = 6
            for offset in range(-r.height(), r.width(), spacing):
                x1 = r.left() + offset
                y1 = r.top()
                x2 = r.left() + offset + r.height()
                y2 = r.bottom()
                p.drawLine(
                    max(x1, r.left()), max(y1, r.top()),
                    min(x2, r.right()), min(y2, r.bottom()),
                )
