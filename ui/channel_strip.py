"""
ChannelStrip — manages both the left-panel label widget and the step grid widget.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSlider, QSizePolicy,
)

from models.schemas import ChannelState
from ui.step_grid import StepGrid
from ui.channel_settings import ChannelSettingsPanel
from ui import theme

WAVEFORM_ICONS = {
    "square":   "▬",
    "triangle": "▲",
    "sawtooth": "∿",
    "noise":    "⊞",
}

LABEL_W = 200


class ChannelStrip:
    """
    Owns two widgets:
      label_widget — shown in the fixed left panel
      grid_widget  — shown in the scrollable area
    Both are kept in sync from here.
    """

    def __init__(
        self,
        live_state: ChannelState,
        settings_panel: ChannelSettingsPanel,
        channel_index: int,
    ) -> None:
        self.live_state = live_state
        self._settings_panel = settings_panel
        self._channel_index = channel_index

        self.label_widget = self._build_label_widget()
        pitched = live_state.waveform_type != "noise"
        self.grid_widget  = StepGrid(live_state.steps, channel_index, pitched=pitched)

        self.grid_widget.step_toggled.connect(self._on_step_toggled)

    # ── Label widget ──────────────────────────────────────────────────────────

    def _build_label_widget(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(LABEL_W)
        w.setFixedHeight(46)
        w.setStyleSheet(f"background-color: {theme.BG_STRIP};")

        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(4)

        # Waveform icon
        icon = QLabel(WAVEFORM_ICONS.get(self.live_state.waveform_type, "?"))
        icon.setStyleSheet(f"color: {theme.CYAN}; font-size: 16px;")
        icon.setFixedWidth(20)

        # Name
        name_lbl = QLabel(self.live_state.name)
        name_lbl.setStyleSheet(f"color: {theme.FG}; font-size: 12px;")
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Gear button
        gear_btn = QPushButton("⚙")
        gear_btn.setFixedSize(22, 22)
        gear_btn.setToolTip("Channel settings")
        gear_btn.setStyleSheet(
            f"background: transparent; color: {theme.FG_DIM}; border: none; font-size: 14px;"
            f" padding: 0;"
        )
        gear_btn.clicked.connect(self._open_settings)

        # Mute button
        self._mute_btn = QPushButton("M")
        self._mute_btn.setObjectName("MuteBtn")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setChecked(self.live_state.muted)
        self._mute_btn.setFixedSize(22, 22)
        self._mute_btn.setToolTip("Mute channel")
        self._mute_btn.toggled.connect(self._on_mute_toggled)

        # Volume slider (vertical, compact)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(int(self.live_state.volume * 100))
        self._vol_slider.setFixedWidth(50)
        self._vol_slider.setToolTip("Volume")
        self._vol_slider.valueChanged.connect(
            lambda v: setattr(self.live_state, "volume", v / 100.0)
        )

        lay.addWidget(icon)
        lay.addWidget(name_lbl, 1)
        lay.addWidget(self._vol_slider)
        lay.addWidget(gear_btn)
        lay.addWidget(self._mute_btn)

        # Store gear button ref for anchor positioning
        self._gear_btn = gear_btn
        return w

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_step_toggled(self, idx: int, active: bool) -> None:
        # Already mutated by StepGrid; just ensure live_state is consistent
        self.live_state.steps[idx].active = active

    def _on_mute_toggled(self, muted: bool) -> None:
        self.live_state.muted = muted

    def _open_settings(self) -> None:
        from PyQt6.QtGui import QCursor
        # Second click on the same gear → close
        if (self._settings_panel.isVisible()
                and self._settings_panel.owner_id == self._channel_index):
            self._settings_panel.close()
            return
        self._settings_panel.open(
            self.live_state.name,
            self.live_state.waveform_type,
            self.live_state.synth_params,
            QCursor.pos(),
            owner_id=self._channel_index,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def set_playhead(self, idx: int) -> None:
        self.grid_widget.set_playhead(idx)

    def resize_steps(self, new_count: int) -> None:
        # Extend or truncate step list
        from models.schemas import StepState
        current = len(self.live_state.steps)
        if new_count > current:
            default_pitch = self.live_state.steps[0].pitch if self.live_state.steps else 60
            for _ in range(new_count - current):
                self.live_state.steps.append(StepState(active=False, pitch=default_pitch))
        elif new_count < current:
            del self.live_state.steps[new_count:]
        self.grid_widget.resize_steps(new_count, self.live_state.steps)

    def add_locked_range(self, start: int, end: int) -> None:
        self.live_state.locked_ranges.append([start, end])
        self.grid_widget.set_locked_ranges(self.live_state.locked_ranges)

    def remove_locked_range(self, start: int, end: int) -> None:
        self.live_state.locked_ranges = [
            r for r in self.live_state.locked_ranges if r != [start, end]
        ]
        self.grid_widget.set_locked_ranges(self.live_state.locked_ranges)

    def clear_locked_ranges(self) -> None:
        self.live_state.locked_ranges = []
        self.grid_widget.set_locked_ranges([])

    def serialize(self) -> dict:
        return self.live_state.serialize()
