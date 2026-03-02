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

    def serialize(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "waveform_type": self.waveform_type,
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
