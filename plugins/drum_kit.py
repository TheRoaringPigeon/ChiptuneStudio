from models.schemas import (
    KICK_SYNTH_PARAMS,
    SNARE_SYNTH_PARAMS,
    HIHAT_CLOSED_SYNTH_PARAMS,
    HIHAT_OPEN_SYNTH_PARAMS,
    CLAP_SYNTH_PARAMS,
)
from plugins.base import ChannelDef, PluginBase, register


class DrumKitPlugin(PluginBase):
    """
    Drum kit plugin with synthesized kick, snare, hi-hat, and clap.
    All channels are unpitched — no pitch editing in step cells.
    """

    def __init__(self) -> None:
        super().__init__(
            id="drum_kit",
            name="Drum Kit",
            description="Synthesized drum kit. Kick uses sine sweep + noise click; "
                        "snare uses bandpass noise + sine body.",
            version="1.0.0",
            color="#ffee00",
            channels=[
                ChannelDef(
                    name="Kick",        waveform_type="kick",
                    icon="●", default_pitch=36, volume=0.9, pan=0.0,
                    pitched=False, synth_params=KICK_SYNTH_PARAMS,
                ),
                ChannelDef(
                    name="Snare",       waveform_type="snare",
                    icon="▪", default_pitch=38, volume=0.8, pan=0.0,
                    pitched=False, synth_params=SNARE_SYNTH_PARAMS,
                ),
                ChannelDef(
                    name="Hi-Hat (Cl)", waveform_type="hihat_closed",
                    icon="─", default_pitch=42, volume=0.6, pan=0.0,
                    pitched=False, synth_params=HIHAT_CLOSED_SYNTH_PARAMS,
                ),
                ChannelDef(
                    name="Hi-Hat (Op)", waveform_type="hihat_open",
                    icon="╌", default_pitch=46, volume=0.6, pan=0.0,
                    pitched=False, synth_params=HIHAT_OPEN_SYNTH_PARAMS,
                ),
                ChannelDef(
                    name="Clap",        waveform_type="clap",
                    icon="◈", default_pitch=39, volume=0.7, pan=0.0,
                    pitched=False, synth_params=CLAP_SYNTH_PARAMS,
                ),
            ],
        )


register(DrumKitPlugin())
