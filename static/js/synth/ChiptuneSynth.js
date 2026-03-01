import { SynthBase } from './SynthBase.js';

/** Convert a MIDI note number to frequency in Hz. */
function midiToFreq(note) {
  return 440 * Math.pow(2, (note - 69) / 12);
}

/**
 * ChiptuneSynth — NES/Game Boy style synthesizer using the Web Audio API.
 *
 * Waveform types:
 *   "square"   — OscillatorNode type="square" (pulse 1 & 2)
 *   "triangle" — OscillatorNode type="triangle" (bass channel)
 *   "noise"    — White noise via AudioBufferSourceNode + BiquadFilter (percussion)
 *   "sawtooth" — OscillatorNode type="sawtooth" (available for future use)
 *
 * Each note uses a short ADSR envelope via GainNode automation:
 *   Attack: 2ms, Decay: 10ms, Sustain: 80% volume, Release: 30ms before note end
 */
export class ChiptuneSynth extends SynthBase {
  /** @type {AudioContext} */
  #ctx = null;

  /** Shared gain (master volume for this synth) */
  #masterGain = null;

  /** Pre-built noise buffer (reused for every noise note) */
  #noiseBuffer = null;

  init(ctx) {
    this.#ctx = ctx;
    this.#masterGain = ctx.createGain();
    this.#masterGain.gain.value = 1.0;
    this.#masterGain.connect(ctx.destination);
    this.#noiseBuffer = this.#buildNoiseBuffer();
  }

  /** Create a mono white-noise AudioBuffer (2 seconds, looped). */
  #buildNoiseBuffer() {
    const sampleRate = this.#ctx.sampleRate;
    const bufferSize = sampleRate * 2; // 2 s
    const buffer = this.#ctx.createBuffer(1, bufferSize, sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return buffer;
  }

  playNote(waveformType, midiPitch, startTime, duration, velocity, volume, pan) {
    if (!this.#ctx) return;

    const ctx = this.#ctx;
    const gainValue = (velocity / 127) * volume;
    const endTime = startTime + duration;
    const releaseStart = Math.max(startTime, endTime - 0.03);

    // ── Envelope gain ──────────────────────────────────────────────────────
    const envGain = ctx.createGain();
    envGain.gain.setValueAtTime(0, startTime);
    envGain.gain.linearRampToValueAtTime(gainValue, startTime + 0.002);       // attack
    envGain.gain.linearRampToValueAtTime(gainValue * 0.8, startTime + 0.012); // decay → sustain
    envGain.gain.setValueAtTime(gainValue * 0.8, releaseStart);
    envGain.gain.linearRampToValueAtTime(0, endTime);                          // release

    // ── Stereo panner ──────────────────────────────────────────────────────
    const panner = ctx.createStereoPanner();
    panner.pan.value = Math.max(-1, Math.min(1, pan));

    // ── Source ─────────────────────────────────────────────────────────────
    if (waveformType === 'noise') {
      this.#scheduleNoise(startTime, endTime, envGain, panner);
    } else {
      this.#scheduleOscillator(waveformType, midiPitch, startTime, endTime, envGain, panner);
    }
  }

  #scheduleOscillator(type, midiPitch, startTime, endTime, envGain, panner) {
    const osc = this.#ctx.createOscillator();
    osc.type = type === 'square' ? 'square' : type === 'sawtooth' ? 'sawtooth' : 'triangle';
    osc.frequency.value = midiToFreq(midiPitch);

    osc.connect(envGain);
    envGain.connect(panner);
    panner.connect(this.#masterGain);

    osc.start(startTime);
    osc.stop(endTime);
  }

  #scheduleNoise(startTime, endTime, envGain, panner) {
    const ctx = this.#ctx;

    // High-pass filter to keep it percussive rather than rumbling
    const filter = ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.value = 2000;

    const source = ctx.createBufferSource();
    source.buffer = this.#noiseBuffer;
    source.loop = true;

    source.connect(filter);
    filter.connect(envGain);
    envGain.connect(panner);
    panner.connect(this.#masterGain);

    source.start(startTime);
    source.stop(endTime);
  }

  getChannelDefs() {
    return [
      { name: 'Pulse 1',  waveform_type: 'square',   default_pitch: 72, volume: 0.7, pan: 0.0 },
      { name: 'Pulse 2',  waveform_type: 'square',   default_pitch: 67, volume: 0.6, pan: 0.0 },
      { name: 'Triangle', waveform_type: 'triangle', default_pitch: 48, volume: 0.75, pan: 0.0 },
      { name: 'Noise',    waveform_type: 'noise',    default_pitch: 0,  volume: 0.5, pan: 0.0 },
    ];
  }

  dispose() {
    this.#masterGain?.disconnect();
    this.#masterGain = null;
    this.#noiseBuffer = null;
    this.#ctx = null;
  }
}

export default ChiptuneSynth;
