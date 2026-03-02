from app.core.plugin_base import ChannelDef, PluginBase


class ChiptunePlugin(PluginBase):
    """
    Chiptune / keygen-style synthesizer plugin.

    Emulates classic 4-channel architecture:
      - 2 pulse/square wave channels (melody, harmony)
      - 1 triangle wave channel (bass)
      - 1 noise channel (percussion)

    Audio synthesis is handled entirely in the browser via
    /static/js/synth/ChiptuneSynth.js using the Web Audio API.
    """

    def __init__(self) -> None:
        super().__init__(
            id="chiptune",
            name="Chiptune",
            description="Classic 4-channel chiptune synthesizer (NES/Game Boy style). "
                        "Pulse waves, triangle bass, and noise percussion.",
            version="1.0.0",
            frontend_module="/static/js/synth/ChiptuneSynth.js",
            default_channels=[
                ChannelDef(
                    name="Pulse 1",
                    waveform_type="square",
                    default_pitch=72,   # C5
                    volume=0.7,
                    pan=0.0,
                ),
                ChannelDef(
                    name="Pulse 2",
                    waveform_type="square",
                    default_pitch=67,   # G4
                    volume=0.6,
                    pan=0.0,
                ),
                ChannelDef(
                    name="Triangle",
                    waveform_type="triangle",
                    default_pitch=48,   # C3
                    volume=0.75,
                    pan=0.0,
                ),
                ChannelDef(
                    name="Noise",
                    waveform_type="noise",
                    default_pitch=0,
                    volume=0.5,
                    pan=0.0,
                ),
            ],
        )
