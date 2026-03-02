"""
TimelineRuler — step numbers, loop region overlay, playhead line.
Fixed height 36px, width dynamically matches step grids.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PyQt6.QtWidgets import QWidget

from ui.step_grid import _step_x, _total_width, STEP_W
from ui import theme

RULER_H = 36


class TimelineRuler(QWidget):
    loop_changed = pyqtSignal(int, int)   # (start, end)

    def __init__(self, total_steps: int = 16, parent=None):
        super().__init__(parent)
        self._total_steps = total_steps
        self._loop_start  = 0
        self._loop_end    = total_steps - 1
        self._playhead    = -1
        self._drag_handle: str | None = None   # "start" | "end"

        self.setFixedHeight(RULER_H)
        self._update_width()
        self.setMouseTracking(True)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_playhead(self, idx: int) -> None:
        self._playhead = idx
        self.update()

    def set_total_steps(self, n: int) -> None:
        self._total_steps = n
        self._loop_end = min(self._loop_end, n - 1)
        self._update_width()
        self.update()

    def set_loop_region(self, start: int, end: int) -> None:
        self._loop_start = start
        self._loop_end   = end
        self.update()

    # ── Sizing ────────────────────────────────────────────────────────────────

    def _update_width(self) -> None:
        w = _total_width(self._total_steps)
        self.setMinimumWidth(w)
        self.setFixedWidth(w)

    # ── Mouse — loop handle dragging ──────────────────────────────────────────

    def _step_center(self, idx: int) -> int:
        return _step_x(idx) + STEP_W // 2

    def _nearest_step(self, x: int) -> int:
        best = 0
        best_dist = abs(x - self._step_center(0))
        for i in range(1, self._total_steps):
            d = abs(x - self._step_center(i))
            if d < best_dist:
                best_dist = d
                best = i
        return best

    def mousePressEvent(self, ev) -> None:
        x = int(ev.position().x())
        cs = self._step_center(self._loop_start)
        ce = self._step_center(self._loop_end)
        if abs(x - cs) < 14:
            self._drag_handle = "start"
        elif abs(x - ce) < 14:
            self._drag_handle = "end"

    def mouseMoveEvent(self, ev) -> None:
        if self._drag_handle is None:
            return
        step = self._nearest_step(int(ev.position().x()))
        if self._drag_handle == "start":
            self._loop_start = min(step, self._loop_end)
        else:
            self._loop_end = max(step, self._loop_start)
        self.loop_changed.emit(self._loop_start, self._loop_end)
        self.update()

    def mouseReleaseEvent(self, ev) -> None:
        self._drag_handle = None

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        p.fillRect(self.rect(), QColor(theme.BG_PANEL))

        # Loop region overlay
        lx = _step_x(self._loop_start)
        rx = _step_x(self._loop_end) + STEP_W
        loop_rect = QRect(lx, 0, rx - lx, RULER_H)
        loop_color = QColor(theme.CYAN)
        loop_color.setAlpha(20)
        p.fillRect(loop_rect, loop_color)

        # Loop boundary lines
        pen = QPen(QColor(theme.CYAN))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(lx, 0, lx, RULER_H)
        p.drawLine(rx, 0, rx, RULER_H)

        # Loop handles (triangles)
        self._draw_handle(p, _step_x(self._loop_start) + STEP_W // 2, is_start=True)
        self._draw_handle(p, _step_x(self._loop_end)   + STEP_W // 2, is_start=False)

        # Step numbers
        font = QFont("Courier New", 9)
        p.setFont(font)
        for i in range(self._total_steps):
            x = _step_x(i)
            is_beat = (i % 4 == 0)
            color = QColor(theme.FG) if is_beat else QColor(theme.FG_DIM)
            p.setPen(QPen(color))
            label = str(i + 1) if is_beat else "·"
            p.drawText(QRect(x, 16, STEP_W, 18), Qt.AlignmentFlag.AlignCenter, label)

            # Beat tick mark
            if is_beat:
                p.setPen(QPen(QColor(theme.FG_DIM)))
                p.drawLine(x + STEP_W // 2, 2, x + STEP_W // 2, 14)

        # Playhead
        if 0 <= self._playhead < self._total_steps:
            px = _step_x(self._playhead) + STEP_W // 2
            pen = QPen(QColor(theme.CYAN))
            pen.setWidth(2)
            p.setPen(pen)
            p.drawLine(px, 0, px, RULER_H)

        p.end()

    def _draw_handle(self, p: QPainter, cx: int, is_start: bool) -> None:
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint
        color = QColor(theme.CYAN)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        size = 6
        if is_start:
            poly = QPolygon([
                QPoint(cx - size, 2),
                QPoint(cx + size, 2),
                QPoint(cx, 2 + size),
            ])
        else:
            poly = QPolygon([
                QPoint(cx - size, 2),
                QPoint(cx + size, 2),
                QPoint(cx, 2 + size),
            ])
        p.drawPolygon(poly)
