import { SynthBase } from './SynthBase.js';

/** Convert a MIDI note number to frequency in Hz. */
function midiToFreq(note) {
  return 440 * Math.pow(2, (note - 69) / 12);
}

/**
 * ChiptuneSynth — NES/Game Boy style synthesizer using the Web Audio API.
 *
 * Waveform types:
 *   "square"   — OscillatorNode with custom PeriodicWave for duty cycle control
 *   "triangle" — OscillatorNode type="triangle"
 *   "noise"    — White noise via AudioBufferSourceNode
 *   "sawtooth" — OscillatorNode type="sawtooth"
 *
 * Signal chain: source → envGain → [filter →] panner → masterGain
 *
 * Supports 14 per-channel parameters: attack, decay, sustain, release,
 * dutyCycle, detune, transpose (applied by sequencer), vibratoRate,
 * vibratoDepth, sweepAmount, sweepTime, filterType, filterFreq, filterQ.
 */
export class ChiptuneSynth extends SynthBase {
  /** @type {AudioContext} */
  #ctx = null;

  /** Shared gain (master volume for this synth) */
  #masterGain = null;

  /** Pre-built noise buffer (reused for every noise note) */
  #noiseBuffer = null;

  /**
   * Cache of PeriodicWave objects keyed by duty cycle (0–100 integer %).
   * Cleared on dispose/reinit to avoid cross-context references.
   */
  #pulseWaveCache = new Map();

  init(ctx) {
    this.#ctx = ctx;
    this.#masterGain = ctx.createGain();
    this.#masterGain.gain.value = 1.0;
    this.#masterGain.connect(ctx.destination);
    this.#noiseBuffer = this.#buildNoiseBuffer();
    this.#pulseWaveCache.clear();
  }

  /** Create a mono white-noise AudioBuffer (2 seconds, looped). */
  #buildNoiseBuffer() {
    const sampleRate = this.#ctx.sampleRate;
    const bufferSize = sampleRate * 2;
    const buffer = this.#ctx.createBuffer(1, bufferSize, sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return buffer;
  }

  /**
   * Build a PeriodicWave for a pulse/square wave with the given duty cycle.
   * Uses Fourier series: imag[k] = (2 / (k·π)) · sin(k·π·D)
   * @param {number} dutyCycle 0.1–0.9
   */
  #buildPulseWave(dutyCycle) {
    const harmonics = 256;
    const real = new Float32Array(harmonics + 1);
    const imag = new Float32Array(harmonics + 1);
    for (let k = 1; k <= harmonics; k++) {
      imag[k] = (2 / (k * Math.PI)) * Math.sin(k * Math.PI * dutyCycle);
    }
    return this.#ctx.createPeriodicWave(real, imag, { disableNormalization: false });
  }

  /**
   * Merge raw synth params with waveform-appropriate defaults.
   * Note: transpose is applied to pitch by the sequencer, not here.
   */
  #resolveParams(waveformType, raw) {
    return {
      attack:       0.002,
      decay:        0.08,
      sustain:      0.8,
      release:      0.05,
      dutyCycle:    0.5,
      detune:       0,
      transpose:    0,
      vibratoRate:  0,
      vibratoDepth: 0,
      sweepAmount:  0,
      sweepTime:    0.1,
      filterType:   waveformType === 'noise' ? 'highpass' : 'none',
      filterFreq:   2000,
      filterQ:      1,
      ...raw,
    };
  }

  playNote(waveformType, midiPitch, startTime, duration, velocity, volume, pan, synthParams = {}) {
    if (!this.#ctx) return;

    const ctx = this.#ctx;
    const p = this.#resolveParams(waveformType, synthParams);

    const gainValue    = (velocity / 127) * volume;
    const endTime      = startTime + duration;
    const sustainLevel = gainValue * p.sustain;
    const attackEnd    = startTime + p.attack;
    const decayEnd     = attackEnd + p.decay;
    const releaseStart = Math.max(startTime, endTime - p.release);

    // ── Envelope gain ──────────────────────────────────────────────────────
    const envGain = ctx.createGain();
    envGain.gain.setValueAtTime(0, startTime);
    envGain.gain.linearRampToValueAtTime(gainValue, attackEnd);
    envGain.gain.linearRampToValueAtTime(sustainLevel, decayEnd);
    envGain.gain.setValueAtTime(sustainLevel, releaseStart);
    envGain.gain.linearRampToValueAtTime(0, endTime);

    // ── Stereo panner ──────────────────────────────────────────────────────
    const panner = ctx.createStereoPanner();
    panner.pan.value = Math.max(-1, Math.min(1, pan));
    panner.connect(this.#masterGain);

    // ── Optional filter: envGain → filter → panner, or envGain → panner ──
    if (p.filterType !== 'none') {
      const filter = ctx.createBiquadFilter();
      filter.type = p.filterType;
      filter.frequency.value = p.filterFreq;
      filter.Q.value = p.filterQ;
      envGain.connect(filter);
      filter.connect(panner);
    } else {
      envGain.connect(panner);
    }

    // ── Source ─────────────────────────────────────────────────────────────
    if (waveformType === 'noise') {
      this.#scheduleNoise(startTime, endTime, envGain);
    } else {
      this.#scheduleOscillator(waveformType, midiPitch, startTime, endTime, envGain, p);
    }
  }

  #scheduleOscillator(type, midiPitch, startTime, endTime, envGain, p) {
    const ctx = this.#ctx;
    const osc = ctx.createOscillator();

    // ── Waveform / duty cycle ───────────────────────────────────────────────
    if (type === 'square') {
      const dutyKey = Math.round(p.dutyCycle * 100);
      if (dutyKey !== 50) {
        if (!this.#pulseWaveCache.has(dutyKey)) {
          this.#pulseWaveCache.set(dutyKey, this.#buildPulseWave(p.dutyCycle));
        }
        osc.setPeriodicWave(this.#pulseWaveCache.get(dutyKey));
      } else {
        osc.type = 'square';
      }
    } else {
      osc.type = type === 'sawtooth' ? 'sawtooth' : 'triangle';
    }

    // ── Frequency / sweep ──────────────────────────────────────────────────
    const baseFreq = midiToFreq(midiPitch);
    if (p.sweepAmount !== 0) {
      const sweepFreq = midiToFreq(midiPitch + p.sweepAmount);
      osc.frequency.setValueAtTime(sweepFreq, startTime);
      osc.frequency.linearRampToValueAtTime(baseFreq, startTime + p.sweepTime);
    } else {
      osc.frequency.value = baseFreq;
    }

    // ── Detune (cents) ─────────────────────────────────────────────────────
    osc.detune.value = p.detune;

    // ── Vibrato LFO ────────────────────────────────────────────────────────
    if (p.vibratoRate > 0 && p.vibratoDepth > 0) {
      const lfo = ctx.createOscillator();
      const lfoGain = ctx.createGain();
      lfo.frequency.value = p.vibratoRate;
      // depthHz = baseFreq · (2^(depth/1200) − 1)
      lfoGain.gain.value = baseFreq * (Math.pow(2, p.vibratoDepth / 1200) - 1);
      lfo.connect(lfoGain);
      lfoGain.connect(osc.frequency);
      lfo.start(startTime);
      lfo.stop(endTime);
    }

    osc.connect(envGain);
    osc.start(startTime);
    osc.stop(endTime);
  }

  #scheduleNoise(startTime, endTime, envGain) {
    const source = this.#ctx.createBufferSource();
    source.buffer = this.#noiseBuffer;
    source.loop = true;
    source.connect(envGain);
    source.start(startTime);
    source.stop(endTime);
  }

  getChannelDefs() {
    return [
      { name: 'Pulse 1',  waveform_type: 'square',   default_pitch: 72, volume: 0.7,  pan: 0.0 },
      { name: 'Pulse 2',  waveform_type: 'square',   default_pitch: 67, volume: 0.6,  pan: 0.0 },
      { name: 'Triangle', waveform_type: 'triangle', default_pitch: 48, volume: 0.75, pan: 0.0 },
      { name: 'Noise',    waveform_type: 'noise',    default_pitch: 0,  volume: 0.5,  pan: 0.0 },
    ];
  }

  dispose() {
    this.#masterGain?.disconnect();
    this.#masterGain = null;
    this.#noiseBuffer = null;
    this.#pulseWaveCache.clear();
    this.#ctx = null;
  }
}

export default ChiptuneSynth;
