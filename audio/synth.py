"""
ChiptuneSynth — numpy-based waveform generation.

All audio synthesis runs on CPU (no Web Audio API).
render_note() returns a (N, 2) float32 stereo array ready for the audio engine.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt

SAMPLE_RATE = 44100


def _midi_to_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def _resolve_params(waveform_type: str, raw: dict) -> dict:
    defaults = {
        "attack":       0.002,
        "decay":        0.08,
        "sustain":      0.8,
        "release":      0.05,
        "dutyCycle":    0.5,
        "detune":       0.0,
        "transpose":    0,
        "vibratoRate":  0.0,
        "vibratoDepth": 0.0,
        "sweepAmount":  0,
        "sweepTime":    0.1,
        "filterType":   "highpass" if waveform_type == "noise" else "none",
        "filterFreq":   2000.0,
        "filterQ":      1.0,
    }
    return {**defaults, **raw}


def _adsr(n: int, sr: int, attack: float, decay: float, sustain: float, release: float) -> np.ndarray:
    """Build an ADSR envelope of length n samples."""
    env = np.zeros(n, dtype=np.float32)
    a = min(int(attack * sr), n)
    d = min(int(decay * sr), n - a)
    r = min(int(release * sr), n)
    s_start = a + d
    s_end = max(s_start, n - r)

    if a > 0:
        env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    if d > 0:
        env[a:a + d] = np.linspace(1.0, sustain, d, dtype=np.float32)
    if s_end > s_start:
        env[s_start:s_end] = sustain
    if r > 0 and s_end < n:
        env[s_end:s_end + r] = np.linspace(sustain, 0.0, min(r, n - s_end), dtype=np.float32)
    return env


def _accumulate_phase(n: int, sr: int, base_freq: float, p: dict) -> np.ndarray:
    """
    Build per-sample frequency array with vibrato + sweep, then cumsum for phase.
    Returns phase array (n,) in cycles (not radians).
    """
    dt = 1.0 / sr
    freq_arr = np.full(n, base_freq, dtype=np.float64)

    # Sweep: linear ramp from sweep_freq → base_freq over sweep_time
    sweep_amount = int(p["sweepAmount"])
    if sweep_amount != 0:
        sweep_samples = min(int(p["sweepTime"] * sr), n)
        sweep_freq = _midi_to_freq(0)  # fallback
        # recompute based on pitch shift
        sweep_freq = base_freq * (2.0 ** (sweep_amount / 12.0))
        ramp = np.linspace(sweep_freq, base_freq, sweep_samples, dtype=np.float64)
        freq_arr[:sweep_samples] = ramp

    # Vibrato LFO
    vib_rate = float(p["vibratoRate"])
    vib_depth = float(p["vibratoDepth"])  # cents
    if vib_rate > 0 and vib_depth > 0:
        t = np.arange(n, dtype=np.float64) * dt
        # depth_hz = base_freq * (2^(depth/1200) - 1)
        depth_hz = base_freq * (2.0 ** (vib_depth / 1200.0) - 1.0)
        freq_arr += depth_hz * np.sin(2.0 * np.pi * vib_rate * t)

    # phase in cycles; wrap to [0,1) per sample via cumsum * dt
    phase = np.cumsum(freq_arr * dt)
    return phase.astype(np.float32)


def _square(n: int, sr: int, base_freq: float, p: dict) -> np.ndarray:
    phase = _accumulate_phase(n, sr, base_freq, p)
    duty = float(p["dutyCycle"])
    wave = np.where((phase % 1.0) < duty, 1.0, -1.0).astype(np.float32)
    return wave


def _triangle(n: int, sr: int, base_freq: float, p: dict) -> np.ndarray:
    phase = _accumulate_phase(n, sr, base_freq, p)
    t = phase % 1.0
    wave = (2.0 * np.abs(2.0 * t - 1.0) - 1.0).astype(np.float32)
    return wave


def _sawtooth(n: int, sr: int, base_freq: float, p: dict) -> np.ndarray:
    phase = _accumulate_phase(n, sr, base_freq, p)
    wave = (2.0 * (phase % 1.0) - 1.0).astype(np.float32)
    return wave


def _noise(n: int) -> np.ndarray:
    return np.random.uniform(-1.0, 1.0, n).astype(np.float32)


def _apply_filter(wave: np.ndarray, p: dict) -> np.ndarray:
    ftype = str(p["filterType"])
    if ftype == "none":
        return wave
    freq = float(p["filterFreq"])
    q = float(p["filterQ"])
    nyq = SAMPLE_RATE / 2.0
    freq = np.clip(freq, 20.0, nyq - 1.0)

    btype_map = {"lowpass": "low", "highpass": "high", "bandpass": "band"}
    btype = btype_map.get(ftype, "low")

    sos = butter(2, freq / nyq, btype=btype, output="sos")
    return sosfilt(sos, wave).astype(np.float32)


def render_note(
    waveform_type: str,
    midi_pitch: int,
    duration_s: float,
    volume: float,
    pan: float,
    velocity: int,
    params: dict,
) -> np.ndarray:
    """
    Render a single note and return a (N, 2) float32 stereo array.

    midi_pitch: MIDI note number (0-127); ignored for noise.
    velocity: 0-127
    volume: 0.0-1.0
    pan: -1.0 (L) to +1.0 (R)
    """
    p = _resolve_params(waveform_type, params)

    # Apply transpose (semitones) to pitch
    effective_pitch = midi_pitch + int(p.get("transpose", 0))
    effective_pitch = int(np.clip(effective_pitch, 0, 127))

    # Apply detune (cents): freq * 2^(cents/1200)
    base_freq = _midi_to_freq(effective_pitch) * (2.0 ** (float(p["detune"]) / 1200.0))

    n = max(1, int(duration_s * SAMPLE_RATE))

    # Generate waveform
    if waveform_type == "noise":
        wave = _noise(n)
    elif waveform_type == "triangle":
        wave = _triangle(n, SAMPLE_RATE, base_freq, p)
    elif waveform_type == "sawtooth":
        wave = _sawtooth(n, SAMPLE_RATE, base_freq, p)
    else:
        wave = _square(n, SAMPLE_RATE, base_freq, p)

    # Filter
    wave = _apply_filter(wave, p)

    # ADSR envelope
    gain_value = (velocity / 127.0) * volume
    env = _adsr(n, SAMPLE_RATE, p["attack"], p["decay"], p["sustain"], p["release"])
    wave = (wave * env * gain_value).astype(np.float32)

    # Pan to stereo
    pan = float(np.clip(pan, -1.0, 1.0))
    left_gain  = np.sqrt(0.5 * (1.0 - pan))
    right_gain = np.sqrt(0.5 * (1.0 + pan))

    stereo = np.empty((n, 2), dtype=np.float32)
    stereo[:, 0] = wave * left_gain
    stereo[:, 1] = wave * right_gain

    return stereo
