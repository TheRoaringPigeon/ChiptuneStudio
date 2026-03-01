/**
 * StepGrid — a row of toggle buttons representing the steps for one channel.
 *
 * Each button can be toggled on/off. Dispatches a custom 'step-toggle' event
 * on the element so parent components can react without coupling.
 *
 * @example
 *   const grid = new StepGrid(container, 16, stepDataArray);
 *   grid.element.addEventListener('step-toggle', e => {
 *     const { stepIndex, active } = e.detail;
 *   });
 */
export class StepGrid {
  /** @type {HTMLElement} */
  element;

  /** @type {{ active: boolean, pitch: number, velocity: number }[]} */
  #steps;

  /** @type {HTMLButtonElement[]} */
  #buttons = [];

  #activePlayheadIndex = -1;

  /**
   * @param {HTMLElement} container  Parent element to append into
   * @param {number}      stepCount  Number of steps (16 or 32)
   * @param {object[]}    steps      Initial step data array from the backend
   */
  constructor(container, stepCount, steps) {
    this.#steps = steps;
    this.element = document.createElement('div');
    this.element.className = 'step-grid';
    this.#render(stepCount);
    container.appendChild(this.element);
  }

  #render(stepCount) {
    this.#buttons = [];
    this.element.innerHTML = '';
    for (let i = 0; i < stepCount; i++) {
      const btn = document.createElement('button');
      btn.className = 'step-btn';
      btn.dataset.index = String(i);

      const stepData = this.#steps[i] ?? { active: false };
      if (stepData.active) btn.classList.add('active');

      // Group steps visually into beats (4 per beat)
      if (i % 4 === 0) btn.classList.add('beat-start');

      btn.addEventListener('click', () => this.#onToggle(i, btn));
      this.element.appendChild(btn);
      this.#buttons.push(btn);
    }
  }

  #onToggle(index, btn) {
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

  /** Rebuild grid when step count changes. */
  resize(newStepCount, steps) {
    this.#steps = steps;
    this.#activePlayheadIndex = -1;
    this.#render(newStepCount);
  }

  /** Read current step data (returns reference, not copy). */
  getSteps() {
    return this.#steps;
  }
}
