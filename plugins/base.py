from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChannelDef:
    """Default channel configuration provided by a plugin."""
    name: str
    waveform_type: str       # key for render_note()
    icon: str = "?"
    default_pitch: int = 60  # MIDI note number (60 = middle C)
    volume: float = 0.8
    pan: float = 0.0
    pitched: bool = True     # False for drums — disables pitch editing in step cells
    synth_params: dict = field(default_factory=dict)  # overrides for this channel type

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "waveform_type": self.waveform_type,
            "icon": self.icon,
            "default_pitch": self.default_pitch,
            "volume": self.volume,
            "pan": self.pan,
            "pitched": self.pitched,
            "synth_params": dict(self.synth_params),
        }


@dataclass
class PluginBase:
    """Base class for all synthesizer plugins (desktop version)."""
    id: str
    name: str
    description: str
    version: str
    color: str = "#00ccff"
    channels: list[ChannelDef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "color": self.color,
            "channels": [ch.to_dict() for ch in self.channels],
        }


# ── Plugin registry ───────────────────────────────────────────────────────────

PLUGIN_REGISTRY: dict[str, "PluginBase"] = {}


def register(plugin: "PluginBase") -> None:
    PLUGIN_REGISTRY[plugin.id] = plugin


def get_all_plugins() -> list["PluginBase"]:
    return list(PLUGIN_REGISTRY.values())
