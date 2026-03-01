/**
 * app.js — ChiptuneStudio bootstrap.
 *
 * Responsibility: wire together the API client, plugin loader, sequencer,
 * and UI components. Keeps each module decoupled from the others.
 */

import * as Api from './api.js';
import { Sequencer } from './sequencer.js';
import { Toolbar } from './ui/Toolbar.js';
import { ChannelStrip } from './ui/ChannelStrip.js';

// ── State ────────────────────────────────────────────────────────────────────

let audioCtx = null;
let synth = null;
let sequencer = null;

/** @type {Toolbar} */
let toolbar = null;

/** @type {ChannelStrip[]} */
let channelStrips = [];

/** @type {{ id: number, plugin_id: string, bpm: number, steps_per_pattern: number, patterns: object[] } | null} */
let currentProject = null;

/** Plugin metadata from backend */
let plugins = [];

// ── DOM ──────────────────────────────────────────────────────────────────────

const appEl        = document.getElementById('app');
const toolbarEl    = document.getElementById('toolbar-mount');
const channelsEl   = document.getElementById('channels-mount');
const statusEl     = document.getElementById('status-bar');

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

// ── Channel strips ───────────────────────────────────────────────────────────

function renderChannels(pattern) {
  channelsEl.innerHTML = '';
  channelStrips = [];

  for (let i = 0; i < pattern.channels.length; i++) {
    const strip = new ChannelStrip(channelsEl, pattern.channels[i], i);
    channelStrips.push(strip);
  }

  // Wire playhead updates from sequencer → all strips
  if (sequencer) {
    sequencer.onStep = (stepIdx) => {
      for (const strip of channelStrips) strip.setPlayhead(stepIdx);
    };
  }
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

  // Load & init the synth plugin for this project
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

  // Render channels from the first (only, for now) pattern
  const pattern = project.patterns[0];
  if (pattern) renderChannels(pattern);

  // Hook up sequencer ↔ channel strips
  updateSequencerChannels();

  toolbar.setCurrentProject(project);
  toolbar.setPlaying(false);
  setStatus(`Loaded: ${project.name}`);
}

function updateSequencerChannels() {
  if (!sequencer) return;
  sequencer.setChannels(channelStrips.map(s => s.sequencerState));
}

async function saveCurrentProject() {
  if (!currentProject) return;

  const pattern = currentProject.patterns[0];
  const payload = {
    name: toolbar.projectName,
    bpm: sequencer?.bpm ?? currentProject.bpm,
    steps_per_pattern: currentProject.steps_per_pattern,
    patterns: [
      {
        name: pattern?.name ?? 'Pattern 1',
        order_index: 0,
        channels: channelStrips.map(s => s.channelData),
      },
    ],
  };

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
  });
  await refreshProjectList();
  await loadProject(project.id);
}

// ── Toolbar event wiring ─────────────────────────────────────────────────────

function bindToolbarEvents() {
  document.addEventListener('transport-play', () => {
    ensureAudioContext();
    updateSequencerChannels();
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

  document.addEventListener('steps-change', (e) => {
    const steps = e.detail.steps;
    if (sequencer) sequencer.totalSteps = steps;
    if (currentProject) currentProject.steps_per_pattern = steps;
    for (const strip of channelStrips) strip.resize(steps);
    updateSequencerChannels();
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
    channelsEl.innerHTML = '';
    channelStrips = [];
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
    steps: 16,
    projectName: 'Untitled',
  });

  bindToolbarEvents();

  // Load the project list and auto-load the most recent one
  const projectList = await refreshProjectList();
  if (projectList.length > 0) {
    await loadProject(projectList[0].id);
  } else {
    // No projects yet — create a default one
    await createNewProject();
  }

  setStatus('Ready.');
}

boot().catch(err => setStatus('Boot error: ' + err.message, true));
