from plugins.base import ChannelDef, PluginBase, register


class ChiptunePlugin(PluginBase):
    """
    Classic chiptune synthesizer (NES/Game Boy style).
    All 7 standard waveform types. Audio synthesis runs on-CPU via numpy.
    """

    def __init__(self) -> None:
        super().__init__(
            id="chiptune",
            name="Chiptune",
            description="Classic chiptune synthesizer (NES/Game Boy style). "
                        "Pulse waves, triangle, sawtooth, sine, FM, wavetable, and noise.",
            version="1.0.0",
            color="#00ccff",
            channels=[
                ChannelDef(name="Pulse 1",   waveform_type="square",    icon="▬", default_pitch=72, volume=0.7,  pan=0.0, pitched=True),
                ChannelDef(name="Pulse 2",   waveform_type="square",    icon="▬", default_pitch=67, volume=0.6,  pan=0.0, pitched=True),
                ChannelDef(name="Triangle",  waveform_type="triangle",  icon="▲", default_pitch=48, volume=0.75, pan=0.0, pitched=True),
                ChannelDef(name="Sawtooth",  waveform_type="sawtooth",  icon="∿", default_pitch=60, volume=0.7,  pan=0.0, pitched=True),
                ChannelDef(name="Sine",      waveform_type="sine",      icon="⌒", default_pitch=60, volume=0.7,  pan=0.0, pitched=True),
                ChannelDef(name="FM",        waveform_type="fm",        icon="≋", default_pitch=60, volume=0.7,  pan=0.0, pitched=True,
                           synth_params={"fmRatio": 2.0, "fmIndex": 2.0}),
                ChannelDef(name="Wavetable", waveform_type="wavetable", icon="⊡", default_pitch=60, volume=0.7,  pan=0.0, pitched=True,
                           synth_params={"wavetablePreset": 0}),
                ChannelDef(name="Noise",     waveform_type="noise",     icon="⊞", default_pitch=0,  volume=0.5,  pan=0.0, pitched=False,
                           synth_params={"filterType": "highpass"}),
            ],
        )


register(ChiptunePlugin())
