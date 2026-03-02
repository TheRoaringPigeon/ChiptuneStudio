/**
 * SequencerLayout — 3-column sequencer container.
 *
 * Column layout:
 *   .seq-left   — fixed-width label/control column
 *   .seq-scroll — horizontally scrollable: ruler + step grids (shared scrollbar)
 *   .seq-right  — fixed-width +/– step pad
 *
 * Owns TimelineRuler, one ChannelStrip per channel, and SelectionManager.
 * Coordinates all child components and surfaces a clean API to app.js.
 */

import { ChannelStrip } from './ChannelStrip.js';
import { TimelineRuler } from './TimelineRuler.js';
import { SelectionManager } from './SelectionManager.js';

// ── Range helpers ─────────────────────────────────────────────────────────────

/** Merge overlapping/adjacent locked ranges. */
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

/** Remove/trim [start,end] from existing locked ranges. */
function subtractRange(ranges, start, end) {
  const result = [];
  for (const r of ranges) {
    if (r.end < start || r.start > end) {
      result.push({ ...r });
    } else {
      if (r.start < start) result.push({ start: r.start, end: start - 1 });
      if (r.end > end)   result.push({ start: end + 1,   end: r.end });
    }
  }
  return result;
}

// ─────────────────────────────────────────────────────────────────────────────

export class SequencerLayout {
  /** @type {HTMLElement} The .seq-layout root */
  element;

  /** @type {HTMLElement} Fixed left column */
  #leftCol;
  /** @type {HTMLElement} Scrollable center */
  #scrollCol;
  /** @type {HTMLElement} Right +/– pad */
  #rightCol;

  /** @type {TimelineRuler} */
  #ruler;

  /** @type {ChannelStrip[]} */
  #strips = [];

  /** @type {SelectionManager} */
  #selMgr;

  #totalSteps = 16;
  #loopStart  = 0;
  #loopEnd    = 15;

  /** Called by app.js when loop changes. @type {(start:number,end:number)=>void} */
  #onLoopChange;
  /** Called by app.js when step count changes. @type {(total:number)=>void} */
  #onStepsChange;

  /**
   * @param {HTMLElement} container          Mount point (replaces contents)
   * @param {object}      project            Full project object from backend
   * @param {(s:number,e:number)=>void} onLoopChange
   * @param {(total:number)=>void}      onStepsChange
   */
  constructor(container, project, onLoopChange, onStepsChange) {
    this.#onLoopChange  = onLoopChange;
    this.#onStepsChange = onStepsChange;

    this.element = document.createElement('div');
    this.element.className = 'seq-layout';
    container.appendChild(this.element);

    this.#buildColumns();
    this.#buildRightPad();
    this.#loadProject(project);
  }

  // ── Column setup ────────────────────────────────────────────────────────────

  #buildColumns() {
    this.#leftCol = document.createElement('div');
    this.#leftCol.className = 'seq-left';

    this.#scrollCol = document.createElement('div');
    this.#scrollCol.className = 'seq-scroll';

    this.#rightCol = document.createElement('div');
    this.#rightCol.className = 'seq-right';

    this.element.appendChild(this.#leftCol);
    this.element.appendChild(this.#scrollCol);
    this.element.appendChild(this.#rightCol);
  }

  #buildRightPad() {
    this.#rightCol.innerHTML = `
      <button data-add="16">+16</button>
      <button data-add="8">+8</button>
      <button data-add="4">+4</button>
      <div class="seq-right-sep">──</div>
      <button data-remove="4">–4</button>
      <button data-remove="1">–1</button>
    `;
    this.#rightCol.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-add],[data-remove]');
      if (!btn) return;
      if (btn.dataset.add)    this.addSteps(parseInt(btn.dataset.add, 10));
      if (btn.dataset.remove) this.removeSteps(parseInt(btn.dataset.remove, 10));
    });
  }

  // ── Project load ────────────────────────────────────────────────────────────

  #loadProject(project) {
    this.#totalSteps = project.steps_per_pattern ?? 16;
    this.#loopStart  = project.loop_start ?? 0;
    this.#loopEnd    = project.loop_end   ?? this.#totalSteps - 1;

    // Clear previous strips + ruler
    this.#strips = [];
    this.#leftCol.innerHTML = '';
    this.#scrollCol.innerHTML = '';

    // Header spacer in left column (matches ruler height)
    const leftHeader = document.createElement('div');
    leftHeader.className = 'seq-left-header';
    this.#leftCol.appendChild(leftHeader);

    // Ruler inside scroll column
    this.#ruler = new TimelineRuler(
      this.#scrollCol,
      this.#totalSteps,
      this.#loopStart,
      this.#loopEnd,
    );
    this.#ruler.element.addEventListener('loop-change', (e) => {
      this.#loopStart = e.detail.start;
      this.#loopEnd   = e.detail.end;
      this.#onLoopChange(this.#loopStart, this.#loopEnd);
    });

    // Channel strips — split label into left, grid into scroll
    const pattern = project.patterns?.[0];
    const channels = pattern?.channels ?? [];
    for (let i = 0; i < channels.length; i++) {
      const strip = new ChannelStrip(
        this.#leftCol,
        this.#scrollCol,
        channels[i],
        i,
      );
      this.#strips.push(strip);
    }

    // Selection manager over the scroll column
    this.#selMgr = new SelectionManager(this.#scrollCol, channels.length);
    this.#scrollCol.addEventListener('selection-lock',   (e) => this.#onLock(e));
    this.#scrollCol.addEventListener('selection-unlock', (e) => this.#onUnlock(e));
  }

  /** Full reload from a saved project (called by app.js when loading). */
  setCurrentProject(project) {
    this.#loadProject(project);
  }

  // ── Lock/Unlock ─────────────────────────────────────────────────────────────

  #onLock(e) {
    const { stepStart, stepEnd, channels } = e.detail;
    for (const ci of channels) {
      const strip = this.#strips[ci];
      if (strip) strip.addLockedRange(stepStart, stepEnd);
    }
    this.#selMgr.clearSelection();
  }

  #onUnlock(e) {
    const { stepStart, stepEnd, channels } = e.detail;
    for (const ci of channels) {
      const strip = this.#strips[ci];
      if (strip) strip.removeLockedRange(stepStart, stepEnd);
    }
    this.#selMgr.clearSelection();
  }

  // ── Playhead ─────────────────────────────────────────────────────────────────

  /** Called by sequencer onStep. Drives ruler + all strips + auto-scroll. */
  setPlayhead(stepIndex) {
    this.#ruler.setPlayhead(stepIndex);
    for (const strip of this.#strips) strip.setPlayhead(stepIndex);

    if (stepIndex >= 0) {
      this.#autoScroll(stepIndex);
    }
  }

  #autoScroll(stepIndex) {
    // Each step cell width = --step-size (38) + gap (3) = 41px, beat-start gets +6px margin
    // Simplest approach: query the actual button from any strip
    const btn = this.#scrollCol.querySelector(`[data-step="${stepIndex}"]`);
    if (!btn) return;
    const scrollEl  = this.#scrollCol;
    const btnLeft   = btn.offsetLeft;
    const btnRight  = btnLeft + btn.offsetWidth;
    const viewLeft  = scrollEl.scrollLeft;
    const viewRight = viewLeft + scrollEl.clientWidth;

    if (btnRight > viewRight - 20) {
      scrollEl.scrollLeft = btnLeft - 40;
    } else if (btnLeft < viewLeft + 20) {
      scrollEl.scrollLeft = Math.max(0, btnLeft - 40);
    }
  }

  // ── Step add/remove ─────────────────────────────────────────────────────────

  addSteps(count) {
    const newTotal = this.#totalSteps + count;
    for (const strip of this.#strips) strip.resize(newTotal);
    this.#ruler.setTotalSteps(newTotal);
    this.#totalSteps = newTotal;
    this.#onStepsChange(newTotal);
  }

  removeSteps(count) {
    const minSteps = 4;
    const newTotal = Math.max(minSteps, this.#totalSteps - count);
    if (newTotal === this.#totalSteps) return;
    // Clamp loop end
    if (this.#loopEnd >= newTotal) {
      this.#loopEnd = newTotal - 1;
      this.#ruler.setLoopRegion(this.#loopStart, this.#loopEnd);
      this.#onLoopChange(this.#loopStart, this.#loopEnd);
    }
    for (const strip of this.#strips) strip.resize(newTotal);
    this.#ruler.setTotalSteps(newTotal);
    this.#totalSteps = newTotal;
    this.#onStepsChange(newTotal);
  }

  // ── Public getters ──────────────────────────────────────────────────────────

  /** Array of sequencer-state objects (live references). */
  getChannelStates() {
    return this.#strips.map(s => s.sequencerState);
  }

  getLoopRegion() {
    return { start: this.#loopStart, end: this.#loopEnd };
  }

  getTotalSteps() {
    return this.#totalSteps;
  }

  /**
   * Returns a ProjectSave-shaped object for backend persistence.
   * @param {string} name    Current project name from toolbar
   * @param {number} bpm
   * @param {object} [existingProject]  Original project for pattern name
   */
  serialize(name, bpm, existingProject) {
    const patternName = existingProject?.patterns?.[0]?.name ?? 'Pattern 1';
    return {
      name,
      bpm,
      steps_per_pattern: this.#totalSteps,
      loop_start: this.#loopStart,
      loop_end:   this.#loopEnd,
      patterns: [
        {
          name:        patternName,
          order_index: 0,
          channels:    this.#strips.map(s => s.channelData),
        },
      ],
    };
  }
}
