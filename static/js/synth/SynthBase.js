/**
 * SynthBase — abstract interface that all synth plugins must implement.
 *
 * A plugin is an ES module that exports a default class extending SynthBase.
 * The frontend loads the plugin's module URL (provided by the backend's
 * plugin metadata) and instantiates it dynamically.
 *
 * Lifecycle:
 *   const synth = new MySynth();
 *   synth.init(audioContext);
 *   synth.playNote(...);   // called by Sequencer
 *   synth.dispose();       // on plugin unload
 */
export class SynthBase {
  /**
   * Called once after the AudioContext is created.
   * @param {AudioContext} ctx
   */
  init(ctx) {
    throw new Error(`${this.constructor.name}.init() not implemented`);
  }

  /**
   * Schedule a single note for future playback.
   *
   * @param {string}  waveformType  - e.g. "square", "triangle", "noise"
   * @param {number}  midiPitch     - MIDI note number (0–127); ignored for noise
   * @param {number}  startTime     - AudioContext time in seconds
   * @param {number}  duration      - Note duration in seconds
   * @param {number}  velocity      - Note velocity (0–127)
   * @param {number}  volume        - Channel volume (0.0–1.0)
   * @param {number}  pan           - Stereo pan (-1.0 left … 1.0 right)
   * @param {object}  synthParams   - Per-channel synthesis parameters (ADSR, filter, etc.)
   */
  playNote(waveformType, midiPitch, startTime, duration, velocity, volume, pan, synthParams = {}) {
    throw new Error(`${this.constructor.name}.playNote() not implemented`);
  }

  /**
   * Return the plugin's default channel definitions.
   * Each entry mirrors the backend ChannelDef shape.
   *
   * @returns {{ name: string, waveform_type: string, default_pitch: number,
   *             volume: number, pan: number }[]}
   */
  getChannelDefs() {
    throw new Error(`${this.constructor.name}.getChannelDefs() not implemented`);
  }

  /**
   * Release any held AudioNodes or resources.
   * Called when the plugin is swapped out or the app shuts down.
   */
  dispose() {}
}
