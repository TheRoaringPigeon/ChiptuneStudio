/**
 * TimelineRuler — step-number labels, draggable loop handles, playhead line.
 *
 * Sits as the first row inside the scrollable center panel so it shares the
 * same horizontal scroll as the step grids below (no JS sync needed).
 *
 * Emits on its element:
 *   'loop-change' → { detail: { start: number, end: number } }
 */
export class TimelineRuler {
  /** @type {HTMLElement} */
  element;

  #totalSteps;
  #loopStart;
  #loopEnd;

  /** @type {HTMLElement[]} */
  #cells = [];

  /** @type {HTMLElement} */
  #loopRegion;
  /** @type {HTMLElement} */
  #handleLeft;
  /** @type {HTMLElement} */
  #handleRight;
  /** @type {HTMLElement} */
  #playheadLine;

  #dragging = null; // 'left' | 'right' | null

  /**
   * @param {HTMLElement} container
   * @param {number} totalSteps
   * @param {number} loopStart
   * @param {number} loopEnd
   */
  constructor(container, totalSteps, loopStart, loopEnd) {
    this.#totalSteps = totalSteps;
    this.#loopStart  = loopStart;
    this.#loopEnd    = loopEnd;

    this.element = document.createElement('div');
    this.element.className = 'timeline-ruler';

    this.#buildRuler();
    container.appendChild(this.element);
    this.#bindDrag();
  }

  // ── Build ───────────────────────────────────────────────────────────────────

  #buildRuler() {
    // Cells row
    const cellsRow = document.createElement('div');
    cellsRow.className = 'ruler-cells';

    for (let i = 0; i < this.#totalSteps; i++) {
      cellsRow.appendChild(this.#makeCell(i));
    }
    this.element.appendChild(cellsRow);

    // Loop region overlay (positioned absolutely over the cells row)
    this.#loopRegion = document.createElement('div');
    this.#loopRegion.className = 'loop-region';

    this.#handleLeft = document.createElement('div');
    this.#handleLeft.className = 'loop-handle loop-handle-left';
    this.#handleLeft.title = 'Drag to set loop start';

    this.#handleRight = document.createElement('div');
    this.#handleRight.className = 'loop-handle loop-handle-right';
    this.#handleRight.title = 'Drag to set loop end';

    this.#loopRegion.appendChild(this.#handleLeft);
    this.#loopRegion.appendChild(this.#handleRight);
    this.element.appendChild(this.#loopRegion);

    // Playhead line
    this.#playheadLine = document.createElement('div');
    this.#playheadLine.className = 'playhead-line';
    this.element.appendChild(this.#playheadLine);

    this.#repositionLoop();
  }

  #makeCell(i) {
    const cell = document.createElement('div');
    cell.className = 'ruler-cell';
    cell.dataset.step = String(i);
    if (i % 4 === 0) cell.classList.add('beat-start');
    // Show number every 4 steps (beat), or every step if small
    cell.textContent = (i % 4 === 0) ? String(i + 1) : '';
    this.#cells.push(cell);
    return cell;
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  /** Move the playhead indicator to a step index (-1 = hidden). */
  setPlayhead(stepIndex) {
    if (stepIndex < 0) {
      this.#playheadLine.style.display = 'none';
      return;
    }
    const cell = this.#cells[stepIndex];
    if (!cell) return;
    const rulerRect = this.element.getBoundingClientRect();
    const cellRect  = cell.getBoundingClientRect();
    const left = cellRect.left - rulerRect.left + this.element.parentElement.scrollLeft +
                 (cellRect.width / 2);
    this.#playheadLine.style.display = 'block';
    this.#playheadLine.style.left = left + 'px';
  }

  /** Extend or shrink the ruler by adding/removing cells. */
  setTotalSteps(n) {
    const cellsRow = this.element.querySelector('.ruler-cells');
    if (n > this.#totalSteps) {
      for (let i = this.#totalSteps; i < n; i++) {
        cellsRow.appendChild(this.#makeCell(i));
      }
    } else {
      while (this.#cells.length > n) {
        const cell = this.#cells.pop();
        cell.remove();
      }
    }
    this.#totalSteps = n;
    // Clamp loop end
    if (this.#loopEnd >= n) {
      this.#loopEnd = n - 1;
    }
    this.#repositionLoop();
  }

  /** Reposition the loop band to new indices. */
  setLoopRegion(start, end) {
    this.#loopStart = start;
    this.#loopEnd   = end;
    this.#repositionLoop();
  }

  // ── Loop band positioning ───────────────────────────────────────────────────

  #cellLeft(index) {
    const cell = this.#cells[index];
    if (!cell) return 0;
    // Position relative to the ruler element itself
    // We need offset from the parent (ruler element)
    return cell.offsetLeft;
  }

  #cellRight(index) {
    const cell = this.#cells[index];
    if (!cell) return 0;
    return cell.offsetLeft + cell.offsetWidth;
  }

  #repositionLoop() {
    // Defer to next frame so cells have been laid out
    requestAnimationFrame(() => {
      const left  = this.#cellLeft(this.#loopStart);
      const right = this.#cellRight(this.#loopEnd);
      this.#loopRegion.style.left  = left + 'px';
      this.#loopRegion.style.width = (right - left) + 'px';
    });
  }

  // ── Drag handles ────────────────────────────────────────────────────────────

  #bindDrag() {
    this.#handleLeft.addEventListener('mousedown', (e) => {
      this.#dragging = 'left';
      e.preventDefault();
      e.stopPropagation();
    });
    this.#handleRight.addEventListener('mousedown', (e) => {
      this.#dragging = 'right';
      e.preventDefault();
      e.stopPropagation();
    });

    document.addEventListener('mousemove', (e) => {
      if (!this.#dragging) return;
      const step = this.#stepAtClientX(e.clientX);
      if (step === null) return;

      if (this.#dragging === 'left') {
        const newStart = Math.min(step, this.#loopEnd);
        if (newStart !== this.#loopStart) {
          this.#loopStart = newStart;
          this.#repositionLoop();
        }
      } else {
        const newEnd = Math.max(step, this.#loopStart);
        if (newEnd !== this.#loopEnd) {
          this.#loopEnd = newEnd;
          this.#repositionLoop();
        }
      }
    });

    document.addEventListener('mouseup', () => {
      if (!this.#dragging) return;
      this.#dragging = null;
      this.#emit('loop-change', { start: this.#loopStart, end: this.#loopEnd });
    });
  }

  /** Find the step index closest to a client X coordinate. */
  #stepAtClientX(clientX) {
    // Account for the scrollable container's scroll offset
    const scrollEl = this.element.closest('.seq-scroll') ?? this.element.parentElement;
    const scrollLeft = scrollEl ? scrollEl.scrollLeft : 0;
    const rulerRect  = this.element.getBoundingClientRect();
    const localX = clientX - rulerRect.left + scrollLeft;

    let closest = null;
    let closestDist = Infinity;
    for (let i = 0; i < this.#cells.length; i++) {
      const cell = this.#cells[i];
      const center = cell.offsetLeft + cell.offsetWidth / 2;
      const dist = Math.abs(localX - center);
      if (dist < closestDist) {
        closestDist = dist;
        closest = i;
      }
    }
    return closest;
  }

  #emit(name, detail) {
    this.element.dispatchEvent(new CustomEvent(name, { bubbles: true, detail }));
  }
}
