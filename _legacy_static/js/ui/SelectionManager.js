/**
 * SelectionManager — 2D drag-select over the step grid.
 *
 * Listens for mousedown on any [data-step][data-channel] element inside
 * `scrollContainer`. Tracks a rectangular (step × channel) selection,
 * renders it as a highlight, and shows a floating context bar with
 * Lock / Unlock / Clear actions.
 *
 * Emits on scrollContainer:
 *   'selection-lock'   → { detail: { stepStart, stepEnd, channels: int[] } }
 *   'selection-unlock' → { detail: { stepStart, stepEnd, channels: int[] } }
 */
export class SelectionManager {
  /** @type {HTMLElement} */
  #scrollContainer;

  #channelCount = 0;

  // Current selection in step/channel indices
  #sel = null; // { stepStart, stepEnd, chStart, chEnd } | null

  // Drag origin
  #dragOrigin = null; // { step, ch }

  /** @type {HTMLElement|null} */
  #contextBar = null;

  /**
   * @param {HTMLElement} scrollContainer  The scrollable center panel
   * @param {number}      channelCount
   */
  constructor(scrollContainer, channelCount) {
    this.#scrollContainer = scrollContainer;
    this.#channelCount = channelCount;

    this.#buildContextBar();
    this.#bindEvents();
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  clearSelection() {
    this.#sel = null;
    this.#applySelectionClasses();
    this.#hideContextBar();
  }

  /** @returns {{ stepStart: number, stepEnd: number, channels: number[] } | null} */
  getSelection() {
    if (!this.#sel) return null;
    const { stepStart, stepEnd, chStart, chEnd } = this.#sel;
    const channels = [];
    for (let c = chStart; c <= chEnd; c++) channels.push(c);
    return { stepStart, stepEnd, channels };
  }

  /** Call when channel count changes (add/remove channels). */
  setChannelCount(n) {
    this.#channelCount = n;
  }

  // ── Context bar ─────────────────────────────────────────────────────────────

  #buildContextBar() {
    const bar = document.createElement('div');
    bar.className = 'selection-context-bar';
    bar.style.display = 'none';
    bar.innerHTML = `
      <button class="ctx-lock">Lock</button>
      <button class="ctx-unlock">Unlock</button>
      <button class="ctx-clear">✕ Clear</button>
    `;
    document.body.appendChild(bar);
    this.#contextBar = bar;

    bar.querySelector('.ctx-lock').addEventListener('click', () => {
      this.#emitAction('selection-lock');
      this.clearSelection();
    });
    bar.querySelector('.ctx-unlock').addEventListener('click', () => {
      this.#emitAction('selection-unlock');
      this.clearSelection();
    });
    bar.querySelector('.ctx-clear').addEventListener('click', () => {
      this.clearSelection();
    });
  }

  #emitAction(eventName) {
    const sel = this.getSelection();
    if (!sel) return;
    this.#scrollContainer.dispatchEvent(new CustomEvent(eventName, {
      bubbles: true,
      detail: sel,
    }));
  }

  #showContextBar(x, y) {
    const bar = this.#contextBar;
    bar.style.display = 'flex';
    // Position near cursor, keep within viewport
    const bw = 200, bh = 36;
    const vw = window.innerWidth, vh = window.innerHeight;
    bar.style.left = Math.min(x + 8, vw - bw - 8) + 'px';
    bar.style.top  = Math.max(y - bh - 8, 8) + 'px';
  }

  #hideContextBar() {
    if (this.#contextBar) this.#contextBar.style.display = 'none';
  }

  // ── Event binding ───────────────────────────────────────────────────────────

  #bindEvents() {
    this.#scrollContainer.addEventListener('mousedown', (e) => {
      const btn = e.target.closest('[data-step][data-channel]');
      if (!btn) return;
      // Only start drag on right-click or shift+click to avoid blocking normal toggles
      // Actually per plan: plain drag-select. We use left mouse button drag.
      // We start tracking but let the click through for single clicks.
      const step = parseInt(btn.dataset.step, 10);
      const ch   = parseInt(btn.dataset.channel, 10);
      this.#dragOrigin = { step, ch };
      this.#sel = { stepStart: step, stepEnd: step, chStart: ch, chEnd: ch };
      e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
      if (!this.#dragOrigin) return;
      const el = document.elementFromPoint(e.clientX, e.clientY);
      const btn = el?.closest('[data-step][data-channel]');
      if (!btn) return;
      const step = parseInt(btn.dataset.step, 10);
      const ch   = parseInt(btn.dataset.channel, 10);
      this.#sel = {
        stepStart: Math.min(this.#dragOrigin.step, step),
        stepEnd:   Math.max(this.#dragOrigin.step, step),
        chStart:   Math.min(this.#dragOrigin.ch,   ch),
        chEnd:     Math.max(this.#dragOrigin.ch,   ch),
      };
      this.#applySelectionClasses();
    });

    document.addEventListener('mouseup', (e) => {
      if (!this.#dragOrigin) return;
      const wasDrag = this.#sel &&
        (this.#sel.stepEnd > this.#sel.stepStart || this.#sel.chEnd > this.#sel.chStart);
      this.#dragOrigin = null;
      if (wasDrag && this.#sel) {
        this.#applySelectionClasses();
        this.#showContextBar(e.clientX, e.clientY);
      } else {
        // Single click — clear selection silently
        this.#sel = null;
        this.#applySelectionClasses();
      }
    });

    // Dismiss bar when clicking outside
    document.addEventListener('mousedown', (e) => {
      if (this.#contextBar && !this.#contextBar.contains(e.target)) {
        const btn = e.target.closest('[data-step][data-channel]');
        if (!btn) {
          this.clearSelection();
        }
      }
    }, true);
  }

  // ── Selection highlight ─────────────────────────────────────────────────────

  #applySelectionClasses() {
    // Remove all existing .selected
    this.#scrollContainer.querySelectorAll('.step-btn.selected').forEach(el => {
      el.classList.remove('selected');
    });
    if (!this.#sel) return;
    const { stepStart, stepEnd, chStart, chEnd } = this.#sel;
    for (let c = chStart; c <= chEnd; c++) {
      for (let s = stepStart; s <= stepEnd; s++) {
        const btn = this.#scrollContainer.querySelector(
          `[data-step="${s}"][data-channel="${c}"]`
        );
        btn?.classList.add('selected');
      }
    }
  }
}
