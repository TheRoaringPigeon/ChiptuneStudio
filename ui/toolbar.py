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
    play_clicked    = pyqtSignal()
    stop_clicked    = pyqtSignal()
    bpm_changed     = pyqtSignal(int)
    project_new     = pyqtSignal()
    project_save    = pyqtSignal(str)       # emits current project name
    project_load    = pyqtSignal(int)       # emits project id
    project_delete  = pyqtSignal(int)       # emits project id

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
        lay.setSpacing(8)

        # App title
        title = QLabel("CHIPTUNE STUDIO")
        title.setObjectName("AppTitle")
        lay.addWidget(title)

        self._separator(lay)

        # Project name editor
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Project name...")
        self._name_edit.setFixedWidth(150)
        lay.addWidget(self._name_edit)

        # Project list
        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(120)
        self._proj_combo.currentIndexChanged.connect(self._on_combo_changed)
        lay.addWidget(self._proj_combo)

        # NEW / SAVE / DEL
        new_btn = QPushButton("NEW")
        new_btn.setFixedWidth(44)
        new_btn.clicked.connect(self.project_new)
        lay.addWidget(new_btn)

        save_btn = QPushButton("SAVE")
        save_btn.setFixedWidth(44)
        save_btn.clicked.connect(self._on_save)
        lay.addWidget(save_btn)

        del_btn = QPushButton("DEL")
        del_btn.setFixedWidth(44)
        del_btn.setStyleSheet(f"color: {theme.RED}; border-color: {theme.RED};")
        del_btn.clicked.connect(self._on_delete)
        lay.addWidget(del_btn)

        self._separator(lay)

        # Play / Stop
        self._play_btn = QPushButton("▶ PLAY")
        self._play_btn.setObjectName("PlayBtn")
        self._play_btn.setCheckable(True)
        self._play_btn.setFixedWidth(72)
        self._play_btn.clicked.connect(self._on_play)
        lay.addWidget(self._play_btn)

        stop_btn = QPushButton("■ STOP")
        stop_btn.setObjectName("StopBtn")
        stop_btn.setFixedWidth(72)
        stop_btn.clicked.connect(self._on_stop)
        lay.addWidget(stop_btn)

        self._separator(lay)

        # BPM
        bpm_lbl = QLabel("BPM")
        bpm_lbl.setStyleSheet(f"color: {theme.FG_DIM}; font-size: 11px;")
        lay.addWidget(bpm_lbl)

        self._bpm_slider = QSlider(Qt.Orientation.Horizontal)
        self._bpm_slider.setRange(40, 300)
        self._bpm_slider.setValue(120)
        self._bpm_slider.setFixedWidth(120)
        self._bpm_slider.valueChanged.connect(self._on_bpm_changed)
        lay.addWidget(self._bpm_slider)

        self._bpm_display = QLabel("120")
        self._bpm_display.setFixedWidth(32)
        self._bpm_display.setStyleSheet(f"color: {theme.GREEN};")
        lay.addWidget(self._bpm_display)

        lay.addStretch(1)

    def _separator(self, lay: QHBoxLayout) -> None:
        from PyQt6.QtWidgets import QFrame
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {theme.BORDER};")
        sep.setFixedWidth(1)
        lay.addWidget(sep)

    # ── Slots ─────────────────────────────────────────────────────────────────

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
