from models.schemas import DEFAULT_SYNTH_PARAMS
from plugins.base import ChannelDef, PluginBase, register

_BASS_PARAMS = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.01, "decay": 0.12, "sustain": 0.7, "release": 0.08,
    "filterType": "lowpass", "filterFreq": 500,
    "detune": 3.0,
}

_LEAD_PARAMS = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.002, "decay": 0.06, "sustain": 0.8, "release": 0.04,
    "dutyCycle": 0.25,
    "filterType": "lowpass", "filterFreq": 2500,
}

_PAD_PARAMS = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.4, "decay": 0.1, "sustain": 0.95, "release": 0.3,
    "vibratoRate": 0.5, "vibratoDepth": 8,
    "filterType": "none",
}

_PLUCK_PARAMS = {
    **DEFAULT_SYNTH_PARAMS,
    "attack": 0.001, "decay": 0.15, "sustain": 0.0, "release": 0.05,
    "filterType": "highpass", "filterFreq": 1800,
}


class SynthLeadPlugin(PluginBase):
    """
    Melodic synth plugin with bass, lead, pad, and pluck presets.
    All channels are pitched.
    """

    def __init__(self) -> None:
        super().__init__(
            id="synth_lead",
            name="Synth Lead",
            description="Melodic synth presets: bass (sawtooth), lead (square), "
                        "pad (sine), and pluck (triangle).",
            version="1.0.0",
            color="#00ff88",
            channels=[
                ChannelDef(
                    name="Bass",  waveform_type="sawtooth",
                    icon="♭", default_pitch=36, volume=0.8, pan=0.0,
                    pitched=True, synth_params=_BASS_PARAMS,
                ),
                ChannelDef(
                    name="Lead",  waveform_type="square",
                    icon="♪", default_pitch=60, volume=0.7, pan=0.0,
                    pitched=True, synth_params=_LEAD_PARAMS,
                ),
                ChannelDef(
                    name="Pad",   waveform_type="sine",
                    icon="◎", default_pitch=60, volume=0.6, pan=0.0,
                    pitched=True, synth_params=_PAD_PARAMS,
                ),
                ChannelDef(
                    name="Pluck", waveform_type="triangle",
                    icon="♦", default_pitch=60, volume=0.7, pan=0.0,
                    pitched=True, synth_params=_PLUCK_PARAMS,
                ),
            ],
        )


register(SynthLeadPlugin())
