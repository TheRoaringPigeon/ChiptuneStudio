/**
 * StepGrid — a row of toggle buttons representing the steps for one channel.
 *
 * Each button carries data-step and data-channel attributes so that
 * SelectionManager can identify it for 2D drag-selection.
 *
 * Dispatches 'step-toggle' on the element so parent components can react.
 */
export class StepGrid {
  /** @type {HTMLElement} */
  element;

  /** @type {{ active: boolean, pitch: number, velocity: number }[]} */
  #steps;

  /** @type {HTMLButtonElement[]} */
  #buttons = [];

  #activePlayheadIndex = -1;
  #channelIndex = 0;

  /**
   * @param {HTMLElement} container
   * @param {number}      stepCount
   * @param {object[]}    steps        Initial step data array
   * @param {number}      channelIndex Used for data-channel attribute
   */
  constructor(container, stepCount, steps, channelIndex = 0) {
    this.#steps = steps;
    this.#channelIndex = channelIndex;
    this.element = document.createElement('div');
    this.element.className = 'step-grid';
    this.#render(stepCount);
    container.appendChild(this.element);
  }

  #render(stepCount) {
    this.#buttons = [];
    this.element.innerHTML = '';
    for (let i = 0; i < stepCount; i++) {
      this.element.appendChild(this.#makeButton(i));
    }
  }

  #makeButton(i) {
    const btn = document.createElement('button');
    btn.className = 'step-btn';
    btn.dataset.index   = String(i);
    btn.dataset.step    = String(i);
    btn.dataset.channel = String(this.#channelIndex);

    const stepData = this.#steps[i] ?? { active: false };
    if (stepData.active) btn.classList.add('active');
    if (i % 4 === 0) btn.classList.add('beat-start');

    btn.addEventListener('click', () => this.#onToggle(i, btn));
    this.#buttons.push(btn);
    return btn;
  }

  #onToggle(index, btn) {
    // Clicks are blocked on locked steps
    if (btn.classList.contains('locked')) return;
    const step = this.#steps[index];
    if (!step) return;
    step.active = !step.active;
    btn.classList.toggle('active', step.active);

    this.element.dispatchEvent(new CustomEvent('step-toggle', {
      bubbles: true,
      detail: { stepIndex: index, active: step.active },
    }));
  }

  /** Highlight the current playhead position. */
  setPlayhead(stepIndex) {
    if (this.#activePlayheadIndex >= 0) {
      this.#buttons[this.#activePlayheadIndex]?.classList.remove('playing');
    }
    this.#activePlayheadIndex = stepIndex;
    if (stepIndex >= 0) {
      this.#buttons[stepIndex]?.classList.add('playing');
    }
  }

  /**
   * Apply locked-range highlighting. Steps inside any range get .locked
   * and cannot be clicked.
   * @param {{ start: number, end: number }[]} ranges
   */
  setLockedRanges(ranges) {
    for (const btn of this.#buttons) {
      btn.classList.remove('locked');
    }
    for (const { start, end } of ranges) {
      for (let i = start; i <= end && i < this.#buttons.length; i++) {
        this.#buttons[i]?.classList.add('locked');
      }
    }
  }

  /**
   * Apply/remove .selected on a set of step indices.
   * @param {Set<number>} stepSet
   */
  setSelected(stepSet) {
    for (let i = 0; i < this.#buttons.length; i++) {
      this.#buttons[i]?.classList.toggle('selected', stepSet.has(i));
    }
  }

  /** Rebuild grid when step count changes (growing or shrinking). */
  resize(newStepCount, steps) {
    this.#steps = steps;
    const old = this.#buttons.length;
    this.#activePlayheadIndex = -1;

    if (newStepCount > old) {
      // Append new buttons
      for (let i = old; i < newStepCount; i++) {
        this.element.appendChild(this.#makeButton(i));
      }
    } else {
      // Remove excess buttons
      while (this.#buttons.length > newStepCount) {
        const btn = this.#buttons.pop();
        btn.remove();
      }
    }
  }

  /** Read current step data (returns reference, not copy). */
  getSteps() {
    return this.#steps;
  }
}
