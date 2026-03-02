/**
 * app.js — ChiptuneStudio bootstrap.
 *
 * Wires together the API client, plugin loader, sequencer, and UI components.
 * The SequencerLayout owns all channel strips, the ruler, and the +/– pad.
 */

import * as Api from './api.js';
import { Sequencer } from './sequencer.js';
import { Toolbar } from './ui/Toolbar.js';
import { SequencerLayout } from './ui/SequencerLayout.js';

// ── State ────────────────────────────────────────────────────────────────────

let audioCtx = null;
let synth = null;
let sequencer = null;

/** @type {Toolbar} */
let toolbar = null;

/** @type {SequencerLayout | null} */
let layout = null;

/** @type {{ id: number, plugin_id: string, bpm: number, steps_per_pattern: number, patterns: object[] } | null} */
let currentProject = null;

/** Plugin metadata from backend */
let plugins = [];

// ── DOM ──────────────────────────────────────────────────────────────────────

const toolbarEl  = document.getElementById('toolbar-mount');
const channelsEl = document.getElementById('channels-mount');
const statusEl   = document.getElementById('status-bar');

// ── Helpers ──────────────────────────────────────────────────────────────────

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.className = isError ? 'status-bar error' : 'status-bar';
}

/** Lazily create the AudioContext on first user interaction (browser policy). */
function ensureAudioContext() {
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

/** Dynamically load the synth plugin JS module registered by the backend. */
async function loadSynthPlugin(pluginMeta) {
  const mod = await import(pluginMeta.frontend_module);
  const SynthClass = mod.default ?? Object.values(mod)[0];
  return new SynthClass();
}

// ── Project management ───────────────────────────────────────────────────────

async function refreshProjectList() {
  const projects = await Api.listProjects();
  toolbar.setProjectList(projects);
  return projects;
}

async function loadProject(projectId) {
  const project = await Api.getProject(projectId);
  currentProject = project;

  const pluginMeta = plugins.find(p => p.id === project.plugin_id);
  if (!pluginMeta) {
    setStatus(`Unknown plugin: ${project.plugin_id}`, true);
    return;
  }

  const ctx = ensureAudioContext();
  if (synth) synth.dispose();
  synth = await loadSynthPlugin(pluginMeta);
  synth.init(ctx);

  if (sequencer) sequencer.stop();
  sequencer = new Sequencer(synth, ctx);
  sequencer.bpm = project.bpm;
  sequencer.totalSteps = project.steps_per_pattern;
  sequencer.setLoopRegion(project.loop_start ?? 0, project.loop_end ?? project.steps_per_pattern - 1);

  // Build the layout (clears and rebuilds channelsEl)
  channelsEl.innerHTML = '';
  layout = new SequencerLayout(
    channelsEl,
    project,
    (start, end) => sequencer.setLoopRegion(start, end),
    (total) => {
      sequencer.totalSteps = total;
      if (currentProject) currentProject.steps_per_pattern = total;
    },
  );

  // Wire sequencer onStep → layout playhead
  sequencer.onStep = (stepIdx) => layout.setPlayhead(stepIdx);

  // Feed channel states to sequencer
  sequencer.setChannels(layout.getChannelStates());

  toolbar.setCurrentProject(project);
  toolbar.setPlaying(false);
  setStatus(`Loaded: ${project.name}`);
}

async function saveCurrentProject() {
  if (!currentProject || !layout) return;

  const payload = layout.serialize(
    toolbar.projectName,
    sequencer?.bpm ?? currentProject.bpm,
    currentProject,
  );

  const saved = await Api.saveProject(currentProject.id, payload);
  currentProject = saved;
  setStatus(`Saved: ${saved.name}`);
  await refreshProjectList();
}

async function createNewProject() {
  const pluginMeta = plugins[0];
  if (!pluginMeta) { setStatus('No plugins available', true); return; }

  const name = `New Project ${Date.now().toString().slice(-4)}`;
  const project = await Api.createProject({
    name,
    plugin_id: pluginMeta.id,
    bpm: 120,
    steps_per_pattern: 16,
    loop_start: 0,
    loop_end: 15,
  });
  await refreshProjectList();
  await loadProject(project.id);
}

// ── Toolbar event wiring ─────────────────────────────────────────────────────

function bindToolbarEvents() {
  document.addEventListener('transport-play', () => {
    ensureAudioContext();
    if (layout) sequencer.setChannels(layout.getChannelStates());
    sequencer?.play();
    toolbar.setPlaying(true);
    setStatus('Playing…');
  });

  document.addEventListener('transport-stop', () => {
    sequencer?.stop();
    toolbar.setPlaying(false);
    setStatus('Stopped.');
  });

  document.addEventListener('bpm-change', (e) => {
    if (sequencer) sequencer.bpm = e.detail.bpm;
    if (currentProject) currentProject.bpm = e.detail.bpm;
  });

  document.addEventListener('project-new', createNewProject);
  document.addEventListener('project-save', saveCurrentProject);

  document.addEventListener('project-load', (e) => {
    loadProject(e.detail.projectId).catch(err => setStatus(err.message, true));
  });

  document.addEventListener('project-delete', async (e) => {
    if (!confirm('Delete this project?')) return;
    await Api.deleteProject(e.detail.projectId);
    setStatus('Project deleted.');
    currentProject = null;
    layout = null;
    channelsEl.innerHTML = '';
    await refreshProjectList();
  });
}

// ── Boot ─────────────────────────────────────────────────────────────────────

async function boot() {
  setStatus('Loading…');

  try {
    plugins = await Api.listPlugins();
  } catch (err) {
    setStatus('Failed to load plugins: ' + err.message, true);
    return;
  }

  toolbar = new Toolbar(toolbarEl, {
    bpm: 120,
    projectName: 'Untitled',
  });

  bindToolbarEvents();

  const projectList = await refreshProjectList();
  if (projectList.length > 0) {
    await loadProject(projectList[0].id);
  } else {
    await createNewProject();
  }

  setStatus('Ready.');
}

boot().catch(err => setStatus('Boot error: ' + err.message, true));
