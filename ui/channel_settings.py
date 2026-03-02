"""
ChannelSettingsPanel — floating frameless popup for per-channel synth params.

Opens near the gear button; dismissed by clicking outside or pressing X.
Directly mutates `synth_params` dict so the scheduler picks up changes
on the very next note render.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QEvent, QObject, QPoint, QRect
from PyQt6.QtGui import QFocusEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QPushButton, QFrame, QApplication,
)

from ui import theme


class _SectionLabel(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("SectionHeader")


class _SliderRow(QWidget):
    def __init__(self, label: str, min_v: float, max_v: float, step: float,
                 value: float, format_fn, on_change, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(54)
        lbl.setStyleSheet(f"color: {theme.FG_DIM}; font-size: 11px;")

        steps = max(1, int((max_v - min_v) / step))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, steps)
        slider.setValue(int((value - min_v) / step))
        slider.setFixedHeight(18)

        val_lbl = QLabel(format_fn(value))
        val_lbl.setFixedWidth(60)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_lbl.setStyleSheet(f"color: {theme.GREEN}; font-size: 11px;")

        def _changed(v: int) -> None:
            real = min_v + v * step
            on_change(real)
            val_lbl.setText(format_fn(real))

        slider.valueChanged.connect(_changed)

        lay.addWidget(lbl)
        lay.addWidget(slider, 1)
        lay.addWidget(val_lbl)


class ChannelSettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("ChannelSettingsPanel")
        self.setMinimumWidth(300)
        self.hide()

        self._main_lay = QVBoxLayout(self)
        self._main_lay.setContentsMargins(8, 6, 8, 8)
        self._main_lay.setSpacing(4)

        self.owner_id: int | None = None   # channel index that opened the panel

    # ── Public API ────────────────────────────────────────────────────────────

    def open(self, name: str, waveform_type: str, synth_params: dict,
             cursor_pos: QPoint, owner_id: int | None = None) -> None:
        """Populate controls and show down-right of cursor_pos, clamped to the main window."""
        self.owner_id = owner_id
        self._clear()
        self._build(name, waveform_type, synth_params)
        self.adjustSize()
        self._position(cursor_pos)
        self.show()
        self.raise_()
        self.activateWindow()
        # Watch for outside clicks on the whole application
        QApplication.instance().installEventFilter(self)

    def close(self) -> None:
        self.hide()
        self.owner_id = None
        QApplication.instance().removeEventFilter(self)

    # ── Outside-click dismissal ───────────────────────────────────────────────

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent):
            gpos = event.globalPosition().toPoint()
            if not self.geometry().contains(gpos):
                self.close()
        return False

    # ── Layout helpers ────────────────────────────────────────────────────────

    def _clear(self) -> None:
        while self._main_lay.count():
            item = self._main_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build(self, name: str, waveform_type: str, params: dict) -> None:
        is_osc       = waveform_type not in ("noise",)
        is_square    = waveform_type == "square"
        is_fm        = waveform_type == "fm"
        is_wavetable = waveform_type == "wavetable"
        # Vibrato / sweep make sense for continuous-phase oscillators only
        has_mod = waveform_type not in ("noise", "wavetable")

        # Header
        hdr = QWidget()
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        title = QLabel(f"{name.upper()} PARAMS")
        title.setStyleSheet(f"color: {theme.GREEN}; font-weight: bold; font-size: 12px;")
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            f"background: transparent; color: {theme.FG_DIM}; border: none; font-size: 16px;"
        )
        close_btn.clicked.connect(self.close)
        hdr_lay.addWidget(title, 1)
        hdr_lay.addWidget(close_btn)
        self._main_lay.addWidget(hdr)

        self._separator()

        # ENVELOPE
        self._section("ENVELOPE")
        self._slider("ATK",  0.001, 2.0,   0.001, params.get("attack",   0.002), lambda v: f"{int(v*1000)}ms",  lambda v: params.update({"attack":   v}))
        self._slider("DEC",  0.001, 2.0,   0.001, params.get("decay",    0.08),  lambda v: f"{int(v*1000)}ms",  lambda v: params.update({"decay":    v}))
        self._slider("SUS",  0.0,   1.0,   0.01,  params.get("sustain",  0.8),   lambda v: f"{int(v*100)}%",    lambda v: params.update({"sustain":  v}))
        self._slider("REL",  0.001, 3.0,   0.001, params.get("release",  0.05),  lambda v: f"{int(v*1000)}ms",  lambda v: params.update({"release":  v}))

        # FILTER — placed early so the type dropdown never falls below the panel bottom
        self._section("FILTER")
        self._filter_type_row(params)
        self._slider("FREQ", 20, 20000, 1,   params.get("filterFreq", 2000), lambda v: f"{int(v)}Hz", lambda v: params.update({"filterFreq": v}))
        self._slider("Q",    0.1, 20,   0.1, params.get("filterQ",    1.0),  lambda v: f"{v:.1f}",    lambda v: params.update({"filterQ":    v}))

        # FM — 2-operator controls (fm only)
        if is_fm:
            self._section("FM")
            self._slider("RATIO", 0.5, 8.0, 0.5, params.get("fmRatio", 1.0),
                         lambda v: f"{v:.1f}x", lambda v: params.update({"fmRatio": v}))
            self._slider("INDEX", 0.0, 10.0, 0.1, params.get("fmIndex", 1.0),
                         lambda v: f"{v:.1f}",  lambda v: params.update({"fmIndex": v}))

        # WAVETABLE preset selector (wavetable only)
        if is_wavetable:
            from audio.synth import WAVETABLE_PRESET_NAMES
            self._section("WAVETABLE")
            self._slider(
                "PRESET", 0, len(WAVETABLE_PRESET_NAMES) - 1, 1,
                params.get("wavetablePreset", 0),
                lambda v: WAVETABLE_PRESET_NAMES[int(round(v))],
                lambda v: params.update({"wavetablePreset": int(round(v))}),
            )

        # TONE (square only)
        if is_square:
            self._section("TONE")
            self._slider("DUTY", 0.1, 0.9, 0.01, params.get("dutyCycle", 0.5), lambda v: f"{int(v*100)}%", lambda v: params.update({"dutyCycle": v}))

        # PITCH — detune / transpose (all oscillators and wavetable)
        if is_osc or is_wavetable:
            self._section("PITCH")
            self._slider("DETUNE", -100, 100, 1, params.get("detune",    0), lambda v: f"{'+' if v>=0 else ''}{int(v)}¢",  lambda v: params.update({"detune":    v}))
            self._slider("XPOSE",  -24,  24,  1, params.get("transpose", 0), lambda v: f"{'+' if v>=0 else ''}{int(v)}st", lambda v: params.update({"transpose": v}))

        # VIBRATO (continuous-phase oscillators only)
        if has_mod:
            self._section("VIBRATO")
            self._slider("RATE",  0, 20,  0.1, params.get("vibratoRate",  0), lambda v: f"{v:.1f}Hz", lambda v: params.update({"vibratoRate":  v}))
            self._slider("DEPTH", 0, 200, 1,   params.get("vibratoDepth", 0), lambda v: f"{int(v)}¢",  lambda v: params.update({"vibratoDepth": v}))

        # SWEEP (continuous-phase oscillators only)
        if has_mod:
            self._section("SWEEP")
            self._slider("AMT",  -24, 24,  1,     params.get("sweepAmount", 0),   lambda v: f"{'+' if v>=0 else ''}{int(v)}st", lambda v: params.update({"sweepAmount": v}))
            self._slider("TIME",  0,  0.5, 0.001, params.get("sweepTime",   0.1), lambda v: f"{int(v*1000)}ms",                  lambda v: params.update({"sweepTime":   v}))

    def _section(self, label: str) -> None:
        sep = _SectionLabel(label)
        sep.setContentsMargins(0, 6, 0, 2)
        self._main_lay.addWidget(sep)

    def _separator(self) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {theme.BORDER};")
        self._main_lay.addWidget(line)

    def _slider(self, label: str, min_v: float, max_v: float, step: float,
                value: float, fmt_fn, on_change) -> None:
        row = _SliderRow(label, min_v, max_v, step, value, fmt_fn, on_change)
        self._main_lay.addWidget(row)

    def _filter_type_row(self, params: dict) -> None:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lbl = QLabel("TYPE")
        lbl.setFixedWidth(54)
        lbl.setStyleSheet(f"color: {theme.FG_DIM}; font-size: 11px;")

        combo = QComboBox()
        for opt in ("none", "lowpass", "highpass", "bandpass"):
            combo.addItem(opt)
        current = params.get("filterType", "none")
        idx = combo.findText(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)

        combo.currentTextChanged.connect(lambda t: params.update({"filterType": t}))

        lay.addWidget(lbl)
        lay.addWidget(combo, 1)
        self._main_lay.addWidget(row)

    # ── Positioning ───────────────────────────────────────────────────────────

    def _position(self, cursor_pos: QPoint) -> None:
        pw = self.width()
        ph = self.height()

        # Start down-right of the cursor
        left = cursor_pos.x() + 12
        top  = cursor_pos.y() + 12

        # Clamp to the main window rect so the panel never leaves the window
        win = QApplication.activeWindow()
        if win is not None:
            wr = win.geometry()
        else:
            wr = QApplication.primaryScreen().availableGeometry()

        left = min(left, wr.right()  - pw - 4)
        left = max(left, wr.left()   + 4)
        top  = min(top,  wr.bottom() - ph - 4)
        top  = max(top,  wr.top()    + 4)

        self.move(left, top)

    # ── Dismiss on outside click ──────────────────────────────────────────────

    def focusOutEvent(self, ev: QFocusEvent) -> None:
        # Don't auto-hide on focus-out — use explicit close button or outside click
        super().focusOutEvent(ev)
