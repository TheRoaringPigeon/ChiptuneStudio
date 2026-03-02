from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChannelDef:
    """Default channel configuration provided by a plugin."""
    name: str
    waveform_type: str       # "square", "triangle", "noise", "sawtooth"
    default_pitch: int = 60  # MIDI note number (60 = middle C)
    volume: float = 0.8
    pan: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "waveform_type": self.waveform_type,
            "default_pitch": self.default_pitch,
            "volume": self.volume,
            "pan": self.pan,
        }


@dataclass
class PluginBase:
    """Base class for all synthesizer plugins (desktop version)."""
    id: str
    name: str
    description: str
    version: str
    default_channels: list[ChannelDef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "default_channels": [ch.to_dict() for ch in self.default_channels],
        }
