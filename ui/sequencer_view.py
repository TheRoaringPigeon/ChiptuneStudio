"""
SequencerView — 3-column layout:
  Left (200px fixed)  : channel label widgets
  Center (scroll area): TimelineRuler + step grids
  Right (56px fixed)  : step count buttons (+16/+8/+4, -4/-1)

2D drag-select is handled here via event filters on all StepGrid widgets.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QObject, QEvent, QPoint, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QScrollArea,
    QPushButton, QLabel, QFrame, QMenu, QSplitter,
)

from models.schemas import ChannelState, StepState, DEFAULT_SYNTH_PARAMS, NOISE_SYNTH_PARAMS
from ui.channel_strip import ChannelStrip, LABEL_W
from ui.timeline_ruler import TimelineRuler
from ui.channel_settings import ChannelSettingsPanel
from ui.step_grid import StepGrid, _step_x, STEP_W
from ui import theme

RULER_SPACER_H = 36
RIGHT_W        = 56
COLLAPSED_W    = 28   # icon-only collapsed width of the left panel


class _SelectionFilter(QObject):
    """Event filter installed on all StepGrid widgets for 2D drag-select."""

    def __init__(self, view: "SequencerView"):
        super().__init__()
        self._view = view

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if isinstance(obj, StepGrid):
            if event.type() == QEvent.Type.MouseButtonPress:
                self._view._sel_start(obj, event)
                return True   # consume — StepGrid must not toggle until we know it's a click
            elif event.type() == QEvent.Type.MouseMove:
                self._view._sel_move(obj, event)
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._view._sel_end(obj, event)
        return False


class SequencerView(QWidget):
    def __init__(self, channel_states: list[ChannelState], parent=None):
        super().__init__(parent)
        self._channel_states = channel_states
        self._strips: list[ChannelStrip] = []
        self._total_steps: int = len(channel_states[0].steps) if channel_states else 16

        self._settings_panel = ChannelSettingsPanel()

        # Selection state
        self._sel_origin_step: int | None = None
        self._sel_origin_ch: int | None = None
        self._sel_origin_grid: "StepGrid | None" = None
        self._sel_current_step: int | None = None
        self._sel_current_ch: int | None = None
        self._sel_button_held: bool = False
        self._sel_dragged: bool = False   # True only after mouse moves away from origin
        self._sel_filter = _SelectionFilter(self)

        # Left-panel collapse state
        self._panel_collapsed: bool = False
        self._saved_panel_width: int = LABEL_W

        # Auto-scroll state
        self._scroll_dx: int = 0
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(16)   # ~60 fps
        self._auto_scroll_timer.timeout.connect(self._do_auto_scroll)

        # Context bar (floating)
        self._ctx_bar = self._build_context_bar()
        self._ctx_bar.hide()

        self._build_ui()
        self._build_strips()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left panel (width controlled by splitter, not fixed)
        self._left_panel = QWidget()
        self._left_panel.setMinimumWidth(COLLAPSED_W)
        self._left_panel.setStyleSheet(f"background: {theme.BG_PANEL};")
        self._left_lay = QVBoxLayout(self._left_panel)
        self._left_lay.setContentsMargins(0, 0, 0, 0)
        self._left_lay.setSpacing(0)

        # Ruler spacer on left
        ruler_spacer = QWidget()
        ruler_spacer.setFixedHeight(RULER_SPACER_H)
        ruler_spacer.setStyleSheet(f"background: {theme.BG_PANEL};")
        self._left_lay.addWidget(ruler_spacer)

        # Sub-container for channel label widgets (populated by _build_strips)
        self._channels_container = QWidget()
        self._left_channels_lay = QVBoxLayout(self._channels_container)
        self._left_channels_lay.setContentsMargins(0, 0, 0, 0)
        self._left_channels_lay.setSpacing(0)
        self._left_lay.addWidget(self._channels_container)

        # Add channel button
        self._add_channel_btn = QPushButton("+ ADD CHANNEL")
        self._add_channel_btn.setFixedHeight(28)
        self._add_channel_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {theme.GREEN};"
            f" border: 1px dashed {theme.GREEN}; font-size: 10px; margin: 4px; }}"
            f"QPushButton:hover {{ background: {theme.BG_STRIP}; }}"
        )
        self._add_channel_btn.clicked.connect(self._show_add_channel_menu)
        self._left_lay.addWidget(self._add_channel_btn)

        self._left_lay.addStretch(1)

        # Scroll area (center)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._scroll_content = QWidget()
        self._scroll_lay = QVBoxLayout(self._scroll_content)
        self._scroll_lay.setContentsMargins(4, 0, 4, 0)
        self._scroll_lay.setSpacing(0)

        # Timeline ruler
        self._ruler = TimelineRuler(self._total_steps)
        self._ruler.loop_changed.connect(self._on_loop_changed)
        self._ruler.installEventFilter(self)   # auto-scroll during loop-handle drag
        self._scroll_lay.addWidget(self._ruler)

        # Grid area placeholder — strips added in _build_strips
        self._grid_container = QWidget()
        self._grid_lay = QVBoxLayout(self._grid_container)
        self._grid_lay.setContentsMargins(0, 0, 0, 0)
        self._grid_lay.setSpacing(0)
        self._scroll_lay.addWidget(self._grid_container)
        self._scroll_lay.addStretch(1)

        self._scroll.setWidget(self._scroll_content)

        # Right panel — step count buttons
        right = QWidget()
        right.setFixedWidth(RIGHT_W)
        right.setStyleSheet(f"background: {theme.BG_PANEL};")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(4, 4, 4, 4)
        right_lay.setSpacing(4)
        for label, delta in [("+16", 16), ("+8", 8), ("+4", 4), ("-4", -4), ("-1", -1)]:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.clicked.connect(lambda _, d=delta: self._change_steps(d))
            right_lay.addWidget(btn)
        right_lay.addStretch(1)

        # Splitter — left panel is resizable, scroll area takes remaining space
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(3)
        self._splitter.setStyleSheet(
            f"QSplitter::handle:horizontal {{ background: {theme.BORDER}; }}"
            f"QSplitter::handle:horizontal:hover {{ background: {theme.GREEN}; }}"
        )
        self._splitter.addWidget(self._left_panel)
        self._splitter.addWidget(self._scroll)
        self._splitter.setSizes([LABEL_W, 800])
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)
        self._scroll.setMinimumWidth(150)

        root.addWidget(self._splitter, 1)
        root.addWidget(right)

    def _build_strips(self) -> None:
        # Detach and destroy existing strip widgets
        for strip in self._strips:
            strip.label_widget.setParent(None)
            strip.label_widget.deleteLater()
            if hasattr(strip, "_row_widget"):
                strip._row_widget.setParent(None)
                strip._row_widget.deleteLater()
        self._strips.clear()

        # Explicit grid layout clear (safety net)
        while self._grid_lay.count():
            item = self._grid_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, state in enumerate(self._channel_states):
            self._append_strip(state, i)

    def _append_strip(self, state: ChannelState, idx: int) -> None:
        """Create a ChannelStrip, wire it up, and insert it into both panels."""
        strip = ChannelStrip(state, self._settings_panel, idx)

        strip.grid_widget.installEventFilter(self._sel_filter)
        strip.grid_widget.setProperty("channel_index", idx)
        strip.remove_requested.connect(lambda s=strip: self._remove_channel(s))

        # Left panel: label widget into the channels sub-layout
        self._left_channels_lay.addWidget(strip.label_widget)
        if self._panel_collapsed:
            strip.collapse()

        # Center scroll: grid row
        row = self._grid_widget_row(strip, idx)
        strip._row_widget = row
        self._grid_lay.addWidget(row)

        self._strips.append(strip)

    def _grid_widget_row(self, strip: ChannelStrip, idx: int) -> QWidget:
        row = QWidget()
        row.setFixedHeight(46)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(0)
        lay.addWidget(strip.grid_widget)
        lay.addStretch(1)
        return row

    # ── Add / Remove channels ─────────────────────────────────────────────────

    def _show_add_channel_menu(self) -> None:
        menu = QMenu(self)
        options = [
            ("▬  Pulse (Square)",  "square"),
            ("▲  Triangle",        "triangle"),
            ("∿  Sawtooth",        "sawtooth"),
            ("⊞  Noise",           "noise"),
        ]
        for label, wtype in options:
            act = QAction(label, menu)
            act.triggered.connect(lambda _, w=wtype: self._add_channel(w))
            menu.addAction(act)
        btn = self._add_channel_btn
        menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))

    def _add_channel(self, waveform_type: str) -> None:
        is_noise = waveform_type == "noise"
        params = dict(NOISE_SYNTH_PARAMS if is_noise else DEFAULT_SYNTH_PARAMS)
        default_names = {
            "square":   "Pulse",
            "triangle": "Triangle",
            "sawtooth": "Sawtooth",
            "noise":    "Noise",
        }
        steps = [StepState() for _ in range(self._total_steps)]
        state = ChannelState(
            name=default_names.get(waveform_type, "Channel"),
            waveform_type=waveform_type,
            volume=0.8,
            pan=0.0,
            muted=False,
            steps=steps,
            locked_ranges=[],
            synth_params=params,
        )
        self._channel_states.append(state)
        self._append_strip(state, len(self._strips))

    def _remove_channel(self, strip: ChannelStrip) -> None:
        if len(self._strips) <= 1:
            return  # always keep at least one channel
        self._clear_sel_state()
        # Detach widgets
        strip.label_widget.setParent(None)
        strip.label_widget.deleteLater()
        strip._row_widget.setParent(None)
        strip._row_widget.deleteLater()
        # Update state lists
        self._channel_states.remove(strip.live_state)
        self._strips.remove(strip)
        # Re-index remaining strips
        for i, s in enumerate(self._strips):
            s._channel_index = i
            s.grid_widget.setProperty("channel_index", i)

    # ── Left panel collapse / expand ──────────────────────────────────────────

    def toggle_left_panel(self) -> None:
        if self._panel_collapsed:
            self.expand_left_panel()
        else:
            self.collapse_left_panel()

    def collapse_left_panel(self) -> None:
        self._panel_collapsed   = True
        self._saved_panel_width = max(self._splitter.sizes()[0], LABEL_W)
        for strip in self._strips:
            strip.collapse()
        self._add_channel_btn.hide()
        total = self._splitter.width()
        self._splitter.setSizes([COLLAPSED_W, total - COLLAPSED_W])

    def expand_left_panel(self) -> None:
        self._panel_collapsed = False
        for strip in self._strips:
            strip.expand()
        self._add_channel_btn.show()
        total  = self._splitter.width()
        restore = min(self._saved_panel_width, total - 150)
        self._splitter.setSizes([restore, total - restore])

    # ── Context bar ───────────────────────────────────────────────────────────

    def _build_context_bar(self) -> QWidget:
        bar = QWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        bar.setStyleSheet(
            f"background: {theme.BG_PANEL}; border: 1px solid {theme.BORDER}; border-radius: 4px;"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(6)

        lock_btn   = QPushButton("Lock")
        unlock_btn = QPushButton("Unlock")
        clear_btn  = QPushButton("Clear")

        lock_btn.clicked.connect(self._lock_selection)
        unlock_btn.clicked.connect(self._unlock_selection)
        clear_btn.clicked.connect(self._clear_selection)

        lay.addWidget(lock_btn)
        lay.addWidget(unlock_btn)
        lay.addWidget(clear_btn)
        return bar

    # ── Step count controls ───────────────────────────────────────────────────

    def _change_steps(self, delta: int) -> None:
        old_count = self._total_steps
        new_count = max(4, min(64, old_count + delta))
        if new_count == old_count:
            return

        # Pin state: was the loop end sitting on the very last step?
        loop_end_was_max = (self._ruler._loop_end == old_count - 1)

        self._total_steps = new_count
        for strip in self._strips:
            strip.resize_steps(new_count)
        # set_total_steps already clamps loop_end downward when removing steps
        self._ruler.set_total_steps(new_count)

        # If the loop end was pinned to the far right, keep it pinned
        if loop_end_was_max:
            self._ruler._loop_end = new_count - 1
            self._ruler.update()

        # Notify scheduler (and anything else wired to loop_changed)
        self._ruler.loop_changed.emit(self._ruler._loop_start, self._ruler._loop_end)

    # ── Loop region ───────────────────────────────────────────────────────────

    def _on_loop_changed(self, start: int, end: int) -> None:
        # Propagated to MainWindow via parent access
        pass

    def get_loop_region(self) -> tuple[int, int]:
        return self._ruler._loop_start, self._ruler._loop_end

    def set_loop_region(self, start: int, end: int) -> None:
        self._ruler.set_loop_region(start, end)

    # ── Playhead ──────────────────────────────────────────────────────────────

    def set_playhead(self, idx: int) -> None:
        self._ruler.set_playhead(idx)
        for strip in self._strips:
            strip.set_playhead(idx)
        # Auto-scroll to keep playhead visible
        x = _step_x(idx)
        self._scroll.ensureVisible(x + STEP_W // 2, 0, STEP_W, 0)

    # ── Auto-scroll ───────────────────────────────────────────────────────────

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Watch ruler mouse events so loop-handle drags also trigger auto-scroll."""
        if obj is self._ruler:
            if event.type() == QEvent.Type.MouseMove:
                if self._ruler._drag_handle is not None:
                    self._update_auto_scroll(event.globalPosition().toPoint())
                else:
                    self._stop_auto_scroll()
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._stop_auto_scroll()
        return False   # never consume ruler events

    def _update_auto_scroll(self, gpos: QPoint) -> None:
        """Start/update or stop the auto-scroll timer based on cursor proximity to viewport edges."""
        vp     = self._scroll.viewport()
        vp_tl  = vp.mapToGlobal(QPoint(0, 0))
        vp_left  = vp_tl.x()
        vp_right = vp_left + vp.width()

        ZONE      = 60    # px from edge that triggers scrolling
        MAX_SPEED = 18    # px per timer tick at full speed

        x = gpos.x()
        if x < vp_left + ZONE:
            dist = (vp_left + ZONE) - x
            self._scroll_dx = -max(2, int(dist / ZONE * MAX_SPEED))
            if not self._auto_scroll_timer.isActive():
                self._auto_scroll_timer.start()
        elif x > vp_right - ZONE:
            dist = x - (vp_right - ZONE)
            self._scroll_dx = max(2, int(dist / ZONE * MAX_SPEED))
            if not self._auto_scroll_timer.isActive():
                self._auto_scroll_timer.start()
        else:
            self._stop_auto_scroll()

    def _stop_auto_scroll(self) -> None:
        self._auto_scroll_timer.stop()
        self._scroll_dx = 0

    def _do_auto_scroll(self) -> None:
        """Timer callback: advance the scrollbar, then refresh selection / ruler."""
        from PyQt6.QtGui import QCursor
        hsb = self._scroll.horizontalScrollBar()
        hsb.setValue(hsb.value() + self._scroll_dx)

        gpos = QCursor.pos()

        # Update step-grid drag selection
        if self._sel_button_held and self._sel_origin_step is not None:
            ch  = self._channel_at_global(gpos)
            idx = self._step_at_global_clamped(gpos)
            if ch is not None:
                self._sel_current_ch = ch
            self._sel_current_step = idx
            if (self._sel_current_step != self._sel_origin_step
                    or self._sel_current_ch != self._sel_origin_ch):
                self._sel_dragged = True
            if self._sel_dragged:
                self._update_selection()

        # Update ruler loop-handle drag
        if self._ruler._drag_handle is not None:
            local_x = self._ruler.mapFromGlobal(gpos).x()
            step = self._ruler._nearest_step(local_x)
            if self._ruler._drag_handle == "start":
                self._ruler._loop_start = min(step, self._ruler._loop_end)
            else:
                self._ruler._loop_end = max(step, self._ruler._loop_start)
            self._ruler.loop_changed.emit(self._ruler._loop_start, self._ruler._loop_end)
            self._ruler.update()

    # ── 2D Drag Selection ─────────────────────────────────────────────────────

    def _grid_index(self, grid: StepGrid) -> int:
        return grid.property("channel_index") or 0

    def _step_at_x(self, x: int) -> int | None:
        for i in range(self._total_steps):
            sx = _step_x(i)
            if sx <= x < sx + STEP_W:
                return i
        return None

    def _channel_at_global(self, gpos: QPoint) -> int | None:
        """Return channel index whose grid widget contains global point gpos."""
        for i, strip in enumerate(self._strips):
            g = strip.grid_widget
            tl = g.mapToGlobal(QPoint(0, 0))
            if tl.y() <= gpos.y() <= tl.y() + g.height():
                return i
        return None

    def _step_at_global(self, gpos: QPoint) -> int | None:
        """Return step index under gpos by converting to first grid's local x."""
        if not self._strips:
            return None
        g = self._strips[0].grid_widget
        local_x = g.mapFromGlobal(gpos).x()
        return self._step_at_x(local_x)

    def _step_at_global_clamped(self, gpos: QPoint) -> int:
        """Like _step_at_global but clamps to [0, total_steps-1] for auto-scroll."""
        if not self._strips:
            return 0
        g = self._strips[0].grid_widget
        local_x = g.mapFromGlobal(gpos).x()
        idx = self._step_at_x(local_x)
        if idx is not None:
            return idx
        return 0 if local_x < _step_x(0) else self._total_steps - 1

    def _sel_start(self, grid: StepGrid, ev) -> None:
        idx = self._step_at_x(int(ev.position().x()))
        if idx is None:
            return
        self._sel_button_held  = True
        self._sel_dragged      = False
        self._sel_origin_step  = idx
        self._sel_origin_ch    = self._grid_index(grid)
        self._sel_origin_grid  = grid
        self._sel_current_step = idx
        self._sel_current_ch   = self._grid_index(grid)
        # No visual selection yet — wait until the mouse actually moves

    def _sel_move(self, grid: StepGrid, ev) -> None:
        if not self._sel_button_held or self._sel_origin_step is None:
            return
        gpos = ev.globalPosition().toPoint()
        ch  = self._channel_at_global(gpos)
        idx = self._step_at_global(gpos)
        if idx is None:
            return
        if ch is not None:
            self._sel_current_ch = ch
        self._sel_current_step = idx
        # Only mark as a real drag once the cursor leaves the origin cell
        if self._sel_current_step != self._sel_origin_step or self._sel_current_ch != self._sel_origin_ch:
            self._sel_dragged = True
        if self._sel_dragged:
            self._update_selection()
        self._update_auto_scroll(gpos)

    def _sel_end(self, grid: StepGrid, ev) -> None:
        self._sel_button_held = False
        self._stop_auto_scroll()
        if not self._sel_dragged:
            # Plain click — manually perform the toggle we blocked in the press event
            g   = self._sel_origin_grid
            idx = self._sel_origin_step
            if g is not None and idx is not None and not g._is_locked(idx):
                g._steps[idx].active = not g._steps[idx].active
                g.step_toggled.emit(idx, g._steps[idx].active)
                g.update()
            self._clear_sel_state()
            return
        # Show context bar if more than one cell selected
        sel = self._compute_selection()
        total = sum(len(s) for s in sel.values())
        if total > 1:
            gpos = ev.globalPosition().toPoint()
            self._ctx_bar.move(gpos.x() + 10, gpos.y() + 10)
            self._ctx_bar.show()
        else:
            self._clear_sel_state()

    def _compute_selection(self) -> dict[int, set[int]]:
        if self._sel_origin_step is None:
            return {}
        step_min = min(self._sel_origin_step, self._sel_current_step)
        step_max = max(self._sel_origin_step, self._sel_current_step)
        ch_min   = min(self._sel_origin_ch,   self._sel_current_ch)
        ch_max   = max(self._sel_origin_ch,   self._sel_current_ch)
        result: dict[int, set[int]] = {}
        for ch in range(ch_min, ch_max + 1):
            result[ch] = set(range(step_min, step_max + 1))
        return result

    def _update_selection(self) -> None:
        sel = self._compute_selection()
        for i, strip in enumerate(self._strips):
            strip.grid_widget.set_selected(sel.get(i, set()))

    def _lock_selection(self) -> None:
        sel = self._compute_selection()
        for ch_idx, steps in sel.items():
            if steps:
                self._strips[ch_idx].add_locked_range(min(steps), max(steps))
        self._clear_sel_state()

    def _unlock_selection(self) -> None:
        sel = self._compute_selection()
        for ch_idx, steps in sel.items():
            if steps:
                self._strips[ch_idx].remove_locked_range(min(steps), max(steps))
        self._clear_sel_state()

    def _clear_selection(self) -> None:
        sel = self._compute_selection()
        for ch_idx, steps in sel.items():
            for s in steps:
                if s < len(self._strips[ch_idx].live_state.steps):
                    self._strips[ch_idx].live_state.steps[s].active = False
        self._clear_sel_state()
        for strip in self._strips:
            strip.grid_widget.update()

    def _clear_sel_state(self) -> None:
        self._stop_auto_scroll()
        self._sel_origin_step = None
        self._sel_origin_ch   = None
        self._sel_origin_grid = None
        self._sel_current_step = None
        self._sel_current_ch   = None
        self._sel_dragged = False
        for strip in self._strips:
            strip.grid_widget.set_selected(set())
        self._ctx_bar.hide()

    # ── Data access ───────────────────────────────────────────────────────────

    def get_channel_states(self) -> list[ChannelState]:
        return [s.live_state for s in self._strips]

    def serialize(self) -> list[dict]:
        return [s.serialize() for s in self._strips]

    def load_project(self, channel_states: list[ChannelState], total_steps: int,
                     loop_start: int, loop_end: int) -> None:
        self._channel_states = channel_states
        self._total_steps = total_steps
        self._build_strips()
        self._ruler.set_total_steps(total_steps)
        self._ruler.set_loop_region(loop_start, loop_end)
