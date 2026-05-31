/**
 * Thin fetch wrapper for the Physics 1 derivation backend.
 * Keeps the HTTP details in one place so the UI never touches `fetch`.
 */

export const API_BASE = "http://localhost:8000";

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
