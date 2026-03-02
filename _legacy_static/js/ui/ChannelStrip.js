import { StepGrid } from './StepGrid.js';
import { channelSettingsPanel } from './ChannelSettingsPanel.js';

/**
 * Merge saved synth params with waveform-appropriate defaults.
 * Noise gets filterType:'highpass' as its default; oscillators get 'none'.
 * @param {string} waveformType
 * @param {object} saved  Partial params from the backend (may be empty)
 * @returns {object}  Complete params object with all 14 keys
 */
export function resolveDefaultParams(waveformType, saved = {}) {
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
    ...saved,
  };
}

/**
 * ChannelStrip — one row in the sequencer for a single instrument channel.
 *
 * In the new 3-column layout, the label/controls live in the fixed left
 * column while the step grid lives in the scrollable center column.
 * This class appends to two separate containers.
 *
 * State management: each strip owns a persistent #liveState object.
 * The Sequencer holds a direct reference to this object (via sequencerState),
 * so any UI change (mute, volume) is visible to the Sequencer on its very
 * next scheduling tick — no snapshots, no events, no getter tricks.
 */

function mergeRanges(ranges) {
  if (!ranges.length) return [];
  const sorted = [...ranges].sort((a, b) => a.start - b.start);
  const merged = [{ ...sorted[0] }];
  for (let i = 1; i < sorted.length; i++) {
    const last = merged[merged.length - 1];
    if (sorted[i].start <= last.end + 1) {
      last.end = Math.max(last.end, sorted[i].end);
    } else {
      merged.push({ ...sorted[i] });
    }
  }
  return merged;
}

function subtractRange(ranges, start, end) {
  const result = [];
  for (const r of ranges) {
    if (r.end < start || r.start > end) {
      result.push({ ...r });
    } else {
      if (r.start < start) result.push({ start: r.start, end: start - 1 });
      if (r.end > end)     result.push({ start: end + 1, end: r.end });
    }
  }
  return result;
}

export class ChannelStrip {
  /** @type {HTMLElement} Label/control element (in left column) */
  labelElement;

  /** @type {HTMLElement} Grid row element (in scroll column) */
  gridElement;

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

  /** @type {{ start: number, end: number }[]} */
  #lockedRanges = [];

  /**
   * @param {HTMLElement} labelContainer   Fixed left column
   * @param {HTMLElement} gridContainer    Scrollable center column
   * @param {object}      channelData      Channel object from the backend (with steps[])
   * @param {number}      channelIndex
   */
  constructor(labelContainer, gridContainer, channelData, channelIndex) {
    this.#data = channelData;
    this.#channelIndex = channelIndex;
    this.#lockedRanges = (channelData.locked_ranges ?? []).map(r => ({ ...r }));

    this.#liveState = {
      waveformType:  channelData.waveform_type,
      volume:        channelData.volume,
      pan:           channelData.pan ?? 0,
      muted:         channelData.muted,
      steps:         channelData.steps,
      lockedRanges:  this.#lockedRanges,
      synthParams:   resolveDefaultParams(channelData.waveform_type, channelData.synth_params ?? {}),
    };

    this.#renderLabel(labelContainer);
    this.#renderGrid(gridContainer);
    this.#grid.setLockedRanges(this.#lockedRanges);
  }

  // ── Rendering ────────────────────────────────────────────────────────────────

  #waveformIcon(type) {
    const icons = { square: '▊', triangle: '△', sawtooth: '⟋', noise: '≋' };
    return icons[type] ?? '?';
  }

  #renderLabel(container) {
    const d = this.#data;
    const el = document.createElement('div');
    el.className = 'ch-label-row';
    el.innerHTML = `
      <div class="ch-label">
        <span class="ch-wave-badge" title="${d.waveform_type}">${this.#waveformIcon(d.waveform_type)}</span>
        <span class="ch-name">${d.name}</span>
        <button class="ch-settings-btn" title="Synth Settings">⚙</button>
      </div>
      <div class="ch-controls">
        <button class="ch-mute-btn${d.muted ? ' muted' : ''}" title="Mute">M</button>
        <input  class="ch-volume" type="range" min="0" max="1" step="0.01" value="${d.volume}" title="Volume">
      </div>
    `;
    this.labelElement = el;
    container.appendChild(el);

    el.querySelector('.ch-settings-btn').addEventListener('click', (e) => {
      channelSettingsPanel.open(d.name, d.waveform_type, this.#liveState.synthParams, e.currentTarget);
      e.stopPropagation();
    });

    el.querySelector('.ch-mute-btn').addEventListener('click', () => {
      d.muted = !d.muted;
      this.#liveState.muted = d.muted;
      el.querySelector('.ch-mute-btn').classList.toggle('muted', d.muted);
    });

    el.querySelector('.ch-volume').addEventListener('input', (ev) => {
      d.volume = parseFloat(ev.target.value);
      this.#liveState.volume = d.volume;
    });
  }

  #renderGrid(container) {
    const el = document.createElement('div');
    el.className = 'ch-grid-row';
    this.gridElement = el;
    container.appendChild(el);

    this.#grid = new StepGrid(el, this.#data.steps.length, this.#data.steps, this.#channelIndex);
  }

  // ── Public API ───────────────────────────────────────────────────────────────

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
    this.#liveState.steps = this.#data.steps;
    this.#grid.resize(newStepCount, this.#data.steps);
  }

  /** Add a locked range (merges with existing). */
  addLockedRange(start, end) {
    this.#lockedRanges = mergeRanges([...this.#lockedRanges, { start, end }]);
    this.#liveState.lockedRanges = this.#lockedRanges;
    this.#grid.setLockedRanges(this.#lockedRanges);
  }

  /** Remove a locked range (subtracts from existing). */
  removeLockedRange(start, end) {
    this.#lockedRanges = subtractRange(this.#lockedRanges, start, end);
    this.#liveState.lockedRanges = this.#lockedRanges;
    this.#grid.setLockedRanges(this.#lockedRanges);
  }

  /** @returns {{ start: number, end: number }[]} */
  get lockedRanges() {
    return this.#lockedRanges;
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
      locked_ranges: this.#lockedRanges.map(r => ({ start: r.start, end: r.end })),
      synth_params:  { ...this.#liveState.synthParams },
      steps: this.#data.steps.map((s, i) => ({
        step_index: i,
        active:     s.active,
        pitch:      s.pitch,
        velocity:   s.velocity,
      })),
    };
  }
}
