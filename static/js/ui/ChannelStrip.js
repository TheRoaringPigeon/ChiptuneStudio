import { StepGrid } from './StepGrid.js';

/**
 * ChannelStrip — one row in the sequencer for a single instrument channel.
 *
 * State management: each strip owns a persistent #liveState object.
 * The Sequencer holds a direct reference to this object (via sequencerState),
 * so any UI change (mute, volume) is visible to the Sequencer on its very
 * next scheduling tick — no snapshots, no events, no getter tricks.
 */
export class ChannelStrip {
  /** @type {HTMLElement} */
  element;

  /** @type {StepGrid} */
  #grid;

  /** Raw channel data from the backend (source of truth for serialisation). */
  #data;

  /**
   * Persistent live-state object shared directly with the Sequencer.
   * Mutated in-place whenever the UI changes so the Sequencer always
   * reads current values.
   */
  #liveState;

  /** @type {number} */
  #channelIndex;

  /**
   * @param {HTMLElement} container
   * @param {object}      channelData   Channel object from the backend (with steps[])
   * @param {number}      channelIndex
   */
  constructor(container, channelData, channelIndex) {
    this.#data = channelData;
    this.#channelIndex = channelIndex;

    this.#liveState = {
      waveformType: channelData.waveform_type,
      volume:       channelData.volume,
      pan:          channelData.pan ?? 0,
      muted:        channelData.muted,
      steps:        channelData.steps, // array reference — step toggles are live automatically
    };

    this.element = document.createElement('div');
    this.element.className = 'channel-strip';
    this.#render();
    container.appendChild(this.element);
  }

  #waveformIcon(type) {
    const icons = {
      square:   '▊',
      triangle: '△',
      sawtooth: '⟋',
      noise:    '≋',
    };
    return icons[type] ?? '?';
  }

  #render() {
    const d = this.#data;

    this.element.innerHTML = `
      <div class="ch-label">
        <span class="ch-wave-badge" title="${d.waveform_type}">${this.#waveformIcon(d.waveform_type)}</span>
        <span class="ch-name">${d.name}</span>
      </div>
      <div class="ch-controls">
        <button class="ch-mute-btn${d.muted ? ' muted' : ''}" title="Mute">M</button>
        <input  class="ch-volume" type="range" min="0" max="1" step="0.01" value="${d.volume}" title="Volume">
      </div>
      <div class="ch-grid-wrap"></div>
    `;

    const gridWrap = this.element.querySelector('.ch-grid-wrap');
    this.#grid = new StepGrid(gridWrap, d.steps.length, d.steps);

    // Mute toggle — update both #data and #liveState
    const muteBtn = this.element.querySelector('.ch-mute-btn');
    muteBtn.addEventListener('click', () => {
      d.muted = !d.muted;
      this.#liveState.muted = d.muted;
      muteBtn.classList.toggle('muted', d.muted);
    });

    // Volume — update both #data and #liveState
    const volInput = this.element.querySelector('.ch-volume');
    volInput.addEventListener('input', () => {
      d.volume = parseFloat(volInput.value);
      this.#liveState.volume = d.volume;
    });
  }

  /** Highlight the current playhead column. */
  setPlayhead(stepIndex) {
    this.#grid.setPlayhead(stepIndex);
  }

  /** Rebuild when step count changes. */
  resize(newStepCount) {
    while (this.#data.steps.length < newStepCount) {
      const last = this.#data.steps[this.#data.steps.length - 1];
      this.#data.steps.push({
        step_index: this.#data.steps.length,
        active: false,
        pitch: last?.pitch ?? 60,
        velocity: last?.velocity ?? 100,
      });
    }
    this.#data.steps = this.#data.steps.slice(0, newStepCount);
    this.#liveState.steps = this.#data.steps; // keep liveState in sync after slice
    this.#grid.resize(newStepCount, this.#data.steps);
  }

  /**
   * Returns the persistent live-state object for the Sequencer.
   * Always the same object reference — the Sequencer can store it once
   * and always reads current values.
   */
  get sequencerState() {
    return this.#liveState;
  }

  /**
   * Returns a serialisable snapshot for saving to the backend.
   */
  get channelData() {
    return {
      name:          this.#data.name,
      waveform_type: this.#data.waveform_type,
      volume:        this.#data.volume,
      pan:           this.#data.pan ?? 0,
      muted:         this.#data.muted,
      steps: this.#data.steps.map((s, i) => ({
        step_index: i,
        active:     s.active,
        pitch:      s.pitch,
        velocity:   s.velocity,
      })),
    };
  }
}
