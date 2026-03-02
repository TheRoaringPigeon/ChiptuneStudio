/**
 * ChannelSettingsPanel — floating singleton panel for per-channel synth params.
 *
 * Usage:
 *   import { channelSettingsPanel } from './ChannelSettingsPanel.js';
 *   channelSettingsPanel.open(name, waveformType, synthParams, anchorEl);
 *   channelSettingsPanel.close();
 *
 * `synthParams` is mutated directly (shared live-state reference), so every
 * slider drag takes effect on the very next sequencer note.
 */
class ChannelSettingsPanel {
  /** @type {HTMLElement} */
  #el;

  constructor() {
    this.#el = document.createElement('div');
    this.#el.className = 'channel-settings-panel';
    this.#el.style.display = 'none';
    document.body.appendChild(this.#el);

    // Dismiss on outside mousedown (ignore clicks on gear buttons themselves —
    // ChannelStrip handles toggle behaviour there).
    document.addEventListener('mousedown', (e) => {
      if (this.#el.style.display === 'none') return;
      if (this.#el.contains(e.target)) return;
      if (e.target.classList.contains('ch-settings-btn')) return;
      this.close();
    });
  }

  /**
   * Populate and show the panel anchored near `anchorEl`.
   * @param {string}      channelName
   * @param {string}      waveformType  'square' | 'triangle' | 'sawtooth' | 'noise'
   * @param {object}      synthParams   Live-state reference — mutated directly
   * @param {HTMLElement} anchorEl      Button that triggered the open
   */
  open(channelName, waveformType, synthParams, anchorEl) {
    this.#render(channelName, waveformType, synthParams);
    this.#el.style.display = 'block';
    this.#position(anchorEl);
  }

  close() {
    this.#el.style.display = 'none';
  }

  // ── Positioning ─────────────────────────────────────────────────────────────

  #position(anchorEl) {
    const rect     = anchorEl.getBoundingClientRect();
    const panelW   = this.#el.offsetWidth  || 260;
    const panelH   = this.#el.offsetHeight || 400;
    const vw       = window.innerWidth;
    const vh       = window.innerHeight;

    let left = rect.right + 6;
    let top  = rect.top;

    // Flip left if too close to right edge
    if (left + panelW > vw - 8) left = rect.left - panelW - 6;
    // Clamp vertically
    if (top + panelH > vh - 8) top = vh - panelH - 8;
    if (top < 8) top = 8;

    this.#el.style.left = `${left}px`;
    this.#el.style.top  = `${top}px`;
  }

  // ── Rendering ────────────────────────────────────────────────────────────────

  #render(channelName, waveformType, params) {
    const isOsc    = waveformType !== 'noise';
    const isSquare = waveformType === 'square';

    this.#el.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'csp-header';
    header.innerHTML = `<span>${channelName.toUpperCase()} PARAMS</span><button class="csp-close" title="Close">×</button>`;
    header.querySelector('.csp-close').addEventListener('click', () => this.close());
    this.#el.appendChild(header);

    // ── ENVELOPE (all channels) ───────────────────────────────────────────────
    this.#addSection('ENVELOPE');
    this.#makeSliderRow('ATK',  0.001, 2,   0.001, params.attack,   v => `${(v * 1000).toFixed(0)}ms`, v => { params.attack   = v; });
    this.#makeSliderRow('DEC',  0.001, 2,   0.001, params.decay,    v => `${(v * 1000).toFixed(0)}ms`, v => { params.decay    = v; });
    this.#makeSliderRow('SUS',  0,     1,   0.01,  params.sustain,  v => `${(v * 100).toFixed(0)}%`,   v => { params.sustain  = v; });
    this.#makeSliderRow('REL',  0.001, 3,   0.001, params.release,  v => `${(v * 1000).toFixed(0)}ms`, v => { params.release  = v; });

    // ── TONE (square only) ────────────────────────────────────────────────────
    if (isSquare) {
      this.#addSection('TONE');
      this.#makeSliderRow('DUTY', 0.1, 0.9, 0.01, params.dutyCycle, v => `${(v * 100).toFixed(0)}%`, v => { params.dutyCycle = v; });
    }

    // ── PITCH (oscillators only) ──────────────────────────────────────────────
    if (isOsc) {
      this.#addSection('PITCH');
      this.#makeSliderRow('DETUNE', -100, 100, 1, params.detune,    v => `${v >= 0 ? '+' : ''}${v.toFixed(0)}¢`,  v => { params.detune    = v; });
      this.#makeSliderRow('XPOSE',  -24,  24,  1, params.transpose, v => `${v >= 0 ? '+' : ''}${v.toFixed(0)}st`, v => { params.transpose = v; });
    }

    // ── VIBRATO (oscillators only) ────────────────────────────────────────────
    if (isOsc) {
      this.#addSection('VIBRATO');
      this.#makeSliderRow('RATE',  0, 20,  0.1, params.vibratoRate,  v => `${v.toFixed(1)}Hz`, v => { params.vibratoRate  = v; });
      this.#makeSliderRow('DEPTH', 0, 200, 1,   params.vibratoDepth, v => `${v.toFixed(0)}¢`,  v => { params.vibratoDepth = v; });
    }

    // ── SWEEP (oscillators only) ──────────────────────────────────────────────
    if (isOsc) {
      this.#addSection('SWEEP');
      this.#makeSliderRow('AMT',  -24, 24,  1,     params.sweepAmount, v => `${v >= 0 ? '+' : ''}${v.toFixed(0)}st`, v => { params.sweepAmount = v; });
      this.#makeSliderRow('TIME', 0,   0.5, 0.001, params.sweepTime,   v => `${(v * 1000).toFixed(0)}ms`,            v => { params.sweepTime   = v; });
    }

    // ── FILTER (all channels) ─────────────────────────────────────────────────
    this.#addSection('FILTER');
    this.#makeFilterTypeRow(params);
    this.#makeSliderRow('FREQ', 20, 20000, 1,   params.filterFreq, v => `${v.toFixed(0)}Hz`, v => { params.filterFreq = v; });
    this.#makeSliderRow('Q',    0.1, 20,   0.1, params.filterQ,    v => v.toFixed(1),         v => { params.filterQ   = v; });
  }

  #addSection(label) {
    const el = document.createElement('div');
    el.className = 'csp-section';
    el.textContent = label;
    this.#el.appendChild(el);
  }

  /**
   * Create a slider row and append it to the panel.
   * @param {string}   label
   * @param {number}   min
   * @param {number}   max
   * @param {number}   step
   * @param {number}   value    Initial value
   * @param {Function} formatFn (value) => string
   * @param {Function} onChange (value) => void  — mutates live params
   */
  #makeSliderRow(label, min, max, step, value, formatFn, onChange) {
    const row = document.createElement('div');
    row.className = 'csp-row';

    const lbl = document.createElement('span');
    lbl.className = 'csp-label';
    lbl.textContent = label;

    const slider = document.createElement('input');
    slider.type  = 'range';
    slider.min   = min;
    slider.max   = max;
    slider.step  = step;
    slider.value = value;

    const val = document.createElement('span');
    val.className = 'csp-value';
    val.textContent = formatFn(value);

    slider.addEventListener('input', () => {
      const v = parseFloat(slider.value);
      onChange(v);
      val.textContent = formatFn(v);
    });

    row.appendChild(lbl);
    row.appendChild(slider);
    row.appendChild(val);
    this.#el.appendChild(row);
  }

  /** Filter type dropdown (spans 2 columns — no value readout needed). */
  #makeFilterTypeRow(params) {
    const row = document.createElement('div');
    row.className = 'csp-row';

    const lbl = document.createElement('span');
    lbl.className = 'csp-label';
    lbl.textContent = 'TYPE';

    const select = document.createElement('select');
    select.className = 'csp-select';
    for (const opt of ['none', 'lowpass', 'highpass', 'bandpass']) {
      const o = document.createElement('option');
      o.value = opt;
      o.textContent = opt;
      if (opt === params.filterType) o.selected = true;
      select.appendChild(o);
    }

    select.addEventListener('change', () => {
      params.filterType = select.value;
    });

    row.appendChild(lbl);
    row.appendChild(select);
    this.#el.appendChild(row);
  }
}

export const channelSettingsPanel = new ChannelSettingsPanel();
