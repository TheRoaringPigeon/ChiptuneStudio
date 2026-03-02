"""
ToolbarWidget — transport controls + project management.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QSlider, QSizePolicy,
)
from PyQt6.QtCore import Qt

from ui import theme


class ToolbarWidget(QWidget):
    play_clicked      = pyqtSignal()
    stop_clicked      = pyqtSignal()
    bpm_changed       = pyqtSignal(int)
    project_new       = pyqtSignal()
    project_save      = pyqtSignal(str)       # emits current project name
    project_load      = pyqtSignal(int)       # emits project id
    project_delete    = pyqtSignal(int)       # emits project id
    left_panel_toggle = pyqtSignal()          # collapse / expand channel strip panel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Toolbar")
        self.setFixedHeight(48)
        self._project_list: list[dict] = []   # [{id, name}, ...]
        self._current_id: int | None = None
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        # Left-panel collapse/expand button
        self._panel_btn = QPushButton("◀")
        self._panel_btn.setCheckable(True)
        self._panel_btn.setFixedSize(22, 22)
        self._panel_btn.setToolTip("Collapse / expand channel panel")
        self._panel_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {theme.FG_DIM}; border: none; font-size: 13px; padding: 0; }}"
            f"QPushButton:checked {{ color: {theme.GREEN}; }}"
        )
        self._panel_btn.toggled.connect(self._on_panel_toggle)
        lay.addWidget(self._panel_btn)

        self._separator(lay)

        # App title — fixed, always visible
        title = QLabel("CHIPTUNE STUDIO")
        title.setObjectName("AppTitle")
        title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        lay.addWidget(title)

        self._separator(lay)

        # Project name — expands to fill spare space (stretch 2)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Project name...")
        self._name_edit.setMinimumWidth(70)
        lay.addWidget(self._name_edit, 2)

        # Project list — expands a little (stretch 1)
        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(70)
        self._proj_combo.currentIndexChanged.connect(self._on_combo_changed)
        lay.addWidget(self._proj_combo, 1)

        # NEW / SAVE / DEL — natural size from text, never clipped
        new_btn = QPushButton("NEW")
        new_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        new_btn.clicked.connect(self.project_new)
        lay.addWidget(new_btn)

        save_btn = QPushButton("SAVE")
        save_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        save_btn.clicked.connect(self._on_save)
        lay.addWidget(save_btn)

        del_btn = QPushButton("DEL")
        del_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        del_btn.setStyleSheet(f"color: {theme.RED}; border-color: {theme.RED};")
        del_btn.clicked.connect(self._on_delete)
        lay.addWidget(del_btn)

        self._separator(lay)

        # Play / Stop — natural size
        self._play_btn = QPushButton("▶ PLAY")
        self._play_btn.setObjectName("PlayBtn")
        self._play_btn.setCheckable(True)
        self._play_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._play_btn.clicked.connect(self._on_play)
        lay.addWidget(self._play_btn)

        stop_btn = QPushButton("■ STOP")
        stop_btn.setObjectName("StopBtn")
        stop_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        stop_btn.clicked.connect(self._on_stop)
        lay.addWidget(stop_btn)

        self._separator(lay)

        # BPM label — fixed
        bpm_lbl = QLabel("BPM")
        bpm_lbl.setStyleSheet(f"color: {theme.FG_DIM}; font-size: 11px;")
        bpm_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        lay.addWidget(bpm_lbl)

        # BPM slider — expands most aggressively (stretch 3)
        self._bpm_slider = QSlider(Qt.Orientation.Horizontal)
        self._bpm_slider.setRange(40, 300)
        self._bpm_slider.setValue(120)
        self._bpm_slider.setMinimumWidth(60)
        self._bpm_slider.valueChanged.connect(self._on_bpm_changed)
        lay.addWidget(self._bpm_slider, 3)

        # BPM readout — fixed, always 3-digit wide
        self._bpm_display = QLabel("120")
        self._bpm_display.setFixedWidth(34)
        self._bpm_display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._bpm_display.setStyleSheet(f"color: {theme.GREEN};")
        lay.addWidget(self._bpm_display)

    def _separator(self, lay: QHBoxLayout) -> None:
        from PyQt6.QtWidgets import QFrame
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {theme.BORDER};")
        sep.setFixedWidth(1)
        lay.addWidget(sep)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_panel_toggle(self, checked: bool) -> None:
        self._panel_btn.setText("▶" if checked else "◀")
        self.left_panel_toggle.emit()

    def _on_play(self) -> None:
        self._play_btn.setChecked(True)
        self.play_clicked.emit()

    def _on_stop(self) -> None:
        self._play_btn.setChecked(False)
        self.stop_clicked.emit()

    def _on_bpm_changed(self, v: int) -> None:
        self._bpm_display.setText(str(v))
        self.bpm_changed.emit(v)

    def _on_save(self) -> None:
        self.project_save.emit(self._name_edit.text().strip() or "Untitled")

    def _on_delete(self) -> None:
        if self._current_id is not None:
            self.project_delete.emit(self._current_id)

    def _on_combo_changed(self, index: int) -> None:
        if 0 <= index < len(self._project_list):
            pid = self._project_list[index]["id"]
            if pid != self._current_id:
                self._current_id = pid
                self.project_load.emit(pid)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_project_list(self, projects: list[dict]) -> None:
        self._project_list = projects
        self._proj_combo.blockSignals(True)
        self._proj_combo.clear()
        for p in projects:
            self._proj_combo.addItem(p["name"])
        self._proj_combo.blockSignals(False)

    def set_current_project(self, project: dict) -> None:
        self._current_id = project["id"]
        self._name_edit.setText(project["name"])
        self._bpm_slider.setValue(project.get("bpm", 120))

        # Select in combo
        self._proj_combo.blockSignals(True)
        for i, p in enumerate(self._project_list):
            if p["id"] == self._current_id:
                self._proj_combo.setCurrentIndex(i)
                break
        self._proj_combo.blockSignals(False)

    def set_playing(self, playing: bool) -> None:
        self._play_btn.setChecked(playing)

    def current_name(self) -> str:
        return self._name_edit.text().strip() or "Untitled"

    def current_bpm(self) -> int:
        return self._bpm_slider.value()
