/**
 * Thin fetch wrapper for the Physics 1 derivation backend.
 * Keeps the HTTP details in one place so the UI never touches `fetch`.
 *
 * API_BASE resolution order (first match wins):
 *   1. ?api=<url>           — query string override (handy for testing)
 *   2. localStorage         — persisted override (set once, sticks)
 *   3. localhost default    — when running on localhost / 127.0.0.1
 *   4. production default   — the deployed Render URL
 */

const DEFAULT_LOCAL  = "http://localhost:8000";
const DEFAULT_REMOTE = "https://physics-solver-api.onrender.com";

function resolveApiBase() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("api");
  if (fromQuery) {
    try { localStorage.setItem("physics_api_base", fromQuery); } catch {}
    return fromQuery;
  }
  try {
    const stored = localStorage.getItem("physics_api_base");
    if (stored) return stored;
  } catch {}

  const host = window.location.hostname;
  const isLocal = host === "localhost" || host === "127.0.0.1" || host === "";
  return isLocal ? DEFAULT_LOCAL : DEFAULT_REMOTE;
}

export const API_BASE = resolveApiBase();

/**
 * POST /api/solve
 * @param {{ knowns: Object, target: string }} payload
 * @returns {Promise<Object>} resolves to {target, value, unit, steps, equations_used}
 * @throws  {Error} with the backend's `detail` string on a 4xx/5xx response
 */
export async function solve(payload) {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/solve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (networkErr) {
    // Connection refused, CORS blocked, DNS failure, etc.
    throw new Error(
      `Cannot reach backend at ${API_BASE}. Is it running?\n(${networkErr.message})`
    );
  }

  // The API uses JSON for both success and error bodies.
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

/** Quick liveness check — used to colour the footer status indicator. */
export async function ping() {
  try {
    const r = await fetch(`${API_BASE}/health`);
    return r.ok;
  } catch {
    return false;
  }
}
