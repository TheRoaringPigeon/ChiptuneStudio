/**
 * api.js — thin wrappers around the ChiptuneStudio backend REST API.
 * All functions return parsed JSON or throw on non-OK responses.
 */

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== null) opts.body = JSON.stringify(body);

  const res = await fetch(path, opts);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${method} ${path} → ${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Plugins ──────────────────────────────────────────────────────────────────

/** @returns {Promise<PluginMeta[]>} */
export async function listPlugins() {
  return request('GET', '/api/plugins');
}

// ── Projects ─────────────────────────────────────────────────────────────────

/** @returns {Promise<ProjectSummary[]>} */
export async function listProjects() {
  return request('GET', '/api/projects');
}

/**
 * @param {{ name: string, plugin_id: string, bpm?: number, steps_per_pattern?: number }} payload
 * @returns {Promise<ProjectFull>}
 */
export async function createProject(payload) {
  return request('POST', '/api/projects', payload);
}

/**
 * @param {number} id
 * @returns {Promise<ProjectFull>}
 */
export async function getProject(id) {
  return request('GET', `/api/projects/${id}`);
}

/**
 * @param {number} id
 * @param {object} payload  Full project state (name, bpm, steps_per_pattern, patterns[])
 * @returns {Promise<ProjectFull>}
 */
export async function saveProject(id, payload) {
  return request('PUT', `/api/projects/${id}`, payload);
}

/**
 * @param {number} id
 * @returns {Promise<null>}
 */
export async function deleteProject(id) {
  return request('DELETE', `/api/projects/${id}`);
}
