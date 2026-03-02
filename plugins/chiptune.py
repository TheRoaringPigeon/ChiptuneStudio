from plugins.base import ChannelDef, PluginBase


class ChiptunePlugin(PluginBase):
    """
    Classic 4-channel chiptune synthesizer (NES/Game Boy style).
    Audio synthesis runs on-CPU via numpy (audio/synth.py).
    """

    def __init__(self) -> None:
        super().__init__(
            id="chiptune",
            name="Chiptune",
            description="Classic 4-channel chiptune synthesizer (NES/Game Boy style). "
                        "Pulse waves, triangle bass, and noise percussion.",
            version="1.0.0",
            default_channels=[
                ChannelDef(name="Pulse 1",  waveform_type="square",   default_pitch=72, volume=0.7,  pan=0.0),
                ChannelDef(name="Pulse 2",  waveform_type="square",   default_pitch=67, volume=0.6,  pan=0.0),
                ChannelDef(name="Triangle", waveform_type="triangle", default_pitch=48, volume=0.75, pan=0.0),
                ChannelDef(name="Noise",    waveform_type="noise",    default_pitch=0,  volume=0.5,  pan=0.0),
            ],
        )
