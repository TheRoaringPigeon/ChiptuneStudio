from dataclasses import dataclass, field
from typing import Any


# Default synth params — same 14 as the web app.
DEFAULT_SYNTH_PARAMS: dict[str, Any] = {
    "attack":       0.002,
    "decay":        0.08,
    "sustain":      0.8,
    "release":      0.05,
    "dutyCycle":    0.5,
    "detune":       0,
    "transpose":    0,
    "vibratoRate":  0,
    "vibratoDepth": 0,
    "sweepAmount":  0,
    "sweepTime":    0.1,
    "filterType":   "none",
    "filterFreq":   2000,
    "filterQ":      1,
}

NOISE_SYNTH_PARAMS: dict[str, Any] = {
    **DEFAULT_SYNTH_PARAMS,
    "filterType": "highpass",
}

FM_SYNTH_PARAMS: dict[str, Any] = {
    **DEFAULT_SYNTH_PARAMS,
    "fmRatio": 2.0,
    "fmIndex": 2.0,
}

WAVETABLE_SYNTH_PARAMS: dict[str, Any] = {
    **DEFAULT_SYNTH_PARAMS,
    "wavetablePreset": 0,
}

# ── Drum Kit default params ───────────────────────────────────────────────────

KICK_SYNTH_PARAMS: dict[str, Any] = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.001, "decay": 0.18, "sustain": 0.0, "release": 0.05,
    "filterType": "none",
}

SNARE_SYNTH_PARAMS: dict[str, Any] = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.001, "decay": 0.12, "sustain": 0.0, "release": 0.04,
    "filterType": "bandpass", "filterFreq": 1200, "filterQ": 1.5,
}

HIHAT_CLOSED_SYNTH_PARAMS: dict[str, Any] = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.001, "decay": 0.04, "sustain": 0.0, "release": 0.02,
    "filterType": "highpass", "filterFreq": 7000,
}

HIHAT_OPEN_SYNTH_PARAMS: dict[str, Any] = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.001, "decay": 0.20, "sustain": 0.05, "release": 0.15,
    "filterType": "highpass", "filterFreq": 6000,
}

CLAP_SYNTH_PARAMS: dict[str, Any] = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.001, "decay": 0.08, "sustain": 0.0, "release": 0.06,
    "filterType": "highpass", "filterFreq": 800,
}

# ── Per-waveform defaults lookup ─────────────────────────────────────────────

WAVEFORM_DEFAULT_PARAMS: dict[str, dict] = {
    "noise":        NOISE_SYNTH_PARAMS,
    "fm":           FM_SYNTH_PARAMS,
    "wavetable":    WAVETABLE_SYNTH_PARAMS,
    "kick":         KICK_SYNTH_PARAMS,
    "snare":        SNARE_SYNTH_PARAMS,
    "hihat_closed": HIHAT_CLOSED_SYNTH_PARAMS,
    "hihat_open":   HIHAT_OPEN_SYNTH_PARAMS,
    "clap":         CLAP_SYNTH_PARAMS,
}


@dataclass
class StepState:
    active: bool = False
    pitch: int = 60
    velocity: int = 100


@dataclass
class ChannelState:
    name: str
    waveform_type: str
    volume: float
    pan: float
    muted: bool
    steps: list[StepState]
    locked_ranges: list  # list of [start, end] pairs
    synth_params: dict   # 14 live-mutated params
    plugin_id: str = "chiptune"

    def serialize(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "waveform_type": self.waveform_type,
            "plugin_id": self.plugin_id,
            "volume": self.volume,
            "pan": self.pan,
            "muted": self.muted,
            "locked_ranges": self.locked_ranges,
            "synth_params": dict(self.synth_params),
            "steps": [
                {"active": s.active, "pitch": s.pitch, "velocity": s.velocity}
                for s in self.steps
            ],
        }


@dataclass
class ProjectState:
    id: int
    name: str
    plugin_id: str
    bpm: int
    steps_per_pattern: int
    loop_start: int
    loop_end: int
    channels: list[ChannelState] = field(default_factory=list)
