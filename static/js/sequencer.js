/**
 * Sequencer — look-ahead step sequencer scheduler.
 *
 * Uses Chris Wilson's web-audio scheduling pattern:
 *   A setTimeout loop wakes up every `scheduleInterval` ms and schedules
 *   any notes that fall within the next `lookahead` seconds into the future.
 *   This decouples the (imprecise) JS timer from the (sample-accurate)
 *   Web Audio clock, giving tight timing without audio glitches.
 *
 * Usage:
 *   const seq = new Sequencer(synth, channels);
 *   seq.bpm = 140;
 *   seq.play();
 *   seq.stop();
 */
export class Sequencer {
  /** @type {import('./synth/SynthBase.js').SynthBase} */
  #synth;

  /** @type {AudioContext} */
  #ctx;

  /** Array of channel state objects (see ChannelStrip.js for shape) */
  #channels = [];

  #bpm = 120;
  #stepsPerBeat = 4;       // 16th notes (4 steps per quarter note)
  #totalSteps = 16;
  #lookahead = 0.1;        // seconds to look ahead
  #scheduleInterval = 25;  // ms between scheduler ticks

  #currentStep = 0;
  #nextStepTime = 0;       // AudioContext time of the next step
  #timerID = null;
  #isPlaying = false;

  /** Callback invoked with the current step index during playback for UI updates. */
  onStep = null;

  /**
   * @param {import('./synth/SynthBase.js').SynthBase} synth
   * @param {AudioContext} ctx
   */
  constructor(synth, ctx) {
    this.#synth = synth;
    this.#ctx = ctx;
  }

  get bpm() { return this.#bpm; }
  set bpm(value) { this.#bpm = Math.max(20, Math.min(300, value)); }

  get totalSteps() { return this.#totalSteps; }
  set totalSteps(value) {
    this.#totalSteps = value;
    if (this.#currentStep >= value) this.#currentStep = 0;
  }

  get isPlaying() { return this.#isPlaying; }

  /** Replace the channel data (called when project loads or UI changes). */
  setChannels(channels) {
    this.#channels = channels;
  }

  /** Duration of one step in seconds. */
  #secondsPerStep() {
    return (60 / this.#bpm) / this.#stepsPerBeat;
  }

  #schedule() {
    const ctx = this.#ctx;
    const stepDuration = this.#secondsPerStep();

    while (this.#nextStepTime < ctx.currentTime + this.#lookahead) {
      const step = this.#currentStep;
      const t = this.#nextStepTime;

      // Notify UI of the current playhead position (fire-and-forget)
      if (this.onStep) {
        // Use postMessage trick to run the UI update outside the audio thread
        const s = step;
        setTimeout(() => this.onStep(s), 0);
      }

      // Schedule notes for every active, un-muted channel
      for (const ch of this.#channels) {
        if (ch.muted) continue;
        const stepData = ch.steps[step];
        if (!stepData?.active) continue;

        this.#synth.playNote(
          ch.waveformType,
          stepData.pitch,
          t,
          stepDuration * 0.9, // slight gate (90% of step duration)
          stepData.velocity,
          ch.volume,
          ch.pan,
        );
      }

      this.#currentStep = (this.#currentStep + 1) % this.#totalSteps;
      this.#nextStepTime += stepDuration;
    }

    this.#timerID = setTimeout(() => this.#schedule(), this.#scheduleInterval);
  }

  play() {
    if (this.#isPlaying) return;
    this.#isPlaying = true;
    this.#currentStep = 0;
    this.#nextStepTime = this.#ctx.currentTime;
    this.#schedule();
  }

  stop() {
    if (!this.#isPlaying) return;
    this.#isPlaying = false;
    clearTimeout(this.#timerID);
    this.#timerID = null;
    this.#currentStep = 0;
    if (this.onStep) this.onStep(-1); // signal UI to clear playhead
  }
}
