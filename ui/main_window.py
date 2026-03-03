"""
MainWindow — wires all components together.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMessageBox

from database import Session, init_db
from models.db import Project, Pattern, Channel, Step
from models.schemas import (
    ChannelState, ProjectState, StepState,
    DEFAULT_SYNTH_PARAMS, WAVEFORM_DEFAULT_PARAMS,
)
import plugins.chiptune   # noqa: F401 — triggers register()
import plugins.drum_kit   # noqa: F401 — triggers register()
import plugins.synth_lead  # noqa: F401 — triggers register()
from audio.engine import AudioEngine
from audio.scheduler import Sequencer
from ui.toolbar import ToolbarWidget
from ui.sequencer_view import SequencerView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChiptuneStudio")
        self.resize(1200, 600)

        self._engine = AudioEngine()
        self._scheduler = Sequencer(self._engine)
        self._current_project_id: int | None = None

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        vlay = QVBoxLayout(central)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # Toolbar
        self._toolbar = ToolbarWidget()
        vlay.addWidget(self._toolbar)

        # Placeholder sequencer view (replaced on project load)
        self._seq_view: SequencerView | None = None
        self._seq_container = QWidget()
        self._seq_container_lay = QVBoxLayout(self._seq_container)
        self._seq_container_lay.setContentsMargins(0, 0, 0, 0)
        vlay.addWidget(self._seq_container, 1)

        # Status bar
        self.statusBar().showMessage("Starting...")

        # Left-panel collapse state (preserved across project loads)
        self._panel_collapsed: bool = False

        # Wire toolbar signals
        self._toolbar.play_clicked.connect(self._on_play)
        self._toolbar.stop_clicked.connect(self._on_stop)
        self._toolbar.bpm_changed.connect(self._on_bpm_changed)
        self._toolbar.project_new.connect(self._on_project_new)
        self._toolbar.project_save.connect(self._on_project_save)
        self._toolbar.project_load.connect(self._on_project_load)
        self._toolbar.project_delete.connect(self._on_project_delete)
        self._toolbar.left_panel_toggle.connect(self._on_left_panel_toggle)

        # Wire scheduler → UI (queued cross-thread)
        self._scheduler.signals.step_changed.connect(
            self._on_step_changed, Qt.ConnectionType.QueuedConnection
        )

        # Boot
        self._boot()

    # ── Boot ──────────────────────────────────────────────────────────────────

    def _boot(self) -> None:
        init_db()
        self._engine.start()

        projects = self._load_project_list()
        if not projects:
            self._create_default_project()
            projects = self._load_project_list()

        self._toolbar.set_project_list(projects)
        if projects:
            self._load_project(projects[0]["id"])

        self.statusBar().showMessage("Ready")

    # ── Project list helpers ──────────────────────────────────────────────────

    def _load_project_list(self) -> list[dict]:
        with Session() as s:
            rows = s.query(Project).order_by(Project.id).all()
            return [{"id": r.id, "name": r.name} for r in rows]

    def _create_default_project(self) -> None:
        """Create a new project pre-loaded with an ocean-waves pattern."""
        BPM   = 65
        STEPS = 32

        # ── Step patterns: list of (active, velocity) per step ────────────────
        #
        # Two wave cycles across 32 steps (~7.4 s per loop at BPM 65).
        # Velocity shapes the wave build / peak / recession envelope.

        # Wave 1: build steps 0-7 → peak 8 → recede 9-13 → silence 14-15
        # Wave 2: build steps 17-22 → peak 23-24 → recede 25-29 → silence 30-31
        crash = [
            (True,  30), (True,  45), (True,  60), (True,  75),  # 0-3  build
            (True,  90), (True, 105), (True, 115), (True, 122),  # 4-7  build
            (True, 127), (True, 118), (True, 100), (True,  80),  # 8-11 peak→recede
            (True,  58), (True,  35), (False,  0), (False,  0),  # 12-15 recede→quiet
            (False,  0), (True,  28), (True,  44), (True,  62),  # 16-19 quiet→build
            (True,  80), (True,  98), (True, 112), (True, 122),  # 20-23 build
            (True, 127), (True, 114), (True,  94), (True,  72),  # 24-27 peak→recede
            (True,  50), (True,  28), (False,  0), (False,  0),  # 28-31 recede→quiet
        ]

        # Foam fires after each wave peak as the wave washes back
        foam = [
            (False, 0), (False, 0), (False, 0), (False, 0),   # 0-3
            (False, 0), (False, 0), (False, 0), (False, 0),   # 4-7
            (False, 0), (True, 70), (True, 90), (True, 85),   # 8-10 (foam starts at peak)
            (True, 68), (True, 45), (True, 25), (False, 0),   # 11-15
            (False, 0), (False, 0), (False, 0), (False, 0),   # 16-19
            (False, 0), (False, 0), (False, 0), (False, 0),   # 20-23
            (False, 0), (True, 65), (True, 88), (True, 80),   # 24-26
            (True, 60), (True, 38), (True, 20), (False, 0),   # 27-31
        ]

        # Ambient wash: constant background at low velocity
        wash  = [(True, 42)] * STEPS

        # Deep swell: continuous sub-bass drone, all steps active
        swell = [(True, 62)] * STEPS

        # ── Channel definitions ────────────────────────────────────────────────
        channels = [
            {
                "name":         "Deep Swell",
                "waveform":     "sine",
                "volume":       0.50,
                "pan":          0.0,
                "pitch":        33,   # A1 — deep sub-bass
                "steps":        [(a, 33, v) for a, v in swell],
                "params": {
                    **DEFAULT_SYNTH_PARAMS,
                    "attack":       0.02,
                    "decay":        0.04,
                    "sustain":      0.90,
                    "release":      0.06,
                    "filterType":   "lowpass",
                    "filterFreq":   155,
                    "filterQ":      1.0,
                    "vibratoRate":  0.15,
                    "vibratoDepth": 4,
                },
            },
            {
                "name":     "Wave Crash",
                "waveform": "noise",
                "volume":   0.82,
                "pan":      0.0,
                "pitch":    60,
                "steps":    [(a, 60, v) for a, v in crash],
                "params": {
                    **DEFAULT_SYNTH_PARAMS,
                    "attack":     0.010,
                    "decay":      0.09,
                    "sustain":    0.55,
                    "release":    0.05,
                    "filterType": "lowpass",
                    "filterFreq": 580,
                    "filterQ":    1.2,
                },
            },
            {
                "name":     "Foam & Spray",
                "waveform": "noise",
                "volume":   0.55,
                "pan":      0.0,
                "pitch":    60,
                "steps":    [(a, 60, v) for a, v in foam],
                "params": {
                    **DEFAULT_SYNTH_PARAMS,
                    "attack":     0.04,
                    "decay":      0.10,
                    "sustain":    0.40,
                    "release":    0.06,
                    "filterType": "highpass",
                    "filterFreq": 2800,
                    "filterQ":    1.5,
                },
            },
            {
                "name":     "Ambient Wash",
                "waveform": "noise",
                "volume":   0.38,
                "pan":      0.0,
                "pitch":    60,
                "steps":    [(a, 60, v) for a, v in wash],
                "params": {
                    **DEFAULT_SYNTH_PARAMS,
                    "attack":     0.015,
                    "decay":      0.05,
                    "sustain":    0.80,
                    "release":    0.04,
                    "filterType": "bandpass",
                    "filterFreq": 750,
                    "filterQ":    0.8,
                },
            },
        ]

        with Session() as s:
            proj = Project(
                name="Ocean Waves",
                plugin_id="chiptune",
                bpm=BPM,
                steps_per_pattern=STEPS,
                loop_start=0,
                loop_end=STEPS - 1,
            )
            s.add(proj)
            s.flush()

            pattern = Pattern(project_id=proj.id, name="Pattern 1", order_index=0)
            s.add(pattern)
            s.flush()

            for ch_def in channels:
                ch = Channel(
                    pattern_id=pattern.id,
                    name=ch_def["name"],
                    waveform_type=ch_def["waveform"],
                    volume=ch_def["volume"],
                    pan=ch_def["pan"],
                    muted=False,
                    locked_ranges=[],
                    synth_params=ch_def["params"],
                )
                s.add(ch)
                s.flush()
                for i, (active, pitch, velocity) in enumerate(ch_def["steps"]):
                    s.add(Step(
                        channel_id=ch.id,
                        step_index=i,
                        active=active,
                        pitch=pitch,
                        velocity=velocity,
                    ))
            s.commit()

    # ── Load project ──────────────────────────────────────────────────────────

    def _load_project(self, project_id: int) -> None:
        with Session() as s:
            proj = s.query(Project).filter(Project.id == project_id).first()
            if proj is None:
                return

            self._current_project_id = proj.id

            # Use first pattern
            pattern = proj.patterns[0] if proj.patterns else None
            if pattern is None:
                return

            channel_states: list[ChannelState] = []
            for ch in pattern.channels:
                steps = [
                    StepState(active=st.active, pitch=st.pitch, velocity=st.velocity)
                    for st in sorted(ch.steps, key=lambda x: x.step_index)
                ]
                # Merge saved params with waveform-appropriate defaults
                default_params = WAVEFORM_DEFAULT_PARAMS.get(
                    ch.waveform_type, DEFAULT_SYNTH_PARAMS
                ).copy()
                params = {**default_params, **(ch.synth_params or {})}
                channel_states.append(ChannelState(
                    name=ch.name,
                    waveform_type=ch.waveform_type,
                    plugin_id=getattr(ch, "plugin_id", "chiptune"),
                    volume=ch.volume,
                    pan=ch.pan,
                    muted=ch.muted,
                    steps=steps,
                    locked_ranges=list(ch.locked_ranges or []),
                    synth_params=params,
                ))

            total_steps = proj.steps_per_pattern

        # Rebuild or update sequencer view
        if self._seq_view is not None:
            self._seq_view.setParent(None)
            self._seq_view.deleteLater()

        self._seq_view = SequencerView(channel_states)
        self._seq_container_lay.addWidget(self._seq_view)
        if self._panel_collapsed:
            self._seq_view.collapse_left_panel()

        # Wire loop ruler → scheduler
        self._seq_view._ruler.loop_changed.connect(self._on_loop_changed)

        # Give the scheduler the live _channel_states list so add/remove during
        # playback are visible immediately without stop/start.
        self._scheduler.channels = self._seq_view._channel_states
        self._scheduler.total_steps = total_steps
        self._scheduler.bpm = self._toolbar.current_bpm()
        loop_start, loop_end = self._seq_view.get_loop_region()
        self._scheduler.loop_start = loop_start
        self._scheduler.loop_end   = loop_end

        self._toolbar.set_current_project({
            "id": proj.id if hasattr(proj, "id") else self._current_project_id,
            "name": proj.name if hasattr(proj, "name") else "",
            "bpm": proj.bpm if hasattr(proj, "bpm") else 120,
        })

        self.statusBar().showMessage(f"Loaded project: {proj.name if hasattr(proj, 'name') else ''}")

    # ── Save project ──────────────────────────────────────────────────────────

    def _save_project(self, name: str) -> None:
        if self._current_project_id is None or self._seq_view is None:
            return

        channel_data = self._seq_view.serialize()
        loop_start, loop_end = self._seq_view.get_loop_region()
        total_steps = self._scheduler.total_steps

        with Session() as s:
            proj = s.query(Project).filter(Project.id == self._current_project_id).first()
            if proj is None:
                return
            proj.name = name
            proj.bpm = self._toolbar.current_bpm()
            proj.steps_per_pattern = total_steps
            proj.loop_start = loop_start
            proj.loop_end   = loop_end

            pattern = proj.patterns[0] if proj.patterns else None
            if pattern is None:
                return

            # Delete and re-create channels + steps
            for ch in list(pattern.channels):
                s.delete(ch)
            s.flush()

            for i, ch_data in enumerate(channel_data):
                ch = Channel(
                    pattern_id=pattern.id,
                    name=ch_data["name"],
                    waveform_type=ch_data["waveform_type"],
                    plugin_id=ch_data.get("plugin_id", "chiptune"),
                    volume=ch_data["volume"],
                    pan=ch_data["pan"],
                    muted=ch_data["muted"],
                    locked_ranges=ch_data["locked_ranges"],
                    synth_params=ch_data["synth_params"],
                )
                s.add(ch)
                s.flush()
                for j, st_data in enumerate(ch_data["steps"]):
                    s.add(Step(
                        channel_id=ch.id,
                        step_index=j,
                        active=st_data["active"],
                        pitch=st_data["pitch"],
                        velocity=st_data["velocity"],
                    ))
            s.commit()

        self.statusBar().showMessage(f"Saved: {name}")
        # Refresh project list
        projects = self._load_project_list()
        self._toolbar.set_project_list(projects)
        self._toolbar.set_current_project({"id": self._current_project_id, "name": name,
                                           "bpm": self._toolbar.current_bpm()})

    # ── Toolbar signal handlers ───────────────────────────────────────────────

    def _on_play(self) -> None:
        self._scheduler.bpm = self._toolbar.current_bpm()
        loop_start, loop_end = self._seq_view.get_loop_region() if self._seq_view else (0, 15)
        self._scheduler.loop_start = loop_start
        self._scheduler.loop_end   = loop_end
        if self._seq_view:
            self._scheduler.channels = self._seq_view._channel_states
        self._scheduler.play()
        self._toolbar.set_playing(True)

    def _on_stop(self) -> None:
        self._scheduler.stop()
        self._toolbar.set_playing(False)
        if self._seq_view:
            self._seq_view.set_playhead(-1)

    def _on_bpm_changed(self, bpm: int) -> None:
        self._scheduler.bpm = bpm

    def _on_loop_changed(self, start: int, end: int) -> None:
        self._scheduler.loop_start = start
        self._scheduler.loop_end   = end

    def _on_project_new(self) -> None:
        self._create_default_project()
        projects = self._load_project_list()
        self._toolbar.set_project_list(projects)
        if projects:
            self._load_project(projects[-1]["id"])

    def _on_project_save(self, name: str) -> None:
        self._save_project(name)

    def _on_project_load(self, project_id: int) -> None:
        if project_id != self._current_project_id:
            self._load_project(project_id)

    def _on_project_delete(self, project_id: int) -> None:
        reply = QMessageBox.question(
            self, "Delete Project",
            "Delete this project? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        with Session() as s:
            proj = s.query(Project).filter(Project.id == project_id).first()
            if proj:
                s.delete(proj)
                s.commit()
        projects = self._load_project_list()
        self._toolbar.set_project_list(projects)
        if projects:
            self._load_project(projects[0]["id"])
        else:
            self._create_default_project()
            projects = self._load_project_list()
            self._toolbar.set_project_list(projects)
            if projects:
                self._load_project(projects[0]["id"])

    def _on_left_panel_toggle(self) -> None:
        if self._seq_view:
            self._seq_view.toggle_left_panel()
            self._panel_collapsed = self._seq_view._panel_collapsed

    # ── Scheduler → UI ────────────────────────────────────────────────────────

    def _on_step_changed(self, step: int) -> None:
        if self._seq_view:
            self._seq_view.set_playhead(step)

    # ── Close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._scheduler.stop()
        self._engine.stop()
        super().closeEvent(event)
