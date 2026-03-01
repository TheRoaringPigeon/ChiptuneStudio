/**
 * Toolbar — transport controls and project management bar.
 *
 * Emits custom events on its element:
 *   'transport-play'   — user pressed Play
 *   'transport-stop'   — user pressed Stop
 *   'bpm-change'       — { detail: { bpm: number } }
 *   'steps-change'     — { detail: { steps: number } }
 *   'project-new'      — user clicked New
 *   'project-save'     — user clicked Save
 *   'project-load'     — { detail: { projectId: number } }
 *   'project-delete'   — { detail: { projectId: number } }
 */
export class Toolbar {
  /** @type {HTMLElement} */
  element;

  #projectList = [];
  #currentProjectName = 'Untitled';

  /**
   * @param {HTMLElement} container
   * @param {{ bpm: number, steps: number, projectName: string }} initialState
   */
  constructor(container, initialState) {
    this.element = document.createElement('div');
    this.element.className = 'toolbar';
    this.#currentProjectName = initialState.projectName ?? 'Untitled';
    this.#render(initialState);
    container.appendChild(this.element);
  }

  #render({ bpm, steps }) {
    this.element.innerHTML = `
      <div class="toolbar-section toolbar-title">
        <span class="app-title">CHIPTUNE STUDIO</span>
      </div>

      <div class="toolbar-section toolbar-project">
        <input class="project-name-input" type="text" value="${this.#currentProjectName}" placeholder="Project name" maxlength="64">
        <select class="project-select" title="Load project">
          <option value="">— projects —</option>
        </select>
        <button class="btn-new"    title="New project">NEW</button>
        <button class="btn-save"   title="Save project">SAVE</button>
        <button class="btn-delete" title="Delete project">DEL</button>
      </div>

      <div class="toolbar-section toolbar-transport">
        <button class="btn-play"  title="Play">▶ PLAY</button>
        <button class="btn-stop"  title="Stop">■ STOP</button>
        <label class="ctrl-label bpm-ctrl">
          BPM
          <input class="bpm-slider" type="range" min="20" max="300" step="1" value="${bpm}">
          <span class="bpm-display">${bpm}</span>
        </label>
        <label class="ctrl-label">
          STEPS
          <select class="steps-select">
            ${[8, 16, 32].map(n => `<option value="${n}"${n === steps ? ' selected' : ''}>${n}</option>`).join('')}
          </select>
        </label>
      </div>
    `;

    this.#bindEvents();
  }

  #emit(name, detail = {}) {
    this.element.dispatchEvent(new CustomEvent(name, { bubbles: true, detail }));
  }

  #bindEvents() {
    const el = this.element;

    el.querySelector('.btn-play').addEventListener('click', () => this.#emit('transport-play'));
    el.querySelector('.btn-stop').addEventListener('click', () => this.#emit('transport-stop'));

    const bpmSlider  = el.querySelector('.bpm-slider');
    const bpmDisplay = el.querySelector('.bpm-display');
    bpmSlider.addEventListener('input', () => {
      const bpm = parseInt(bpmSlider.value, 10);
      bpmDisplay.textContent = bpm;
      this.#emit('bpm-change', { bpm });
    });

    const stepsSelect = el.querySelector('.steps-select');
    stepsSelect.addEventListener('change', () => {
      this.#emit('steps-change', { steps: parseInt(stepsSelect.value, 10) });
    });

    el.querySelector('.btn-new').addEventListener('click', () => this.#emit('project-new'));
    el.querySelector('.btn-save').addEventListener('click', () => this.#emit('project-save'));
    el.querySelector('.btn-delete').addEventListener('click', () => {
      const sel = el.querySelector('.project-select');
      const id = parseInt(sel.value, 10);
      if (!isNaN(id) && id > 0) this.#emit('project-delete', { projectId: id });
    });

    const projectSelect = el.querySelector('.project-select');
    projectSelect.addEventListener('change', () => {
      const id = parseInt(projectSelect.value, 10);
      if (!isNaN(id) && id > 0) this.#emit('project-load', { projectId: id });
    });

    const nameInput = el.querySelector('.project-name-input');
    nameInput.addEventListener('input', () => {
      this.#currentProjectName = nameInput.value;
    });
  }

  /** Refresh the project dropdown. */
  setProjectList(projects) {
    this.#projectList = projects;
    const sel = this.element.querySelector('.project-select');
    if (!sel) return;
    sel.innerHTML = '<option value="">— projects —</option>' +
      projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
  }

  /** Reflect a loaded project in the toolbar. */
  setCurrentProject(project) {
    this.#currentProjectName = project.name;
    const nameInput = this.element.querySelector('.project-name-input');
    if (nameInput) nameInput.value = project.name;

    const bpmSlider = this.element.querySelector('.bpm-slider');
    if (bpmSlider) bpmSlider.value = project.bpm;
    const bpmDisplay = this.element.querySelector('.bpm-display');
    if (bpmDisplay) bpmDisplay.textContent = project.bpm;

    const stepsSelect = this.element.querySelector('.steps-select');
    if (stepsSelect) stepsSelect.value = String(project.steps_per_pattern);

    // Select this project in the dropdown
    const sel = this.element.querySelector('.project-select');
    if (sel) sel.value = String(project.id);
  }

  get projectName() {
    return this.element.querySelector('.project-name-input')?.value ?? this.#currentProjectName;
  }

  setPlaying(isPlaying) {
    const playBtn = this.element.querySelector('.btn-play');
    const stopBtn = this.element.querySelector('.btn-stop');
    if (playBtn) playBtn.classList.toggle('active', isPlaying);
    if (stopBtn) stopBtn.classList.toggle('active', !isPlaying);
  }
}
